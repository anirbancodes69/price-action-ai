<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/*
 * ARC-03 §8: watchlists, trade plans, paper and actual trades, journal, backtests, notifications.
 * Long-only and stop < entry < target are enforced here as well as in the engine (C-12, ARC-03 §13).
 * Writers and column-level grants arrive in 2026_11_16_000006_apply_role_grants.
 */
return new class extends Migration
{
    public function up(): void
    {
        DB::unprepared(<<<'SQL'
            CREATE TABLE watchlists (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES tenants (id),
                user_id uuid NOT NULL REFERENCES users (id),
                name text NOT NULL,
                sort_order smallint NOT NULL DEFAULT 0,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_watchlists__tenant_user_name UNIQUE (tenant_id, user_id, name),
                CONSTRAINT ck_watchlists__name CHECK (char_length(name) BETWEEN 1 AND 60)
            );

            CREATE TABLE watchlist_items (
                watchlist_id uuid NOT NULL REFERENCES watchlists (id) ON DELETE CASCADE,
                instrument_id uuid NOT NULL REFERENCES instruments (id),
                sort_order smallint NOT NULL DEFAULT 0,
                added_at timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY (watchlist_id, instrument_id)
            );
            CREATE INDEX ix_watchlist_items__instrument_id ON watchlist_items (instrument_id);

            -- plan_number is assigned by the application (per-tenant counter, OQ-DB-03 still open).
            CREATE TABLE trade_plans (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES tenants (id),
                user_id uuid NOT NULL REFERENCES users (id),
                plan_number integer NOT NULL,
                instrument_id uuid NOT NULL REFERENCES instruments (id),
                analysis_run_id uuid NOT NULL REFERENCES analysis_runs (id),
                detected_setup_id uuid NULL REFERENCES detected_setups (id),
                setup_key text NULL,
                source text NOT NULL,
                direction text NOT NULL,
                status text NOT NULL,
                status_reason text NULL,
                entry_price numeric(12,2) NOT NULL,
                stop_price numeric(12,2) NOT NULL,
                target_price numeric(12,2) NOT NULL,
                engine_entry_price numeric(12,2) NULL,
                engine_stop_price numeric(12,2) NULL,
                engine_target_price numeric(12,2) NULL,
                levels_overridden boolean NOT NULL DEFAULT false,
                quantity integer NOT NULL,
                risk_budget numeric(14,2) NOT NULL,
                risk_amount numeric(14,2) NOT NULL,
                position_value numeric(14,2) NOT NULL,
                rr numeric(8,4) NOT NULL,
                binding_constraint text NULL,
                risk_profile_id uuid NOT NULL REFERENCES risk_profiles (id),
                ruleset_version_id uuid NOT NULL REFERENCES ruleset_versions (id),
                paper_tracking boolean NOT NULL DEFAULT true,
                note text NULL,
                triggered_on date NULL,
                lock_version integer NOT NULL DEFAULT 0,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_trade_plans__tenant_id_plan_number UNIQUE (tenant_id, plan_number),
                CONSTRAINT ck_trade_plans__plan_number CHECK (plan_number > 0),
                CONSTRAINT ck_trade_plans__setup_key CHECK (setup_key IS NULL OR setup_key ~ '^[0-9a-f]{64}$'),
                CONSTRAINT ck_trade_plans__source CHECK (source IN ('ENGINE', 'MANUAL')),
                CONSTRAINT ck_trade_plans__direction CHECK (direction = 'LONG'),
                CONSTRAINT ck_trade_plans__status CHECK (
                    status IN ('PENDING', 'TRIGGERED', 'FILLED', 'SKIPPED', 'INVALIDATED', 'EXPIRED', 'CANCELLED')
                ),
                CONSTRAINT ck_trade_plans__levels CHECK (stop_price > 0 AND stop_price < entry_price AND target_price > entry_price),
                CONSTRAINT ck_trade_plans__engine_levels CHECK (
                    (engine_entry_price IS NULL AND engine_stop_price IS NULL AND engine_target_price IS NULL)
                    OR (engine_stop_price > 0 AND engine_stop_price < engine_entry_price AND engine_target_price > engine_entry_price)
                ),
                CONSTRAINT ck_trade_plans__manual_has_no_engine_levels CHECK (
                    source <> 'MANUAL'
                    OR (engine_entry_price IS NULL AND engine_stop_price IS NULL AND engine_target_price IS NULL)
                ),
                CONSTRAINT ck_trade_plans__quantity CHECK (quantity > 0),
                CONSTRAINT ck_trade_plans__amounts CHECK (risk_budget >= 0 AND risk_amount >= 0 AND position_value > 0),
                CONSTRAINT ck_trade_plans__rr CHECK (rr > 0),
                CONSTRAINT ck_trade_plans__note CHECK (note IS NULL OR char_length(note) <= 2000),
                CONSTRAINT ck_trade_plans__lock_version CHECK (lock_version >= 0)
            );
            CREATE INDEX ix_trade_plans__tenant_user_status ON trade_plans (tenant_id, user_id, status);
            CREATE INDEX ix_trade_plans__setup_key_open ON trade_plans (setup_key) WHERE status IN ('PENDING', 'TRIGGERED');
            CREATE INDEX ix_trade_plans__instrument_id ON trade_plans (instrument_id);
            CREATE INDEX ix_trade_plans__analysis_run_id ON trade_plans (analysis_run_id);

            CREATE TABLE paper_accounts (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES tenants (id),
                user_id uuid NOT NULL REFERENCES users (id),
                starting_capital numeric(14,2) NOT NULL,
                reset_generation integer NOT NULL DEFAULT 0,
                is_current boolean NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_paper_accounts__generation UNIQUE (tenant_id, user_id, reset_generation),
                CONSTRAINT ck_paper_accounts__capital CHECK (starting_capital > 0),
                CONSTRAINT ck_paper_accounts__generation CHECK (reset_generation >= 0)
            );
            CREATE UNIQUE INDEX uq_paper_accounts__current ON paper_accounts (tenant_id, user_id) WHERE is_current;

            CREATE TABLE paper_trades (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES tenants (id),
                user_id uuid NOT NULL REFERENCES users (id),
                paper_account_id uuid NOT NULL REFERENCES paper_accounts (id),
                trade_plan_id uuid NOT NULL REFERENCES trade_plans (id),
                instrument_id uuid NOT NULL REFERENCES instruments (id),
                status text NOT NULL,
                entry_date date NOT NULL,
                entry_price numeric(12,2) NOT NULL,
                quantity integer NOT NULL,
                initial_stop numeric(12,2) NOT NULL,
                current_stop numeric(12,2) NOT NULL,
                target_price numeric(12,2) NOT NULL,
                exit_requested_on date NULL,
                exit_date date NULL,
                exit_price numeric(12,2) NULL,
                exit_reason text NULL,
                gross_pnl numeric(14,2) NULL,
                charges numeric(14,2) NULL,
                net_pnl numeric(14,2) NULL,
                r_multiple numeric(8,4) NULL,
                cost_schedule_version text NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_paper_trades__trade_plan_id UNIQUE (trade_plan_id),
                CONSTRAINT ck_paper_trades__status CHECK (status IN ('OPEN', 'CLOSED')),
                CONSTRAINT ck_paper_trades__quantity CHECK (quantity > 0),
                CONSTRAINT ck_paper_trades__prices CHECK (entry_price > 0 AND initial_stop > 0 AND target_price > 0),
                -- A stop may only be moved up (ARC-03 §8.4).
                CONSTRAINT ck_paper_trades__stop_only_up CHECK (current_stop >= initial_stop),
                CONSTRAINT ck_paper_trades__exit_reason CHECK (
                    exit_reason IS NULL OR exit_reason IN (
                        'STOP', 'STOP_GAP', 'STOP_COLLISION', 'TARGET', 'TARGET_GAP', 'STRUCTURE_EXIT', 'MANUAL',
                        'CORPORATE_ACTION_EXIT'
                    )
                ),
                CONSTRAINT ck_paper_trades__exit_dates CHECK (
                    (exit_date IS NULL OR exit_date >= entry_date)
                    AND (exit_requested_on IS NULL OR exit_requested_on >= entry_date)
                ),
                CONSTRAINT ck_paper_trades__open_or_closed CHECK (
                    (status = 'OPEN' AND exit_date IS NULL AND exit_price IS NULL AND exit_reason IS NULL AND net_pnl IS NULL)
                    OR (status = 'CLOSED' AND exit_date IS NOT NULL AND exit_price > 0 AND exit_reason IS NOT NULL
                        AND gross_pnl IS NOT NULL AND net_pnl IS NOT NULL)
                )
            );
            CREATE INDEX ix_paper_trades__tenant_user_status ON paper_trades (tenant_id, user_id, status);
            CREATE INDEX ix_paper_trades__status_instrument_id ON paper_trades (status, instrument_id);
            CREATE INDEX ix_paper_trades__paper_account_id ON paper_trades (paper_account_id);

            CREATE TABLE paper_trade_events (
                id uuid PRIMARY KEY,
                paper_trade_id uuid NOT NULL REFERENCES paper_trades (id) ON DELETE CASCADE,
                event_type text NOT NULL,
                event_date date NOT NULL,
                data jsonb NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT ck_paper_trade_events__event_type
                    CHECK (event_type IN ('FILLED', 'STOP_MOVED', 'EXIT_SIGNALLED', 'CLOSED'))
            );
            CREATE INDEX ix_paper_trade_events__paper_trade_id ON paper_trade_events (paper_trade_id);

            CREATE TABLE actual_trades (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES tenants (id),
                user_id uuid NOT NULL REFERENCES users (id),
                instrument_id uuid NOT NULL REFERENCES instruments (id),
                trade_plan_id uuid NULL REFERENCES trade_plans (id),
                direction text NOT NULL,
                status text NOT NULL,
                quantity_open integer NOT NULL DEFAULT 0,
                avg_entry_price numeric(12,4) NULL,
                avg_exit_price numeric(12,4) NULL,
                realized_pnl numeric(14,2) NULL,
                charges numeric(14,2) NULL,
                source text NOT NULL DEFAULT 'MANUAL',
                opened_at timestamptz NULL,
                closed_at timestamptz NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT ck_actual_trades__direction CHECK (direction = 'LONG'),
                CONSTRAINT ck_actual_trades__status CHECK (status IN ('OPEN', 'CLOSED')),
                CONSTRAINT ck_actual_trades__quantity_open CHECK (quantity_open >= 0),
                CONSTRAINT ck_actual_trades__source CHECK (source IN ('MANUAL', 'BROKER_IMPORT')),
                CONSTRAINT ck_actual_trades__prices CHECK (COALESCE(avg_entry_price, 1) > 0 AND COALESCE(avg_exit_price, 1) > 0),
                CONSTRAINT ck_actual_trades__closed CHECK (
                    (status = 'OPEN' AND closed_at IS NULL)
                    OR (status = 'CLOSED' AND quantity_open = 0 AND closed_at IS NOT NULL)
                ),
                CONSTRAINT ck_actual_trades__closed_after_opened CHECK (closed_at IS NULL OR opened_at IS NULL OR closed_at >= opened_at)
            );
            CREATE INDEX ix_actual_trades__tenant_user_status ON actual_trades (tenant_id, user_id, status);
            CREATE INDEX ix_actual_trades__instrument_id ON actual_trades (instrument_id);
            CREATE INDEX ix_actual_trades__trade_plan_id ON actual_trades (trade_plan_id);

            -- Application rule (not expressible as a CHECK): cumulative SELL quantity <= cumulative BUY quantity.
            CREATE TABLE actual_trade_fills (
                id uuid PRIMARY KEY,
                actual_trade_id uuid NOT NULL REFERENCES actual_trades (id) ON DELETE CASCADE,
                side text NOT NULL,
                quantity integer NOT NULL,
                price numeric(12,2) NOT NULL,
                executed_at timestamptz NOT NULL,
                broker_order_id text NULL,
                broker_trade_id text NULL,
                fees numeric(14,2) NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT ck_actual_trade_fills__side CHECK (side IN ('BUY', 'SELL')),
                CONSTRAINT ck_actual_trade_fills__quantity CHECK (quantity > 0),
                CONSTRAINT ck_actual_trade_fills__price CHECK (price > 0),
                CONSTRAINT ck_actual_trade_fills__fees CHECK (fees IS NULL OR fees >= 0)
            );
            CREATE UNIQUE INDEX uq_actual_trade_fills__broker_trade
                ON actual_trade_fills (actual_trade_id, broker_trade_id) WHERE broker_trade_id IS NOT NULL;
            CREATE INDEX ix_actual_trade_fills__actual_trade_id ON actual_trade_fills (actual_trade_id, executed_at);

            CREATE TABLE journal_entries (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES tenants (id),
                user_id uuid NOT NULL REFERENCES users (id),
                trade_kind text NOT NULL,
                paper_trade_id uuid NULL REFERENCES paper_trades (id),
                actual_trade_id uuid NULL REFERENCES actual_trades (id),
                status text NOT NULL DEFAULT 'DRAFT',
                followed_plan_system boolean NULL,
                followed_plan boolean NULL,
                notes text NULL,
                tags text[] NOT NULL DEFAULT '{}',
                emotions text[] NOT NULL DEFAULT '{}',
                mistakes text[] NOT NULL DEFAULT '{}',
                lessons text NULL,
                rating smallint NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_journal_entries__paper_trade_id UNIQUE (paper_trade_id),
                CONSTRAINT uq_journal_entries__actual_trade_id UNIQUE (actual_trade_id),
                CONSTRAINT ck_journal_entries__trade_kind CHECK (trade_kind IN ('PAPER', 'ACTUAL')),
                CONSTRAINT ck_journal_entries__trade_ref CHECK (
                    (trade_kind = 'PAPER' AND paper_trade_id IS NOT NULL AND actual_trade_id IS NULL)
                    OR (trade_kind = 'ACTUAL' AND actual_trade_id IS NOT NULL AND paper_trade_id IS NULL)
                ),
                CONSTRAINT ck_journal_entries__status CHECK (status IN ('DRAFT', 'COMPLETE')),
                CONSTRAINT ck_journal_entries__notes CHECK (notes IS NULL OR char_length(notes) <= 10000),
                CONSTRAINT ck_journal_entries__rating CHECK (rating IS NULL OR rating BETWEEN 1 AND 5)
            );
            CREATE INDEX ix_journal_entries__tenant_user_created_at ON journal_entries (tenant_id, user_id, created_at DESC);

            CREATE TABLE backtest_runs (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES tenants (id),
                user_id uuid NOT NULL REFERENCES users (id),
                ruleset_version_id uuid NOT NULL REFERENCES ruleset_versions (id),
                data_source_id uuid NOT NULL REFERENCES data_sources (id),
                universe_id uuid NULL REFERENCES universes (id),
                instrument_ids uuid[] NULL,
                setup_types text[] NOT NULL DEFAULT '{}',
                date_from date NOT NULL,
                date_to date NOT NULL,
                starting_capital numeric(14,2) NOT NULL,
                risk_per_trade_pct numeric(6,3) NOT NULL,
                sizing_mode text NOT NULL,
                slippage_pct numeric(6,3) NOT NULL DEFAULT 0,
                cost_schedule_version text NULL,
                purpose text NOT NULL DEFAULT 'USER',
                status text NOT NULL DEFAULT 'QUEUED',
                progress_pct smallint NOT NULL DEFAULT 0,
                input_hash text NULL,
                engine_version text NULL,
                metrics jsonb NULL,
                equity_curve jsonb NULL,
                flags jsonb NULL,
                error_code text NULL,
                queued_at timestamptz NOT NULL DEFAULT now(),
                started_at timestamptz NULL,
                finished_at timestamptz NULL,
                CONSTRAINT ck_backtest_runs__dates CHECK (date_from < date_to),
                CONSTRAINT ck_backtest_runs__capital CHECK (starting_capital >= 10000),
                CONSTRAINT ck_backtest_runs__risk CHECK (risk_per_trade_pct BETWEEN 0.1 AND 5),
                CONSTRAINT ck_backtest_runs__sizing_mode CHECK (sizing_mode IN ('FIXED', 'COMPOUNDING')),
                CONSTRAINT ck_backtest_runs__slippage CHECK (slippage_pct >= 0),
                CONSTRAINT ck_backtest_runs__purpose CHECK (purpose IN ('USER', 'EXPLORATION', 'OOS', 'HOLDOUT')),
                CONSTRAINT ck_backtest_runs__status CHECK (status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),
                CONSTRAINT ck_backtest_runs__progress CHECK (progress_pct BETWEEN 0 AND 100),
                CONSTRAINT ck_backtest_runs__input_hash CHECK (input_hash IS NULL OR input_hash ~ '^[0-9a-f]{64}$'),
                CONSTRAINT ck_backtest_runs__scope CHECK (universe_id IS NOT NULL OR instrument_ids IS NOT NULL)
            );
            CREATE INDEX ix_backtest_runs__tenant_user_queued_at ON backtest_runs (tenant_id, user_id, queued_at DESC);

            CREATE TABLE backtest_trades (
                id uuid PRIMARY KEY,
                backtest_run_id uuid NOT NULL REFERENCES backtest_runs (id) ON DELETE CASCADE,
                instrument_id uuid NOT NULL REFERENCES instruments (id),
                setup_type text NOT NULL,
                setup_key text NOT NULL,
                signal_date date NOT NULL,
                outcome text NOT NULL,
                skip_reason text NULL,
                entry_date date NULL,
                entry_price numeric(12,2) NULL,
                quantity integer NULL,
                stop_price numeric(12,2) NULL,
                target_price numeric(12,2) NULL,
                exit_date date NULL,
                exit_price numeric(12,2) NULL,
                exit_reason text NULL,
                gross_pnl numeric(14,2) NULL,
                charges numeric(14,2) NULL,
                net_pnl numeric(14,2) NULL,
                r_multiple numeric(8,4) NULL,
                paqs_score smallint NULL,
                structure_state_at_entry text NULL,
                CONSTRAINT ck_backtest_trades__setup_type CHECK (
                    setup_type IN ('BREAKOUT_RETEST', 'SUPPORT_REJECTION', 'TREND_PULLBACK', 'LIQUIDITY_SWEEP_REVERSAL')
                ),
                CONSTRAINT ck_backtest_trades__setup_key CHECK (setup_key ~ '^[0-9a-f]{64}$'),
                CONSTRAINT ck_backtest_trades__outcome CHECK (outcome IN ('FILLED', 'SKIPPED')),
                -- No look-ahead: a signal at close t fills at the open of a later bar (C-09, TRD-06).
                CONSTRAINT ck_backtest_trades__fill_after_signal CHECK (entry_date IS NULL OR entry_date > signal_date),
                CONSTRAINT ck_backtest_trades__filled CHECK (
                    outcome <> 'FILLED' OR (entry_date IS NOT NULL AND entry_price > 0 AND quantity > 0
                        AND stop_price > 0 AND stop_price < entry_price AND target_price > entry_price)
                ),
                CONSTRAINT ck_backtest_trades__skipped CHECK (
                    outcome <> 'SKIPPED' OR (skip_reason IS NOT NULL AND entry_date IS NULL AND exit_date IS NULL)
                ),
                CONSTRAINT ck_backtest_trades__exit_after_entry CHECK (exit_date IS NULL OR (entry_date IS NOT NULL AND exit_date >= entry_date)),
                CONSTRAINT ck_backtest_trades__paqs_score CHECK (paqs_score IS NULL OR paqs_score BETWEEN 0 AND 100),
                CONSTRAINT ck_backtest_trades__structure_state CHECK (
                    structure_state_at_entry IS NULL
                    OR structure_state_at_entry IN ('BULLISH', 'BEARISH', 'SIDEWAYS', 'TRANSITION')
                )
            );
            CREATE INDEX ix_backtest_trades__run_entry_date ON backtest_trades (backtest_run_id, entry_date);
            CREATE INDEX ix_backtest_trades__instrument_id ON backtest_trades (instrument_id);

            CREATE TABLE notifications (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES tenants (id),
                user_id uuid NOT NULL REFERENCES users (id),
                type text NOT NULL,
                title text NOT NULL,
                body text NULL,
                entity_type text NULL,
                entity_id uuid NULL,
                read_at timestamptz NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT ck_notifications__type CHECK (type ~ '^[A-Z][A-Z0-9_]*$'),
                CONSTRAINT ck_notifications__title CHECK (char_length(title) BETWEEN 1 AND 200)
            );
            CREATE INDEX ix_notifications__user_read_created ON notifications (user_id, read_at, created_at DESC);
            CREATE INDEX ix_notifications__tenant_id ON notifications (tenant_id);
            SQL);
    }

    public function down(): void
    {
        DB::unprepared(<<<'SQL'
            DROP TABLE IF EXISTS notifications, backtest_trades, backtest_runs, journal_entries, actual_trade_fills,
                actual_trades, paper_trade_events, paper_trades, paper_accounts, trade_plans, watchlist_items, watchlists;
            SQL);
    }
};
