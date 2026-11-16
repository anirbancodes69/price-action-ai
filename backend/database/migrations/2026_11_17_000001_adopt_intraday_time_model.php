<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/*
 * Intraday time model and snapshots by reference (ADR-015, ARC-03 §2.2; direction ADR-014).
 *
 * - Bars are keyed by bar_start (timestamptz); timeframes 1m/5m/15m/1D; trade_date stays as the IST session date.
 * - Bar corrections keep their previous values in candle_revisions (trigger, so no writer can forget it).
 * - candle_snapshots reference a bar range plus content hash; the payload column is dropped.
 * - analysis runs link several inputs (analysis_run_inputs) and carry as_of_ts.
 * - Derived, trading and backtest rows gain timestamps beside their dates.
 * - risk_profiles gains the intraday account limits (TRD-05 §8).
 *
 * Existing rows are backfilled: daily bars start at the 09:15 IST session open, daily "as of" moments are the
 * 15:30 IST close. No production data exists (ADR-015 decision 10); the backfill keeps development databases valid.
 * Immutability triggers are disabled only around the backfill updates.
 */
return new class extends Migration
{
    public function up(): void
    {
        DB::unprepared(<<<'SQL'
            -- ---------------------------------------------------------------- candles
            ALTER TABLE candles ADD COLUMN bar_start timestamptz NULL;
            UPDATE candles SET bar_start = (trade_date + time '09:15') AT TIME ZONE 'Asia/Kolkata';
            ALTER TABLE candles ALTER COLUMN bar_start SET NOT NULL;
            ALTER TABLE candles DROP CONSTRAINT candles_pkey;
            ALTER TABLE candles ADD PRIMARY KEY (data_source_id, instrument_id, timeframe, bar_start);
            ALTER TABLE candles DROP CONSTRAINT ck_candles__timeframe;
            ALTER TABLE candles ADD CONSTRAINT ck_candles__timeframe CHECK (timeframe IN ('1m', '5m', '15m', '1D'));
            -- trade_date is the IST session date of the bar; bars start on a whole minute.
            ALTER TABLE candles ADD CONSTRAINT ck_candles__session_date
                CHECK ((bar_start AT TIME ZONE 'Asia/Kolkata')::date = trade_date);
            ALTER TABLE candles ADD CONSTRAINT ck_candles__whole_minute CHECK (date_trunc('minute', bar_start) = bar_start);
            DROP INDEX ix_candles__instrument_id_trade_date;
            CREATE INDEX ix_candles__instrument_timeframe_trade_date ON candles (instrument_id, timeframe, trade_date);

            -- ---------------------------------------------------------------- candle_revisions
            CREATE TABLE candle_revisions (
                data_source_id uuid NOT NULL,
                instrument_id uuid NOT NULL,
                timeframe text NOT NULL,
                bar_start timestamptz NOT NULL,
                revision smallint NOT NULL,
                open numeric(12,2) NOT NULL,
                high numeric(12,2) NOT NULL,
                low numeric(12,2) NOT NULL,
                close numeric(12,2) NOT NULL,
                volume bigint NOT NULL,
                replaced_at timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY (data_source_id, instrument_id, timeframe, bar_start, revision),
                CONSTRAINT fk_candle_revisions__candle FOREIGN KEY (data_source_id, instrument_id, timeframe, bar_start)
                    REFERENCES candles (data_source_id, instrument_id, timeframe, bar_start) ON DELETE CASCADE,
                CONSTRAINT ck_candle_revisions__revision CHECK (revision >= 1)
            );
            CREATE TRIGGER tr_candle_revisions__immutable BEFORE UPDATE ON candle_revisions
                FOR EACH ROW EXECUTE FUNCTION reject_row_update();

            -- Any change to a stored bar's values archives the old values and increments the revision (ADR-015 §4).
            CREATE OR REPLACE FUNCTION keep_candle_revision() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF (NEW.data_source_id, NEW.instrument_id, NEW.timeframe, NEW.bar_start)
                   IS DISTINCT FROM (OLD.data_source_id, OLD.instrument_id, OLD.timeframe, OLD.bar_start) THEN
                    RAISE EXCEPTION 'the key of a candle cannot change' USING ERRCODE = 'integrity_constraint_violation';
                END IF;
                IF (NEW.open, NEW.high, NEW.low, NEW.close, NEW.volume)
                   IS DISTINCT FROM (OLD.open, OLD.high, OLD.low, OLD.close, OLD.volume) THEN
                    INSERT INTO candle_revisions
                        (data_source_id, instrument_id, timeframe, bar_start, revision, open, high, low, close, volume)
                    VALUES (OLD.data_source_id, OLD.instrument_id, OLD.timeframe, OLD.bar_start, OLD.revision,
                        OLD.open, OLD.high, OLD.low, OLD.close, OLD.volume);
                    NEW.revision := OLD.revision + 1;
                    NEW.updated_at := now();
                ELSE
                    NEW.revision := OLD.revision;
                END IF;
                RETURN NEW;
            END
            $$;
            CREATE TRIGGER tr_candles__keep_revision BEFORE UPDATE ON candles
                FOR EACH ROW EXECUTE FUNCTION keep_candle_revision();

            -- ---------------------------------------------------------------- candle_snapshots
            ALTER TABLE candle_snapshots DISABLE TRIGGER tr_candle_snapshots__immutable;
            ALTER TABLE candle_snapshots
                ADD COLUMN from_bar_start timestamptz NULL,
                ADD COLUMN to_bar_start timestamptz NULL,
                ADD COLUMN max_revision smallint NULL;
            UPDATE candle_snapshots SET
                from_bar_start = (from_date + time '09:15') AT TIME ZONE 'Asia/Kolkata',
                to_bar_start = (to_date + time '09:15') AT TIME ZONE 'Asia/Kolkata',
                max_revision = 1;
            ALTER TABLE candle_snapshots
                ALTER COLUMN from_bar_start SET NOT NULL,
                ALTER COLUMN to_bar_start SET NOT NULL,
                ALTER COLUMN max_revision SET NOT NULL;
            ALTER TABLE candle_snapshots ENABLE TRIGGER tr_candle_snapshots__immutable;
            ALTER TABLE candle_snapshots DROP COLUMN payload;
            ALTER TABLE candle_snapshots DROP CONSTRAINT ck_candle_snapshots__timeframe;
            ALTER TABLE candle_snapshots ADD CONSTRAINT ck_candle_snapshots__timeframe
                CHECK (timeframe IN ('1m', '5m', '15m', '1D'));
            -- Intraday inputs are unadjusted; daily context is adjusted (TRD-01 §4).
            ALTER TABLE candle_snapshots DROP CONSTRAINT ck_candle_snapshots__price_basis;
            ALTER TABLE candle_snapshots ADD CONSTRAINT ck_candle_snapshots__price_basis
                CHECK (price_basis IN ('ADJUSTED', 'UNADJUSTED'));
            ALTER TABLE candle_snapshots ADD CONSTRAINT ck_candle_snapshots__bar_range CHECK (to_bar_start >= from_bar_start);
            ALTER TABLE candle_snapshots ADD CONSTRAINT ck_candle_snapshots__max_revision CHECK (max_revision >= 1);

            -- ---------------------------------------------------------------- analysis runs and their inputs
            CREATE TABLE analysis_run_inputs (
                analysis_run_id uuid NOT NULL REFERENCES analysis_runs (id) ON DELETE CASCADE,
                role text NOT NULL,
                candle_snapshot_id uuid NOT NULL REFERENCES candle_snapshots (id),
                PRIMARY KEY (analysis_run_id, role),
                CONSTRAINT ck_analysis_run_inputs__role CHECK (role IN ('PRIMARY_5M', 'CONTEXT_15M', 'DAILY_CONTEXT'))
            );
            CREATE INDEX ix_analysis_run_inputs__candle_snapshot_id ON analysis_run_inputs (candle_snapshot_id);
            CREATE TRIGGER tr_analysis_run_inputs__immutable BEFORE UPDATE ON analysis_run_inputs
                FOR EACH ROW EXECUTE FUNCTION reject_row_update();

            ALTER TABLE analysis_runs DISABLE TRIGGER tr_analysis_runs__immutable;
            ALTER TABLE analysis_runs ADD COLUMN as_of_ts timestamptz NULL;
            UPDATE analysis_runs SET as_of_ts = (as_of_date + time '15:30') AT TIME ZONE 'Asia/Kolkata';
            -- Pre-intraday (daily) runs keep their single snapshot as daily context.
            INSERT INTO analysis_run_inputs (analysis_run_id, role, candle_snapshot_id)
                SELECT id, 'DAILY_CONTEXT', candle_snapshot_id FROM analysis_runs;
            ALTER TABLE analysis_runs ALTER COLUMN as_of_ts SET NOT NULL;
            ALTER TABLE analysis_runs ENABLE TRIGGER tr_analysis_runs__immutable;
            ALTER TABLE analysis_runs DROP CONSTRAINT uq_analysis_runs__idempotency;
            ALTER TABLE analysis_runs DROP COLUMN candle_snapshot_id;
            ALTER TABLE analysis_runs ADD CONSTRAINT uq_analysis_runs__idempotency
                UNIQUE (data_source_id, instrument_id, ruleset_version_id, as_of_ts);
            ALTER TABLE analysis_runs ADD CONSTRAINT ck_analysis_runs__session_date
                CHECK ((as_of_ts AT TIME ZONE 'Asia/Kolkata')::date = as_of_date);
            DROP INDEX ix_analysis_runs__source_as_of_signal;
            DROP INDEX ix_analysis_runs__instrument_id_as_of_date;
            CREATE INDEX ix_analysis_runs__source_as_of_ts_signal ON analysis_runs (data_source_id, as_of_ts, signal_state);
            CREATE INDEX ix_analysis_runs__instrument_id_as_of_ts ON analysis_runs (instrument_id, as_of_ts DESC);

            ALTER TABLE analysis_batches ADD COLUMN as_of_ts timestamptz NULL;
            UPDATE analysis_batches SET as_of_ts = (as_of_date + time '15:30') AT TIME ZONE 'Asia/Kolkata';
            ALTER TABLE analysis_batches ALTER COLUMN as_of_ts SET NOT NULL;
            ALTER TABLE analysis_batches DROP CONSTRAINT uq_analysis_batches__scope;
            ALTER TABLE analysis_batches ADD CONSTRAINT uq_analysis_batches__scope
                UNIQUE (data_source_id, universe_id, ruleset_version_id, as_of_ts);
            ALTER TABLE analysis_batches DROP CONSTRAINT ck_analysis_batches__trigger;
            ALTER TABLE analysis_batches ADD CONSTRAINT ck_analysis_batches__trigger
                CHECK (trigger IN ('SCHEDULED_EOD', 'BAR_CLOSE', 'MANUAL'));
            ALTER TABLE analysis_batches ADD CONSTRAINT ck_analysis_batches__session_date
                CHECK ((as_of_ts AT TIME ZONE 'Asia/Kolkata')::date = as_of_date);

            -- ---------------------------------------------------------------- derived rows: timeframe and bar times
            ALTER TABLE swing_points DISABLE TRIGGER tr_swing_points__immutable;
            ALTER TABLE swing_points
                ADD COLUMN timeframe text NULL,
                ADD COLUMN bar_start timestamptz NULL,
                ADD COLUMN confirmed_at_bar_start timestamptz NULL;
            UPDATE swing_points SET
                timeframe = '1D',
                bar_start = (bar_date + time '09:15') AT TIME ZONE 'Asia/Kolkata',
                confirmed_at_bar_start = (confirmed_at_date + time '09:15') AT TIME ZONE 'Asia/Kolkata';
            ALTER TABLE swing_points
                ALTER COLUMN timeframe SET NOT NULL,
                ALTER COLUMN bar_start SET NOT NULL,
                ALTER COLUMN confirmed_at_bar_start SET NOT NULL;
            ALTER TABLE swing_points ENABLE TRIGGER tr_swing_points__immutable;
            ALTER TABLE swing_points ADD CONSTRAINT ck_swing_points__timeframe CHECK (timeframe IN ('1m', '5m', '15m', '1D'));
            -- No look-ahead in time as well as in index (C-09, TRD-02 §3.4).
            ALTER TABLE swing_points ADD CONSTRAINT ck_swing_points__confirmed_after_bar_start
                CHECK (confirmed_at_bar_start >= bar_start);

            ALTER TABLE structure_events DISABLE TRIGGER tr_structure_events__immutable;
            ALTER TABLE structure_events ADD COLUMN timeframe text NULL, ADD COLUMN break_bar_start timestamptz NULL;
            UPDATE structure_events SET timeframe = '1D',
                break_bar_start = (break_date + time '09:15') AT TIME ZONE 'Asia/Kolkata';
            ALTER TABLE structure_events ALTER COLUMN timeframe SET NOT NULL, ALTER COLUMN break_bar_start SET NOT NULL;
            ALTER TABLE structure_events ENABLE TRIGGER tr_structure_events__immutable;
            ALTER TABLE structure_events ADD CONSTRAINT ck_structure_events__timeframe
                CHECK (timeframe IN ('1m', '5m', '15m', '1D'));

            ALTER TABLE price_zones DISABLE TRIGGER tr_price_zones__immutable;
            ALTER TABLE price_zones ADD COLUMN formed_at_bar_start timestamptz NULL, ADD COLUMN broken_at_bar_start timestamptz NULL;
            UPDATE price_zones SET
                formed_at_bar_start = (formed_at_date + time '09:15') AT TIME ZONE 'Asia/Kolkata',
                broken_at_bar_start = (broken_at_date + time '09:15') AT TIME ZONE 'Asia/Kolkata';
            ALTER TABLE price_zones ALTER COLUMN formed_at_bar_start SET NOT NULL;
            ALTER TABLE price_zones ENABLE TRIGGER tr_price_zones__immutable;
            ALTER TABLE price_zones ADD CONSTRAINT ck_price_zones__broken_after_formed_ts
                CHECK (broken_at_bar_start IS NULL OR broken_at_bar_start >= formed_at_bar_start);

            ALTER TABLE liquidity_events DISABLE TRIGGER tr_liquidity_events__immutable;
            ALTER TABLE liquidity_events ADD COLUMN first_bar_start timestamptz NULL, ADD COLUMN last_bar_start timestamptz NULL;
            UPDATE liquidity_events SET
                first_bar_start = (first_date + time '09:15') AT TIME ZONE 'Asia/Kolkata',
                last_bar_start = (last_date + time '09:15') AT TIME ZONE 'Asia/Kolkata';
            ALTER TABLE liquidity_events ALTER COLUMN first_bar_start SET NOT NULL, ALTER COLUMN last_bar_start SET NOT NULL;
            ALTER TABLE liquidity_events ENABLE TRIGGER tr_liquidity_events__immutable;
            ALTER TABLE liquidity_events ADD CONSTRAINT ck_liquidity_events__bar_range CHECK (last_bar_start >= first_bar_start);

            ALTER TABLE detected_setups DISABLE TRIGGER tr_detected_setups__immutable;
            ALTER TABLE detected_setups
                ADD COLUMN detected_at_bar_start timestamptz NULL,
                ADD COLUMN signal_at timestamptz NULL,
                ADD COLUMN valid_until timestamptz NULL;
            UPDATE detected_setups SET detected_at_bar_start = (detected_at_date + time '09:15') AT TIME ZONE 'Asia/Kolkata';
            ALTER TABLE detected_setups ALTER COLUMN detected_at_bar_start SET NOT NULL;
            ALTER TABLE detected_setups ENABLE TRIGGER tr_detected_setups__immutable;
            -- pa-intraday vocabulary (TRD-01 §7); the retired pa-core types stay valid for existing immutable rows.
            ALTER TABLE detected_setups DROP CONSTRAINT ck_detected_setups__setup_type;
            ALTER TABLE detected_setups ADD CONSTRAINT ck_detected_setups__setup_type CHECK (setup_type IN (
                'OPENING_RANGE_BREAKOUT', 'PREV_DAY_HIGH_BREAK', 'PREV_DAY_LOW_BREAK', 'BREAKOUT_RETEST',
                'TREND_CONTINUATION', 'LIQUIDITY_SWEEP_REVERSAL', 'SUPPORT_REJECTION', 'TREND_PULLBACK'
            ));
            ALTER TABLE detected_setups ADD CONSTRAINT ck_detected_setups__validity
                CHECK (valid_until IS NULL OR (signal_at IS NOT NULL AND valid_until >= signal_at));

            -- ---------------------------------------------------------------- ingestion runs
            ALTER TABLE ingestion_runs ADD COLUMN timeframe text NULL, ADD COLUMN bar_start timestamptz NULL;
            ALTER TABLE ingestion_runs DROP CONSTRAINT ck_ingestion_runs__kind;
            ALTER TABLE ingestion_runs ADD CONSTRAINT ck_ingestion_runs__kind CHECK (kind IN (
                'INSTRUMENT_MASTER', 'DAILY_CANDLES', 'INTRADAY_BARS', 'BACKFILL', 'CORPORATE_ACTIONS', 'UNIVERSE'
            ));
            ALTER TABLE ingestion_runs ADD CONSTRAINT ck_ingestion_runs__timeframe
                CHECK (timeframe IS NULL OR timeframe IN ('1m', '5m', '15m', '1D'));
            -- An intraday run fetches one bar close of one timeframe.
            ALTER TABLE ingestion_runs ADD CONSTRAINT ck_ingestion_runs__intraday_bar CHECK (
                kind <> 'INTRADAY_BARS' OR (timeframe IN ('1m', '5m', '15m') AND bar_start IS NOT NULL)
            );
            CREATE UNIQUE INDEX uq_ingestion_runs__active_bar ON ingestion_runs (data_source_id, kind, timeframe, bar_start)
                WHERE status IN ('QUEUED', 'RUNNING') AND bar_start IS NOT NULL;

            -- ---------------------------------------------------------------- trading tables
            ALTER TABLE trade_plans ADD COLUMN triggered_at timestamptz NULL, ADD COLUMN valid_until timestamptz NULL;

            ALTER TABLE paper_trades ADD COLUMN entry_at timestamptz NULL, ADD COLUMN exit_at timestamptz NULL;
            UPDATE paper_trades SET
                entry_at = (entry_date + time '09:15') AT TIME ZONE 'Asia/Kolkata',
                exit_at = (exit_date + time '15:30') AT TIME ZONE 'Asia/Kolkata';
            ALTER TABLE paper_trades ALTER COLUMN entry_at SET NOT NULL;
            ALTER TABLE paper_trades DROP CONSTRAINT ck_paper_trades__exit_reason;
            ALTER TABLE paper_trades ADD CONSTRAINT ck_paper_trades__exit_reason CHECK (
                exit_reason IS NULL OR exit_reason IN (
                    'STOP', 'STOP_GAP', 'STOP_COLLISION', 'TARGET', 'TARGET_GAP', 'STRUCTURE_EXIT', 'MANUAL',
                    'SESSION_END', 'CORPORATE_ACTION_EXIT'
                )
            );
            ALTER TABLE paper_trades ADD CONSTRAINT ck_paper_trades__exit_times CHECK (
                (status = 'OPEN') = (exit_at IS NULL) AND (exit_at IS NULL OR exit_at >= entry_at)
            );

            ALTER TABLE backtest_trades
                ADD COLUMN signal_at timestamptz NULL,
                ADD COLUMN entry_at timestamptz NULL,
                ADD COLUMN exit_at timestamptz NULL;
            UPDATE backtest_trades SET
                signal_at = (signal_date + time '15:30') AT TIME ZONE 'Asia/Kolkata',
                entry_at = (entry_date + time '09:15') AT TIME ZONE 'Asia/Kolkata',
                exit_at = (exit_date + time '15:30') AT TIME ZONE 'Asia/Kolkata';
            ALTER TABLE backtest_trades ALTER COLUMN signal_at SET NOT NULL;
            -- A signal at a bar close fills on a later bar (C-09, TRD-06 BT-02). signal_at is the end of the signal bar and
            -- entry_at the start of the fill bar, so a fill at the very next open has entry_at = signal_at; a fill inside
            -- the signal bar would start before its end. Intraday the session date may be equal.
            ALTER TABLE backtest_trades DROP CONSTRAINT ck_backtest_trades__fill_after_signal;
            ALTER TABLE backtest_trades ADD CONSTRAINT ck_backtest_trades__fill_after_signal
                CHECK (entry_date IS NULL OR entry_date >= signal_date);
            ALTER TABLE backtest_trades ADD CONSTRAINT ck_backtest_trades__fill_after_signal_ts
                CHECK (entry_at IS NULL OR entry_at >= signal_at);
            ALTER TABLE backtest_trades ADD CONSTRAINT ck_backtest_trades__filled_has_entry_at
                CHECK (outcome <> 'FILLED' OR entry_at IS NOT NULL);
            ALTER TABLE backtest_trades ADD CONSTRAINT ck_backtest_trades__exit_after_entry_ts
                CHECK (exit_at IS NULL OR (entry_at IS NOT NULL AND exit_at >= entry_at));
            ALTER TABLE backtest_trades DROP CONSTRAINT ck_backtest_trades__setup_type;
            ALTER TABLE backtest_trades ADD CONSTRAINT ck_backtest_trades__setup_type CHECK (setup_type IN (
                'OPENING_RANGE_BREAKOUT', 'PREV_DAY_HIGH_BREAK', 'PREV_DAY_LOW_BREAK', 'BREAKOUT_RETEST',
                'TREND_CONTINUATION', 'LIQUIDITY_SWEEP_REVERSAL', 'SUPPORT_REJECTION', 'TREND_PULLBACK'
            ));

            -- ---------------------------------------------------------------- risk profiles (TRD-05 §8, TRD-01 §6 ranges)
            ALTER TABLE risk_profiles
                ADD COLUMN max_position_value numeric(14,2) NULL,
                ADD COLUMN daily_loss_limit_pct numeric(6,3) NULL,
                ADD COLUMN max_consecutive_losses smallint NULL,
                ADD COLUMN max_open_risk_pct numeric(6,3) NULL;
            -- The daily-scope heat and position-% limits are superseded; kept nullable for existing rows.
            ALTER TABLE risk_profiles ALTER COLUMN max_portfolio_heat_pct DROP NOT NULL, ALTER COLUMN max_position_pct DROP NOT NULL;
            ALTER TABLE risk_profiles ADD CONSTRAINT ck_risk_profiles__max_position_value
                CHECK (max_position_value IS NULL OR max_position_value BETWEEN 5000 AND 1000000);
            ALTER TABLE risk_profiles ADD CONSTRAINT ck_risk_profiles__daily_loss_limit_pct
                CHECK (daily_loss_limit_pct IS NULL OR daily_loss_limit_pct BETWEEN 0.5 AND 5.0);
            ALTER TABLE risk_profiles ADD CONSTRAINT ck_risk_profiles__max_consecutive_losses
                CHECK (max_consecutive_losses IS NULL OR max_consecutive_losses BETWEEN 1 AND 10);
            ALTER TABLE risk_profiles ADD CONSTRAINT ck_risk_profiles__max_open_risk_pct
                CHECK (max_open_risk_pct IS NULL OR max_open_risk_pct BETWEEN 0.25 AND 5.0);

            -- ---------------------------------------------------------------- grants (same function, two new tables)
            CREATE OR REPLACE FUNCTION apply_role_grants() RETURNS void LANGUAGE plpgsql AS $$
            DECLARE
                backend_exists boolean := EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_backend');
                engine_exists boolean := EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_engine');
                laravel_owned text[] := ARRAY[
                    'users', 'password_reset_tokens', 'cache', 'cache_locks', 'jobs', 'job_batches', 'failed_jobs',
                    'tenants', 'tenant_memberships', 'user_profiles', 'onboarding_progress', 'trading_preferences',
                    'risk_profiles', 'subscription_entitlements', 'provider_connections', 'data_sources',
                    'data_source_selections', 'universes', 'market_calendar', 'ruleset_versions', 'watchlists',
                    'watchlist_items', 'paper_accounts', 'actual_trades', 'actual_trade_fills', 'notifications'
                ];
                engine_reads text[] := ARRAY[
                    'data_sources', 'data_source_selections', 'universes', 'market_calendar', 'ruleset_versions',
                    'trading_preferences', 'risk_profiles', 'paper_accounts'
                ];
                engine_owned text[] := ARRAY[
                    'instruments', 'instrument_provider_refs', 'instrument_snapshots', 'universe_memberships', 'candles',
                    'corporate_actions', 'ingestion_runs', 'data_quality_issues', 'analysis_batches', 'ai_explanations',
                    'backtest_trades'
                ];
                engine_append_only text[] := ARRAY[
                    'analysis_runs', 'analysis_run_inputs', 'swing_points', 'structure_events', 'price_zones',
                    'liquidity_events', 'detected_setups', 'candle_revisions'
                ];
            BEGIN
                IF backend_exists THEN
                    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM app_backend;
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM app_backend;
                    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON %s TO app_backend',
                        (SELECT string_agg(quote_ident(t), ', ') FROM unnest(laravel_owned) t));
                    EXECUTE format('GRANT SELECT ON %s TO app_backend',
                        (SELECT string_agg(quote_ident(t), ', ')
                           FROM unnest(engine_owned || engine_append_only || ARRAY['candle_snapshots']) t));
                    GRANT SELECT, INSERT, UPDATE, DELETE ON trade_plans, journal_entries TO app_backend;
                    GRANT SELECT ON paper_trades TO app_backend;
                    GRANT UPDATE (current_stop, exit_requested_on, updated_at) ON paper_trades TO app_backend;
                    GRANT SELECT, INSERT ON paper_trade_events TO app_backend;
                    GRANT SELECT, INSERT, DELETE ON backtest_runs TO app_backend;
                    GRANT UPDATE (status) ON backtest_runs TO app_backend;
                    GRANT SELECT, INSERT ON audit_logs TO app_backend;
                END IF;

                IF engine_exists THEN
                    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM app_engine;
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM app_engine;
                    EXECUTE format('GRANT SELECT ON %s TO app_engine',
                        (SELECT string_agg(quote_ident(t), ', ') FROM unnest(engine_reads) t));
                    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON %s TO app_engine',
                        (SELECT string_agg(quote_ident(t), ', ') FROM unnest(engine_owned) t));
                    EXECUTE format('GRANT SELECT, INSERT, DELETE ON %s TO app_engine',
                        (SELECT string_agg(quote_ident(t), ', ') FROM unnest(engine_append_only) t));
                    GRANT SELECT, INSERT ON candle_snapshots TO app_engine;
                    -- trade_plans: bar-close status transitions only (TRD-07 §4).
                    GRANT SELECT ON trade_plans TO app_engine;
                    GRANT UPDATE (status, status_reason, triggered_on, triggered_at, lock_version, updated_at)
                        ON trade_plans TO app_engine;
                    GRANT SELECT, INSERT, UPDATE ON paper_trades TO app_engine;
                    GRANT SELECT, INSERT ON paper_trade_events TO app_engine;
                    GRANT SELECT, INSERT ON journal_entries TO app_engine;
                    GRANT SELECT ON backtest_runs TO app_engine;
                    GRANT UPDATE (status, progress_pct, input_hash, engine_version, metrics, equity_curve, flags,
                        error_code, started_at, finished_at) ON backtest_runs TO app_engine;
                    GRANT SELECT, INSERT ON audit_logs TO app_engine;
                END IF;
            END
            $$;

            SELECT apply_role_grants();
            SQL);
    }

    public function down(): void
    {
        DB::unprepared(<<<'SQL'
            ALTER TABLE risk_profiles
                DROP CONSTRAINT ck_risk_profiles__max_position_value, DROP CONSTRAINT ck_risk_profiles__daily_loss_limit_pct,
                DROP CONSTRAINT ck_risk_profiles__max_consecutive_losses, DROP CONSTRAINT ck_risk_profiles__max_open_risk_pct,
                DROP COLUMN max_position_value, DROP COLUMN daily_loss_limit_pct,
                DROP COLUMN max_consecutive_losses, DROP COLUMN max_open_risk_pct;
            UPDATE risk_profiles SET max_portfolio_heat_pct = COALESCE(max_portfolio_heat_pct, 5),
                max_position_pct = COALESCE(max_position_pct, 25);
            ALTER TABLE risk_profiles ALTER COLUMN max_portfolio_heat_pct SET NOT NULL, ALTER COLUMN max_position_pct SET NOT NULL;

            ALTER TABLE backtest_trades DROP CONSTRAINT ck_backtest_trades__setup_type;
            ALTER TABLE backtest_trades ADD CONSTRAINT ck_backtest_trades__setup_type CHECK (
                setup_type IN ('BREAKOUT_RETEST', 'SUPPORT_REJECTION', 'TREND_PULLBACK', 'LIQUIDITY_SWEEP_REVERSAL')
            );
            ALTER TABLE backtest_trades DROP CONSTRAINT ck_backtest_trades__fill_after_signal,
                DROP CONSTRAINT ck_backtest_trades__fill_after_signal_ts, DROP CONSTRAINT ck_backtest_trades__filled_has_entry_at,
                DROP CONSTRAINT ck_backtest_trades__exit_after_entry_ts,
                DROP COLUMN signal_at, DROP COLUMN entry_at, DROP COLUMN exit_at;
            ALTER TABLE backtest_trades ADD CONSTRAINT ck_backtest_trades__fill_after_signal
                CHECK (entry_date IS NULL OR entry_date > signal_date);

            ALTER TABLE paper_trades DROP CONSTRAINT ck_paper_trades__exit_times, DROP CONSTRAINT ck_paper_trades__exit_reason,
                DROP COLUMN entry_at, DROP COLUMN exit_at;
            ALTER TABLE paper_trades ADD CONSTRAINT ck_paper_trades__exit_reason CHECK (
                exit_reason IS NULL OR exit_reason IN (
                    'STOP', 'STOP_GAP', 'STOP_COLLISION', 'TARGET', 'TARGET_GAP', 'STRUCTURE_EXIT', 'MANUAL',
                    'CORPORATE_ACTION_EXIT'
                )
            );
            ALTER TABLE trade_plans DROP COLUMN triggered_at, DROP COLUMN valid_until;

            DROP INDEX uq_ingestion_runs__active_bar;
            ALTER TABLE ingestion_runs DROP CONSTRAINT ck_ingestion_runs__intraday_bar, DROP CONSTRAINT ck_ingestion_runs__timeframe,
                DROP CONSTRAINT ck_ingestion_runs__kind, DROP COLUMN timeframe, DROP COLUMN bar_start;
            ALTER TABLE ingestion_runs ADD CONSTRAINT ck_ingestion_runs__kind
                CHECK (kind IN ('INSTRUMENT_MASTER', 'DAILY_CANDLES', 'BACKFILL', 'CORPORATE_ACTIONS', 'UNIVERSE'));

            ALTER TABLE detected_setups DROP CONSTRAINT ck_detected_setups__validity, DROP CONSTRAINT ck_detected_setups__setup_type,
                DROP COLUMN detected_at_bar_start, DROP COLUMN signal_at, DROP COLUMN valid_until;
            ALTER TABLE detected_setups ADD CONSTRAINT ck_detected_setups__setup_type CHECK (
                setup_type IN ('BREAKOUT_RETEST', 'SUPPORT_REJECTION', 'TREND_PULLBACK', 'LIQUIDITY_SWEEP_REVERSAL')
            );
            ALTER TABLE liquidity_events DROP CONSTRAINT ck_liquidity_events__bar_range,
                DROP COLUMN first_bar_start, DROP COLUMN last_bar_start;
            ALTER TABLE price_zones DROP CONSTRAINT ck_price_zones__broken_after_formed_ts,
                DROP COLUMN formed_at_bar_start, DROP COLUMN broken_at_bar_start;
            ALTER TABLE structure_events DROP CONSTRAINT ck_structure_events__timeframe,
                DROP COLUMN timeframe, DROP COLUMN break_bar_start;
            ALTER TABLE swing_points DROP CONSTRAINT ck_swing_points__timeframe,
                DROP CONSTRAINT ck_swing_points__confirmed_after_bar_start,
                DROP COLUMN timeframe, DROP COLUMN bar_start, DROP COLUMN confirmed_at_bar_start;

            ALTER TABLE analysis_batches DROP CONSTRAINT ck_analysis_batches__session_date,
                DROP CONSTRAINT ck_analysis_batches__trigger, DROP CONSTRAINT uq_analysis_batches__scope, DROP COLUMN as_of_ts;
            ALTER TABLE analysis_batches ADD CONSTRAINT uq_analysis_batches__scope
                UNIQUE (data_source_id, universe_id, as_of_date, ruleset_version_id);
            ALTER TABLE analysis_batches ADD CONSTRAINT ck_analysis_batches__trigger CHECK (trigger IN ('SCHEDULED_EOD', 'MANUAL'));

            DROP INDEX ix_analysis_runs__source_as_of_ts_signal;
            DROP INDEX ix_analysis_runs__instrument_id_as_of_ts;
            ALTER TABLE analysis_runs DROP CONSTRAINT ck_analysis_runs__session_date, DROP CONSTRAINT uq_analysis_runs__idempotency;
            ALTER TABLE analysis_runs DISABLE TRIGGER tr_analysis_runs__immutable;
            ALTER TABLE analysis_runs ADD COLUMN candle_snapshot_id uuid NULL REFERENCES candle_snapshots (id);
            UPDATE analysis_runs r SET candle_snapshot_id = (
                SELECT i.candle_snapshot_id FROM analysis_run_inputs i WHERE i.analysis_run_id = r.id
                ORDER BY i.role DESC LIMIT 1
            );
            ALTER TABLE analysis_runs ALTER COLUMN candle_snapshot_id SET NOT NULL;
            ALTER TABLE analysis_runs ENABLE TRIGGER tr_analysis_runs__immutable;
            ALTER TABLE analysis_runs DROP COLUMN as_of_ts;
            ALTER TABLE analysis_runs ADD CONSTRAINT uq_analysis_runs__idempotency
                UNIQUE (data_source_id, instrument_id, candle_snapshot_id, ruleset_version_id);
            CREATE INDEX ix_analysis_runs__source_as_of_signal ON analysis_runs (data_source_id, as_of_date, signal_state);
            CREATE INDEX ix_analysis_runs__instrument_id_as_of_date ON analysis_runs (instrument_id, as_of_date DESC);
            DROP TABLE analysis_run_inputs;

            ALTER TABLE candle_snapshots DROP CONSTRAINT ck_candle_snapshots__max_revision,
                DROP CONSTRAINT ck_candle_snapshots__bar_range, DROP CONSTRAINT ck_candle_snapshots__price_basis,
                DROP CONSTRAINT ck_candle_snapshots__timeframe,
                DROP COLUMN from_bar_start, DROP COLUMN to_bar_start, DROP COLUMN max_revision;
            ALTER TABLE candle_snapshots ADD COLUMN payload bytea NOT NULL DEFAULT ''::bytea;
            ALTER TABLE candle_snapshots ALTER COLUMN payload DROP DEFAULT;
            ALTER TABLE candle_snapshots ADD CONSTRAINT ck_candle_snapshots__timeframe CHECK (timeframe IN ('1D'));
            ALTER TABLE candle_snapshots ADD CONSTRAINT ck_candle_snapshots__price_basis CHECK (price_basis IN ('ADJUSTED'));

            DROP TRIGGER tr_candles__keep_revision ON candles;
            DROP FUNCTION keep_candle_revision();
            DROP TABLE candle_revisions;
            DROP INDEX ix_candles__instrument_timeframe_trade_date;
            CREATE INDEX ix_candles__instrument_id_trade_date ON candles (instrument_id, trade_date);
            ALTER TABLE candles DROP CONSTRAINT ck_candles__whole_minute, DROP CONSTRAINT ck_candles__session_date,
                DROP CONSTRAINT ck_candles__timeframe;
            DELETE FROM candles WHERE timeframe <> '1D';
            ALTER TABLE candles ADD CONSTRAINT ck_candles__timeframe CHECK (timeframe IN ('1D'));
            ALTER TABLE candles DROP CONSTRAINT candles_pkey;
            ALTER TABLE candles ADD PRIMARY KEY (data_source_id, instrument_id, timeframe, trade_date);
            ALTER TABLE candles DROP COLUMN bar_start;

            -- Grants: restore the M1 table lists (the new tables are gone).
            SQL);
        // Re-run the 000006 migration's function body so grants match the M1 schema.
        $previous = require __DIR__.'/2026_11_16_000006_apply_role_grants.php';
        $previous->up();
    }
};
