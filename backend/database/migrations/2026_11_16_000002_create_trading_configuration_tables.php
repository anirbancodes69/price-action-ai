<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/*
 * ARC-03 §5: trading preferences, risk profiles, entitlements, provider connections, data sources and
 * selections. trading_preferences.universe_id is a plain uuid for now; its FK to universes is added with
 * the market-data tables (TASKS T-101b).
 */
return new class extends Migration
{
    public function up(): void
    {
        DB::unprepared(<<<'SQL'
            CREATE TABLE trading_preferences (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES tenants (id),
                user_id uuid NOT NULL REFERENCES users (id),
                trading_styles text[] NOT NULL DEFAULT '{}',
                default_timeframe text NOT NULL DEFAULT '1D',
                universe_id uuid NULL,
                direction_preference text NOT NULL DEFAULT 'LONG_ONLY',
                notification_settings jsonb NOT NULL DEFAULT '{}',
                updated_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_trading_preferences__tenant_id_user_id UNIQUE (tenant_id, user_id),
                CONSTRAINT ck_trading_preferences__default_timeframe CHECK (default_timeframe IN ('1D')),
                CONSTRAINT ck_trading_preferences__direction_preference
                    CHECK (direction_preference IN ('LONG_ONLY', 'LONG_AND_REFERENCE'))
            );

            -- Versioned, never updated in place; trade plans reference the version used.
            CREATE TABLE risk_profiles (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES tenants (id),
                user_id uuid NOT NULL REFERENCES users (id),
                version integer NOT NULL,
                is_current boolean NOT NULL,
                trading_capital numeric(14,2) NOT NULL,
                risk_per_trade_pct numeric(6,3) NOT NULL,
                max_open_positions smallint NOT NULL,
                max_portfolio_heat_pct numeric(6,3) NOT NULL,
                max_position_pct numeric(6,3) NOT NULL,
                min_rr numeric(8,4) NULL,
                max_entry_gap_pct numeric(6,3) NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_risk_profiles__tenant_id_user_id_version UNIQUE (tenant_id, user_id, version),
                CONSTRAINT ck_risk_profiles__trading_capital CHECK (trading_capital >= 10000),
                CONSTRAINT ck_risk_profiles__risk_per_trade_pct CHECK (risk_per_trade_pct BETWEEN 0.1 AND 2.0),
                CONSTRAINT ck_risk_profiles__max_open_positions CHECK (max_open_positions BETWEEN 1 AND 20),
                CONSTRAINT ck_risk_profiles__max_portfolio_heat_pct CHECK (max_portfolio_heat_pct BETWEEN 1 AND 10),
                CONSTRAINT ck_risk_profiles__max_position_pct CHECK (max_position_pct BETWEEN 5 AND 100)
            );
            CREATE UNIQUE INDEX uq_risk_profiles__current ON risk_profiles (tenant_id, user_id) WHERE is_current;

            CREATE TABLE subscription_entitlements (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES tenants (id),
                plan_code text NOT NULL,
                features jsonb NOT NULL DEFAULT '{}',
                status text NOT NULL,
                source text NOT NULL,
                valid_from timestamptz NOT NULL,
                valid_to timestamptz NULL,
                CONSTRAINT ck_subscription_entitlements__plan_code CHECK (plan_code IN ('DEMO', 'PERSONAL', 'PRO')),
                CONSTRAINT ck_subscription_entitlements__status CHECK (status IN ('ACTIVE', 'EXPIRED', 'CANCELLED')),
                CONSTRAINT ck_subscription_entitlements__source CHECK (source IN ('DEFAULT', 'MANUAL', 'BILLING')),
                CONSTRAINT ck_subscription_entitlements__valid_range CHECK (valid_to IS NULL OR valid_to > valid_from),
                CONSTRAINT ex_subscription_entitlements__active_no_overlap
                    EXCLUDE USING gist (tenant_id WITH =, tstzrange(valid_from, valid_to) WITH &&)
                    WHERE (status = 'ACTIVE')
            );

            -- Tokens are encrypted by the application; the Zerodha password, 2FA/PIN and request_token are never stored.
            CREATE TABLE provider_connections (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES tenants (id),
                user_id uuid NOT NULL REFERENCES users (id),
                provider text NOT NULL,
                provider_user_id text NULL,
                status text NOT NULL,
                access_token_encrypted text NULL,
                token_expires_at timestamptz NULL,
                key_version smallint NOT NULL DEFAULT 1,
                oauth_state_hash text NULL,
                last_connected_at timestamptz NULL,
                last_error_at timestamptz NULL,
                last_error_code text NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_provider_connections__tenant_id_provider_provider_user_id
                    UNIQUE (tenant_id, provider, provider_user_id),
                CONSTRAINT ck_provider_connections__provider CHECK (provider IN ('ZERODHA_KITE')),
                CONSTRAINT ck_provider_connections__status
                    CHECK (status IN ('PENDING', 'CONNECTED', 'EXPIRED', 'REVOKED', 'ERROR'))
            );
            CREATE INDEX ix_provider_connections__user_id ON provider_connections (user_id);

            -- Unit of market-data licensing and isolation (ADR-011).
            CREATE TABLE data_sources (
                id uuid PRIMARY KEY,
                mode text NOT NULL,
                provider text NOT NULL,
                tenant_id uuid NULL REFERENCES tenants (id),
                provider_connection_id uuid NULL REFERENCES provider_connections (id),
                name text NOT NULL,
                status text NOT NULL DEFAULT 'ACTIVE',
                created_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_data_sources__provider_connection_id UNIQUE (provider_connection_id),
                CONSTRAINT ck_data_sources__mode CHECK (mode IN ('DEMO', 'PERSONAL', 'LICENSED')),
                CONSTRAINT ck_data_sources__provider CHECK (provider IN ('DEMO', 'ZERODHA_KITE', 'LICENSED_VENDOR')),
                CONSTRAINT ck_data_sources__status CHECK (status IN ('ACTIVE', 'DISABLED')),
                CONSTRAINT ck_data_sources__mode_ownership CHECK (
                    (mode = 'PERSONAL' AND tenant_id IS NOT NULL AND provider_connection_id IS NOT NULL)
                    OR (mode IN ('DEMO', 'LICENSED') AND tenant_id IS NULL)
                )
            );
            CREATE UNIQUE INDEX uq_data_sources__global_mode_provider ON data_sources (mode, provider) WHERE tenant_id IS NULL;
            CREATE INDEX ix_data_sources__tenant_id ON data_sources (tenant_id);

            CREATE TABLE data_source_selections (
                tenant_id uuid PRIMARY KEY REFERENCES tenants (id),
                data_source_id uuid NOT NULL REFERENCES data_sources (id),
                selected_by uuid NOT NULL REFERENCES users (id),
                selected_at timestamptz NOT NULL DEFAULT now()
            );
            SQL);
    }

    public function down(): void
    {
        DB::unprepared(
            'DROP TABLE IF EXISTS data_source_selections, data_sources, provider_connections, '
            .'subscription_entitlements, risk_profiles, trading_preferences'
        );
    }
};
