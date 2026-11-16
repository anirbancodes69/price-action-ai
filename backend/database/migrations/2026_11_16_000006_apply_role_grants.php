<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/*
 * Single-writer grants (ARC-01 §6, ARC-06 §6). The init script gives app_backend and app_engine full DML on
 * every table the migrator creates; this narrows it to the owning writer per table.
 *
 *  - Laravel-owned tables: app_backend has DML; app_engine has at most SELECT.
 *  - Engine-owned tables: app_engine has DML; app_backend has SELECT.
 *  - The documented shared-write exceptions are column-level UPDATE grants.
 *  - Immutable tables (candle snapshots, analysis runs and children) have no UPDATE for anyone;
 *    candle_snapshots also has no DELETE. Triggers enforce the UPDATE rule even for the owner.
 *  - Default privileges are cleared, so a table added later is closed to both roles until its
 *    migration calls apply_role_grants() (or grants explicitly). It fails closed, not open.
 *
 * Roles are absent in CI's plain Postgres service; the function then does nothing.
 * Add each new table to the lists below and re-run the function from its migration.
 */
return new class extends Migration
{
    public function up(): void
    {
        DB::unprepared(<<<'SQL'
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
                -- Laravel tables the engine reads (no secrets: provider_connections is deliberately absent).
                engine_reads text[] := ARRAY[
                    'data_sources', 'data_source_selections', 'universes', 'market_calendar', 'ruleset_versions',
                    'trading_preferences', 'risk_profiles', 'paper_accounts'
                ];
                engine_owned text[] := ARRAY[
                    'instruments', 'instrument_provider_refs', 'instrument_snapshots', 'universe_memberships', 'candles',
                    'corporate_actions', 'ingestion_runs', 'data_quality_issues', 'analysis_batches', 'ai_explanations',
                    'backtest_trades'
                ];
                -- Immutable once written (UPDATE blocked by trigger); DELETE is for the retention job and cascades.
                engine_append_only text[] := ARRAY[
                    'analysis_runs', 'swing_points', 'structure_events', 'price_zones', 'liquidity_events', 'detected_setups'
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
                    -- trade_plans: Laravel creates, edits and cancels.
                    GRANT SELECT, INSERT, UPDATE, DELETE ON trade_plans, journal_entries TO app_backend;
                    -- paper trades: Laravel only reads and sends user commands (stop up, close request).
                    GRANT SELECT ON paper_trades TO app_backend;
                    GRANT UPDATE (current_stop, exit_requested_on, updated_at) ON paper_trades TO app_backend;
                    GRANT SELECT, INSERT ON paper_trade_events TO app_backend;
                    -- backtest runs: Laravel creates QUEUED rows and requests cancellation (status only).
                    GRANT SELECT, INSERT, DELETE ON backtest_runs TO app_backend;
                    GRANT UPDATE (status) ON backtest_runs TO app_backend;
                    -- audit log is append-only for both roles.
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
                    -- Snapshots are write-once and never deleted by an application role.
                    GRANT SELECT, INSERT ON candle_snapshots TO app_engine;
                    -- trade_plans: EOD status transitions only.
                    GRANT SELECT ON trade_plans TO app_engine;
                    GRANT UPDATE (status, status_reason, triggered_on, lock_version, updated_at) ON trade_plans TO app_engine;
                    -- paper trades and events: the engine records fills, exits and P&L.
                    GRANT SELECT, INSERT, UPDATE ON paper_trades TO app_engine;
                    GRANT SELECT, INSERT ON paper_trade_events TO app_engine;
                    -- journal: drafts are created on close; users edit them through Laravel.
                    GRANT SELECT, INSERT ON journal_entries TO app_engine;
                    -- backtest runs: Laravel creates the row; the engine reports status, progress and results.
                    GRANT SELECT ON backtest_runs TO app_engine;
                    GRANT UPDATE (status, progress_pct, input_hash, engine_version, metrics, equity_curve, flags,
                        error_code, started_at, finished_at) ON backtest_runs TO app_engine;
                    -- audit log: service actions, append-only.
                    GRANT SELECT, INSERT ON audit_logs TO app_engine;
                END IF;
            END
            $$;

            SELECT apply_role_grants();
            SQL);
    }

    public function down(): void
    {
        // Grants are not restored to the permissive baseline; re-run the init script's defaults if needed.
        DB::unprepared('DROP FUNCTION IF EXISTS apply_role_grants()');
    }
};
