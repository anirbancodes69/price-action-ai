<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/*
 * ARC-03 §7: rulesets, immutable candle snapshots, analysis batches/runs, run children, detected setups,
 * AI explanations. Written by the engine (ARC-01 §6); per-table runtime grants arrive with T-101d.
 *
 * Immutability (C-08, ARC-03 §11) is enforced by triggers, which bind every role including the owner:
 * snapshots, runs, their children and setups reject UPDATE; rulesets reject changes to their content once
 * they leave DRAFT. Deletion stays possible for the retention job and for ON DELETE CASCADE.
 * The functions are CREATE OR REPLACE because migrate:fresh drops tables but not functions.
 */
return new class extends Migration
{
    public function up(): void
    {
        DB::unprepared(<<<'SQL'
            CREATE OR REPLACE FUNCTION reject_row_update() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION '% rows are immutable', TG_TABLE_NAME USING ERRCODE = 'integrity_constraint_violation';
            END
            $$;

            CREATE TABLE ruleset_versions (
                id uuid PRIMARY KEY,
                ruleset_code text NOT NULL,
                version text NOT NULL,
                parameters jsonb NOT NULL,
                parameters_hash text NOT NULL,
                score_version text NOT NULL,
                status text NOT NULL DEFAULT 'DRAFT',
                validation_status text NOT NULL DEFAULT 'HYPOTHESIS',
                created_at timestamptz NOT NULL DEFAULT now(),
                activated_at timestamptz NULL,
                retired_at timestamptz NULL,
                CONSTRAINT uq_ruleset_versions__code_version UNIQUE (ruleset_code, version),
                CONSTRAINT ck_ruleset_versions__version CHECK (version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),
                CONSTRAINT ck_ruleset_versions__parameters_hash CHECK (parameters_hash ~ '^[0-9a-f]{64}$'),
                CONSTRAINT ck_ruleset_versions__status CHECK (status IN ('DRAFT', 'ACTIVE', 'RETIRED')),
                CONSTRAINT ck_ruleset_versions__validation_status CHECK (validation_status IN ('HYPOTHESIS', 'VALIDATED')),
                CONSTRAINT ck_ruleset_versions__activated CHECK (status = 'DRAFT' OR activated_at IS NOT NULL)
            );

            CREATE OR REPLACE FUNCTION guard_ruleset_content() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF OLD.status <> 'DRAFT' THEN
                    IF NEW.status = 'DRAFT'
                       OR NEW.ruleset_code IS DISTINCT FROM OLD.ruleset_code
                       OR NEW.version IS DISTINCT FROM OLD.version
                       OR NEW.parameters IS DISTINCT FROM OLD.parameters
                       OR NEW.parameters_hash IS DISTINCT FROM OLD.parameters_hash
                       OR NEW.score_version IS DISTINCT FROM OLD.score_version THEN
                        RAISE EXCEPTION 'ruleset % % is % and its content is immutable', OLD.ruleset_code, OLD.version, OLD.status
                            USING ERRCODE = 'integrity_constraint_violation';
                    END IF;
                END IF;
                RETURN NEW;
            END
            $$;
            CREATE TRIGGER tr_ruleset_versions__guard_content BEFORE UPDATE ON ruleset_versions
                FOR EACH ROW EXECUTE FUNCTION guard_ruleset_content();

            -- Identical inputs dedupe on (data_source_id, content_hash). Payload: zstd columnar arrays.
            CREATE TABLE candle_snapshots (
                id uuid PRIMARY KEY,
                data_source_id uuid NOT NULL REFERENCES data_sources (id),
                instrument_id uuid NOT NULL REFERENCES instruments (id),
                timeframe text NOT NULL,
                from_date date NOT NULL,
                to_date date NOT NULL,
                bar_count integer NOT NULL,
                price_basis text NOT NULL,
                content_hash text NOT NULL,
                payload bytea NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_candle_snapshots__data_source_id_content_hash UNIQUE (data_source_id, content_hash),
                CONSTRAINT ck_candle_snapshots__timeframe CHECK (timeframe IN ('1D')),
                CONSTRAINT ck_candle_snapshots__dates CHECK (to_date >= from_date),
                CONSTRAINT ck_candle_snapshots__bar_count CHECK (bar_count > 0),
                CONSTRAINT ck_candle_snapshots__price_basis CHECK (price_basis IN ('ADJUSTED')),
                CONSTRAINT ck_candle_snapshots__content_hash CHECK (content_hash ~ '^[0-9a-f]{64}$')
            );
            CREATE INDEX ix_candle_snapshots__instrument_id_to_date ON candle_snapshots (instrument_id, to_date);
            CREATE TRIGGER tr_candle_snapshots__immutable BEFORE UPDATE ON candle_snapshots
                FOR EACH ROW EXECUTE FUNCTION reject_row_update();

            CREATE TABLE analysis_batches (
                id uuid PRIMARY KEY,
                data_source_id uuid NOT NULL REFERENCES data_sources (id),
                universe_id uuid NOT NULL REFERENCES universes (id),
                as_of_date date NOT NULL,
                ruleset_version_id uuid NOT NULL REFERENCES ruleset_versions (id),
                trigger text NOT NULL,
                status text NOT NULL,
                instruments_total integer NOT NULL DEFAULT 0,
                instruments_completed integer NOT NULL DEFAULT 0,
                instruments_failed integer NOT NULL DEFAULT 0,
                started_at timestamptz NULL,
                finished_at timestamptz NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_analysis_batches__scope UNIQUE (data_source_id, universe_id, as_of_date, ruleset_version_id),
                CONSTRAINT ck_analysis_batches__trigger CHECK (trigger IN ('SCHEDULED_EOD', 'MANUAL')),
                CONSTRAINT ck_analysis_batches__status CHECK (status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED')),
                CONSTRAINT ck_analysis_batches__counters CHECK (
                    instruments_total >= 0 AND instruments_completed >= 0 AND instruments_failed >= 0
                    AND instruments_completed + instruments_failed <= instruments_total
                )
            );

            -- One immutable evaluation of one instrument (the "analysis snapshot").
            -- primary_setup_id is a deferrable FK, added below, so a run and its setups insert in one transaction.
            CREATE TABLE analysis_runs (
                id uuid PRIMARY KEY,
                tenant_id uuid NULL REFERENCES tenants (id),
                data_source_id uuid NOT NULL REFERENCES data_sources (id),
                analysis_batch_id uuid NULL REFERENCES analysis_batches (id),
                instrument_id uuid NOT NULL REFERENCES instruments (id),
                candle_snapshot_id uuid NOT NULL REFERENCES candle_snapshots (id),
                ruleset_version_id uuid NOT NULL REFERENCES ruleset_versions (id),
                engine_version text NOT NULL,
                as_of_date date NOT NULL,
                status text NOT NULL,
                structure_state text NULL,
                transition_direction text NULL,
                signal_state text NOT NULL,
                primary_setup_id uuid NULL,
                summary jsonb NOT NULL DEFAULT '{}',
                result_hash text NULL,
                error_code text NULL,
                duration_ms integer NOT NULL DEFAULT 0,
                created_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_analysis_runs__idempotency
                    UNIQUE (data_source_id, instrument_id, candle_snapshot_id, ruleset_version_id),
                CONSTRAINT ck_analysis_runs__status CHECK (status IN ('COMPLETED', 'INSUFFICIENT_HISTORY', 'INVALID_INPUT', 'FAILED')),
                CONSTRAINT ck_analysis_runs__structure_state
                    CHECK (structure_state IS NULL OR structure_state IN ('BULLISH', 'BEARISH', 'SIDEWAYS', 'TRANSITION')),
                CONSTRAINT ck_analysis_runs__transition_direction
                    CHECK (transition_direction IS NULL OR transition_direction IN ('UP', 'DOWN')),
                CONSTRAINT ck_analysis_runs__signal_state CHECK (signal_state IN ('NO_TRADE', 'BUY_WATCH', 'ENTRY_CONFIRMED')),
                CONSTRAINT ck_analysis_runs__result_hash CHECK (result_hash IS NULL OR result_hash ~ '^[0-9a-f]{64}$'),
                CONSTRAINT ck_analysis_runs__completed_has_hash CHECK (status <> 'COMPLETED' OR result_hash IS NOT NULL),
                CONSTRAINT ck_analysis_runs__duration CHECK (duration_ms >= 0)
            );
            CREATE INDEX ix_analysis_runs__source_as_of_signal ON analysis_runs (data_source_id, as_of_date, signal_state);
            CREATE INDEX ix_analysis_runs__instrument_id_as_of_date ON analysis_runs (instrument_id, as_of_date DESC);
            CREATE INDEX ix_analysis_runs__analysis_batch_id ON analysis_runs (analysis_batch_id);
            CREATE TRIGGER tr_analysis_runs__immutable BEFORE UPDATE ON analysis_runs
                FOR EACH ROW EXECUTE FUNCTION reject_row_update();

            CREATE TABLE swing_points (
                id uuid PRIMARY KEY,
                analysis_run_id uuid NOT NULL REFERENCES analysis_runs (id) ON DELETE CASCADE,
                kind text NOT NULL,
                bar_index integer NOT NULL,
                bar_date date NOT NULL,
                price numeric(12,2) NOT NULL,
                label text NOT NULL,
                confirmed_at_index integer NOT NULL,
                confirmed_at_date date NOT NULL,
                broken_at_date date NULL,
                CONSTRAINT ck_swing_points__kind CHECK (kind IN ('HIGH', 'LOW')),
                CONSTRAINT ck_swing_points__label CHECK (label IN ('HH', 'LH', 'EQH', 'HL', 'LL', 'EQL', 'NONE')),
                CONSTRAINT ck_swing_points__label_matches_kind CHECK (
                    label = 'NONE'
                    OR (kind = 'HIGH' AND label IN ('HH', 'LH', 'EQH'))
                    OR (kind = 'LOW' AND label IN ('HL', 'LL', 'EQL'))
                ),
                CONSTRAINT ck_swing_points__price CHECK (price > 0),
                CONSTRAINT ck_swing_points__bar_index CHECK (bar_index >= 0),
                -- No look-ahead: a pivot is only known once its confirmation bar has closed (C-09).
                CONSTRAINT ck_swing_points__confirmed_after_bar
                    CHECK (confirmed_at_index >= bar_index AND confirmed_at_date >= bar_date)
            );
            CREATE INDEX ix_swing_points__analysis_run_id ON swing_points (analysis_run_id);
            CREATE TRIGGER tr_swing_points__immutable BEFORE UPDATE ON swing_points
                FOR EACH ROW EXECUTE FUNCTION reject_row_update();

            CREATE TABLE structure_events (
                id uuid PRIMARY KEY,
                analysis_run_id uuid NOT NULL REFERENCES analysis_runs (id) ON DELETE CASCADE,
                event_type text NOT NULL,
                direction text NOT NULL,
                level_price numeric(12,2) NOT NULL,
                level_swing_point_id uuid NULL REFERENCES swing_points (id) ON DELETE CASCADE,
                break_date date NOT NULL,
                break_close numeric(12,2) NOT NULL,
                close_inside_buffer boolean NOT NULL DEFAULT false,
                CONSTRAINT ck_structure_events__event_type CHECK (event_type IN ('BOS', 'CHOCH', 'WICK_BREACH')),
                CONSTRAINT ck_structure_events__direction CHECK (direction IN ('UP', 'DOWN')),
                CONSTRAINT ck_structure_events__prices CHECK (level_price > 0 AND break_close > 0)
            );
            CREATE INDEX ix_structure_events__analysis_run_id ON structure_events (analysis_run_id);
            CREATE TRIGGER tr_structure_events__immutable BEFORE UPDATE ON structure_events
                FOR EACH ROW EXECUTE FUNCTION reject_row_update();

            CREATE TABLE price_zones (
                id uuid PRIMARY KEY,
                analysis_run_id uuid NOT NULL REFERENCES analysis_runs (id) ON DELETE CASCADE,
                role text NOT NULL,
                low numeric(12,2) NOT NULL,
                high numeric(12,2) NOT NULL,
                touches smallint NOT NULL DEFAULT 0,
                strength_score smallint NOT NULL,
                strength_bucket text NOT NULL,
                status text NOT NULL,
                role_reversed boolean NOT NULL DEFAULT false,
                formed_at_date date NOT NULL,
                broken_at_date date NULL,
                member_swing_point_ids uuid[] NOT NULL DEFAULT '{}',
                distance_pct numeric(6,3) NULL,
                CONSTRAINT ck_price_zones__role CHECK (role IN ('SUPPORT', 'RESISTANCE')),
                CONSTRAINT ck_price_zones__bounds CHECK (low > 0 AND high >= low),
                CONSTRAINT ck_price_zones__touches CHECK (touches >= 0),
                CONSTRAINT ck_price_zones__strength_score CHECK (strength_score BETWEEN 0 AND 100),
                CONSTRAINT ck_price_zones__strength_bucket CHECK (strength_bucket IN ('WEAK', 'MODERATE', 'STRONG')),
                CONSTRAINT ck_price_zones__status CHECK (status IN ('ACTIVE', 'BROKEN_FLIPPED', 'RETIRED')),
                CONSTRAINT ck_price_zones__broken_after_formed CHECK (broken_at_date IS NULL OR broken_at_date >= formed_at_date)
            );
            CREATE INDEX ix_price_zones__analysis_run_id ON price_zones (analysis_run_id);
            CREATE TRIGGER tr_price_zones__immutable BEFORE UPDATE ON price_zones
                FOR EACH ROW EXECUTE FUNCTION reject_row_update();

            CREATE TABLE liquidity_events (
                id uuid PRIMARY KEY,
                analysis_run_id uuid NOT NULL REFERENCES analysis_runs (id) ON DELETE CASCADE,
                event_type text NOT NULL,
                level_price numeric(12,2) NOT NULL,
                first_date date NOT NULL,
                last_date date NOT NULL,
                refs jsonb NOT NULL DEFAULT '{}',
                CONSTRAINT ck_liquidity_events__event_type
                    CHECK (event_type IN ('EQUAL_HIGHS', 'EQUAL_LOWS', 'SWEEP_HIGH', 'SWEEP_LOW')),
                CONSTRAINT ck_liquidity_events__level_price CHECK (level_price > 0),
                CONSTRAINT ck_liquidity_events__dates CHECK (last_date >= first_date)
            );
            CREATE INDEX ix_liquidity_events__analysis_run_id ON liquidity_events (analysis_run_id);
            CREATE TRIGGER tr_liquidity_events__immutable BEFORE UPDATE ON liquidity_events
                FOR EACH ROW EXECUTE FUNCTION reject_row_update();

            CREATE TABLE detected_setups (
                id uuid PRIMARY KEY,
                analysis_run_id uuid NOT NULL REFERENCES analysis_runs (id) ON DELETE CASCADE,
                instrument_id uuid NOT NULL REFERENCES instruments (id),
                setup_key text NOT NULL,
                setup_type text NOT NULL,
                direction text NOT NULL,
                informational boolean NOT NULL,
                status text NOT NULL,
                detected_at_date date NOT NULL,
                status_changed_date date NOT NULL,
                trigger_price numeric(12,2) NULL,
                entry_price numeric(12,2) NULL,
                stop_price numeric(12,2) NULL,
                target_price numeric(12,2) NULL,
                target_source text NULL,
                rr numeric(8,4) NULL,
                rr_below_min boolean NOT NULL DEFAULT false,
                entry_window_open boolean NOT NULL DEFAULT false,
                paqs_score smallint NOT NULL,
                paqs_version text NOT NULL,
                paqs_components jsonb NOT NULL,
                anchor_zone_id uuid NULL REFERENCES price_zones (id) ON DELETE CASCADE,
                anchor_swing_point_id uuid NULL REFERENCES swing_points (id) ON DELETE CASCADE,
                evidence jsonb NOT NULL DEFAULT '[]',
                reason_codes text[] NOT NULL DEFAULT '{}',
                CONSTRAINT ck_detected_setups__setup_key CHECK (setup_key ~ '^[0-9a-f]{64}$'),
                CONSTRAINT ck_detected_setups__setup_type CHECK (
                    setup_type IN ('BREAKOUT_RETEST', 'SUPPORT_REJECTION', 'TREND_PULLBACK', 'LIQUIDITY_SWEEP_REVERSAL')
                ),
                CONSTRAINT ck_detected_setups__direction CHECK (direction IN ('LONG', 'SHORT')),
                -- Bearish setups are informational only in the NSE cash-equity MVP (C-12).
                CONSTRAINT ck_detected_setups__short_informational CHECK (direction <> 'SHORT' OR informational),
                CONSTRAINT ck_detected_setups__status CHECK (
                    status IN ('FORMING', 'AWAITING_CONFIRMATION', 'ENTRY_CONFIRMED', 'INVALIDATED', 'EXPIRED')
                ),
                CONSTRAINT ck_detected_setups__status_date CHECK (status_changed_date >= detected_at_date),
                CONSTRAINT ck_detected_setups__target_source
                    CHECK (target_source IS NULL OR target_source IN ('SETUP_SPECIFIC', 'ZONE', 'SWING_HIGH', 'MEASURED_MOVE')),
                CONSTRAINT ck_detected_setups__long_levels CHECK (
                    direction <> 'LONG' OR (
                        (stop_price IS NULL OR entry_price IS NULL OR stop_price < entry_price)
                        AND (entry_price IS NULL OR target_price IS NULL OR entry_price < target_price)
                    )
                ),
                CONSTRAINT ck_detected_setups__prices_positive CHECK (
                    COALESCE(trigger_price, 1) > 0 AND COALESCE(entry_price, 1) > 0
                    AND COALESCE(stop_price, 1) > 0 AND COALESCE(target_price, 1) > 0
                ),
                CONSTRAINT ck_detected_setups__rr CHECK (rr IS NULL OR rr > 0),
                CONSTRAINT ck_detected_setups__paqs_score CHECK (paqs_score BETWEEN 0 AND 100)
            );
            CREATE INDEX ix_detected_setups__analysis_run_id ON detected_setups (analysis_run_id);
            CREATE INDEX ix_detected_setups__setup_key ON detected_setups (setup_key);
            CREATE INDEX ix_detected_setups__instrument_id_status ON detected_setups (instrument_id, status);
            CREATE TRIGGER tr_detected_setups__immutable BEFORE UPDATE ON detected_setups
                FOR EACH ROW EXECUTE FUNCTION reject_row_update();

            ALTER TABLE analysis_runs
                ADD CONSTRAINT fk_analysis_runs__primary_setup_id FOREIGN KEY (primary_setup_id)
                REFERENCES detected_setups (id) DEFERRABLE INITIALLY DEFERRED;

            CREATE TABLE ai_explanations (
                id uuid PRIMARY KEY,
                tenant_id uuid NULL REFERENCES tenants (id),
                user_id uuid NULL REFERENCES users (id),
                analysis_run_id uuid NOT NULL REFERENCES analysis_runs (id),
                detected_setup_id uuid NULL REFERENCES detected_setups (id),
                kind text NOT NULL,
                question text NULL,
                prompt_version text NOT NULL,
                model_provider text NULL,
                model_id text NULL,
                context_hash text NOT NULL,
                output jsonb NULL,
                status text NOT NULL,
                validation_errors jsonb NULL,
                input_tokens integer NULL,
                output_tokens integer NULL,
                latency_ms integer NULL,
                cost_usd numeric(10,6) NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT ck_ai_explanations__kind CHECK (kind IN ('SETUP_SUMMARY', 'CHART_QA')),
                CONSTRAINT ck_ai_explanations__status CHECK (status IN ('COMPLETED', 'REJECTED_VALIDATION', 'FAILED', 'FALLBACK')),
                -- A question exists exactly for CHART_QA. Shared summaries of global runs have no tenant/user; Q&A has both.
                CONSTRAINT ck_ai_explanations__question CHECK ((kind = 'CHART_QA') = (question IS NOT NULL)),
                CONSTRAINT ck_ai_explanations__owner CHECK (
                    (tenant_id IS NULL) = (user_id IS NULL) AND (kind <> 'CHART_QA' OR tenant_id IS NOT NULL)
                ),
                -- FALLBACK uses a template, not a model.
                CONSTRAINT ck_ai_explanations__model CHECK (status = 'FALLBACK' OR (model_provider IS NOT NULL AND model_id IS NOT NULL)),
                CONSTRAINT ck_ai_explanations__usage CHECK (
                    COALESCE(input_tokens, 0) >= 0 AND COALESCE(output_tokens, 0) >= 0
                    AND COALESCE(latency_ms, 0) >= 0 AND COALESCE(cost_usd, 0) >= 0
                )
            );
            -- Cache: one completed summary per run, setup, prompt version and model.
            CREATE UNIQUE INDEX uq_ai_explanations__summary_cache
                ON ai_explanations (analysis_run_id, detected_setup_id, kind, prompt_version, model_id)
                WHERE kind = 'SETUP_SUMMARY' AND status = 'COMPLETED';
            CREATE INDEX ix_ai_explanations__tenant_user_created_at ON ai_explanations (tenant_id, user_id, created_at DESC);
            CREATE INDEX ix_ai_explanations__analysis_run_id ON ai_explanations (analysis_run_id);
            SQL);
    }

    public function down(): void
    {
        DB::unprepared(<<<'SQL'
            ALTER TABLE analysis_runs DROP CONSTRAINT IF EXISTS fk_analysis_runs__primary_setup_id;
            DROP TABLE IF EXISTS ai_explanations, detected_setups, liquidity_events, price_zones, structure_events,
                swing_points, analysis_runs, analysis_batches, candle_snapshots, ruleset_versions;
            DROP FUNCTION IF EXISTS guard_ruleset_content();
            DROP FUNCTION IF EXISTS reject_row_update();
            SQL);
    }
};
