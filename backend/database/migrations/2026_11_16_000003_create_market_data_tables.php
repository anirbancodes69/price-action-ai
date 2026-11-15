<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/*
 * ARC-03 §6: instruments, provider refs, effective-dated snapshots, universes and memberships, raw candles,
 * corporate actions, ingestion runs, data-quality issues, market calendar. Written by the engine (ARC-01 §6);
 * per-table runtime grants are added with the trading tables (T-101d).
 * Also adds the deferred FK trading_preferences.universe_id -> universes.
 */
return new class extends Migration
{
    public function up(): void
    {
        DB::unprepared(<<<'SQL'
            CREATE TABLE instruments (
                id uuid PRIMARY KEY,
                exchange text NOT NULL,
                segment text NOT NULL,
                trading_symbol text NOT NULL,
                isin text NULL,
                name text NOT NULL,
                status text NOT NULL,
                listed_on date NULL,
                delisted_on date NULL,
                is_demo boolean NOT NULL DEFAULT false,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT ck_instruments__exchange CHECK (exchange IN ('NSE')),
                CONSTRAINT ck_instruments__segment CHECK (segment IN ('EQ', 'INDEX')),
                CONSTRAINT ck_instruments__status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'DELISTED'))
            );
            CREATE UNIQUE INDEX uq_instruments__exchange_isin ON instruments (exchange, isin) WHERE isin IS NOT NULL;
            -- Symbols can be reused after delisting, so only ACTIVE rows are unique.
            CREATE UNIQUE INDEX uq_instruments__active_symbol ON instruments (exchange, trading_symbol) WHERE status = 'ACTIVE';
            CREATE INDEX ix_instruments__exchange_trading_symbol ON instruments (exchange, trading_symbol);

            CREATE TABLE instrument_provider_refs (
                id uuid PRIMARY KEY,
                instrument_id uuid NOT NULL REFERENCES instruments (id),
                provider text NOT NULL,
                provider_token text NOT NULL,
                exchange_token text NULL,
                valid_from date NOT NULL,
                valid_to date NULL,
                CONSTRAINT uq_instrument_provider_refs__provider_token_valid_from UNIQUE (provider, provider_token, valid_from),
                CONSTRAINT ck_instrument_provider_refs__provider CHECK (provider IN ('DEMO', 'ZERODHA_KITE', 'LICENSED_VENDOR')),
                CONSTRAINT ck_instrument_provider_refs__valid_range CHECK (valid_to IS NULL OR valid_to > valid_from)
            );
            CREATE INDEX ix_instrument_provider_refs__instrument_id_provider ON instrument_provider_refs (instrument_id, provider);

            -- Attribute history for point-in-time correctness (tick size, lot size, name).
            CREATE TABLE instrument_snapshots (
                instrument_id uuid NOT NULL REFERENCES instruments (id),
                effective_from date NOT NULL,
                effective_to date NULL,
                name text NOT NULL,
                tick_size numeric(8,4) NOT NULL,
                lot_size integer NOT NULL DEFAULT 1,
                status text NOT NULL,
                PRIMARY KEY (instrument_id, effective_from),
                CONSTRAINT ck_instrument_snapshots__status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'DELISTED')),
                CONSTRAINT ck_instrument_snapshots__tick_size CHECK (tick_size > 0),
                CONSTRAINT ck_instrument_snapshots__lot_size CHECK (lot_size > 0),
                CONSTRAINT ck_instrument_snapshots__range CHECK (effective_to IS NULL OR effective_to > effective_from),
                CONSTRAINT ex_instrument_snapshots__no_overlap
                    EXCLUDE USING gist (instrument_id WITH =, daterange(effective_from, effective_to, '[)') WITH &&)
            );

            CREATE TABLE universes (
                id uuid PRIMARY KEY,
                code text NOT NULL,
                name text NOT NULL,
                source text NULL,
                is_demo boolean NOT NULL DEFAULT false,
                CONSTRAINT uq_universes__code UNIQUE (code),
                CONSTRAINT ck_universes__code
                    CHECK (code IN ('NIFTY500', 'NIFTY50', 'NIFTY100', 'NIFTY200', 'NIFTYMIDCAP150', 'DEMO'))
            );

            -- Point-in-time lookup: effective_from <= d AND (effective_to IS NULL OR effective_to > d).
            CREATE TABLE universe_memberships (
                id uuid PRIMARY KEY,
                universe_id uuid NOT NULL REFERENCES universes (id),
                instrument_id uuid NOT NULL REFERENCES instruments (id),
                effective_from date NOT NULL,
                effective_to date NULL,
                source_ref text NULL,
                CONSTRAINT ck_universe_memberships__range CHECK (effective_to IS NULL OR effective_to > effective_from),
                CONSTRAINT ex_universe_memberships__no_overlap
                    EXCLUDE USING gist (universe_id WITH =, instrument_id WITH =, daterange(effective_from, effective_to, '[)') WITH &&)
            );
            CREATE INDEX ix_universe_memberships__universe_id_effective
                ON universe_memberships (universe_id, effective_from, effective_to);
            CREATE INDEX ix_universe_memberships__instrument_id ON universe_memberships (instrument_id);

            ALTER TABLE trading_preferences
                ADD CONSTRAINT fk_trading_preferences__universe_id FOREIGN KEY (universe_id) REFERENCES universes (id);

            CREATE TABLE ingestion_runs (
                id uuid PRIMARY KEY,
                data_source_id uuid NOT NULL REFERENCES data_sources (id),
                kind text NOT NULL,
                trade_date date NULL,
                range_from date NULL,
                range_to date NULL,
                status text NOT NULL,
                requested_by uuid NULL REFERENCES users (id),
                instruments_total integer NOT NULL DEFAULT 0,
                instruments_succeeded integer NOT NULL DEFAULT 0,
                instruments_failed integer NOT NULL DEFAULT 0,
                rows_inserted integer NOT NULL DEFAULT 0,
                rows_updated integer NOT NULL DEFAULT 0,
                quality_issue_count integer NOT NULL DEFAULT 0,
                error_summary jsonb NULL,
                started_at timestamptz NULL,
                finished_at timestamptz NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT ck_ingestion_runs__kind
                    CHECK (kind IN ('INSTRUMENT_MASTER', 'DAILY_CANDLES', 'BACKFILL', 'CORPORATE_ACTIONS', 'UNIVERSE')),
                CONSTRAINT ck_ingestion_runs__status CHECK (status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED')),
                CONSTRAINT ck_ingestion_runs__range CHECK (range_to IS NULL OR range_from IS NULL OR range_to >= range_from),
                CONSTRAINT ck_ingestion_runs__counters CHECK (
                    instruments_total >= 0 AND instruments_succeeded >= 0 AND instruments_failed >= 0
                    AND rows_inserted >= 0 AND rows_updated >= 0 AND quality_issue_count >= 0
                )
            );
            CREATE INDEX ix_ingestion_runs__data_source_id_kind_created_at ON ingestion_runs (data_source_id, kind, created_at DESC);
            -- Prevents concurrent duplicate runs for a dated kind (runs without a trade_date, e.g. backfills, are not covered).
            CREATE UNIQUE INDEX uq_ingestion_runs__active ON ingestion_runs (data_source_id, kind, trade_date)
                WHERE status IN ('QUEUED', 'RUNNING');

            -- Stored raw (unadjusted); adjusted series are built per candle snapshot from corporate_actions.
            CREATE TABLE candles (
                data_source_id uuid NOT NULL REFERENCES data_sources (id),
                instrument_id uuid NOT NULL REFERENCES instruments (id),
                timeframe text NOT NULL,
                trade_date date NOT NULL,
                open numeric(12,2) NOT NULL,
                high numeric(12,2) NOT NULL,
                low numeric(12,2) NOT NULL,
                close numeric(12,2) NOT NULL,
                volume bigint NOT NULL,
                ingestion_run_id uuid NOT NULL REFERENCES ingestion_runs (id),
                revision smallint NOT NULL DEFAULT 1,
                updated_at timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY (data_source_id, instrument_id, timeframe, trade_date),
                CONSTRAINT ck_candles__timeframe CHECK (timeframe IN ('1D')),
                CONSTRAINT ck_candles__prices_positive CHECK (open > 0 AND high > 0 AND low > 0 AND close > 0),
                CONSTRAINT ck_candles__ohlc CHECK (low <= least(open, close) AND greatest(open, close) <= high),
                CONSTRAINT ck_candles__volume CHECK (volume >= 0),
                CONSTRAINT ck_candles__revision CHECK (revision >= 1)
            );
            CREATE INDEX ix_candles__instrument_id_trade_date ON candles (instrument_id, trade_date);

            CREATE TABLE corporate_actions (
                id uuid PRIMARY KEY,
                instrument_id uuid NOT NULL REFERENCES instruments (id),
                action_type text NOT NULL,
                ex_date date NOT NULL,
                ratio_from numeric(12,4) NULL,
                ratio_to numeric(12,4) NULL,
                cash_amount numeric(12,4) NULL,
                source text NOT NULL,
                CONSTRAINT uq_corporate_actions__instrument_type_ex_date UNIQUE (instrument_id, action_type, ex_date),
                CONSTRAINT ck_corporate_actions__action_type
                    CHECK (action_type IN ('SPLIT', 'BONUS', 'DIVIDEND', 'RIGHTS', 'MERGER', 'DEMERGER', 'SYMBOL_CHANGE')),
                CONSTRAINT ck_corporate_actions__ratio CHECK (
                    (ratio_from IS NULL AND ratio_to IS NULL) OR (ratio_from > 0 AND ratio_to > 0)
                )
            );

            CREATE TABLE data_quality_issues (
                id uuid PRIMARY KEY,
                ingestion_run_id uuid NOT NULL REFERENCES ingestion_runs (id),
                instrument_id uuid NULL REFERENCES instruments (id),
                trade_date date NULL,
                issue_type text NOT NULL,
                severity text NOT NULL,
                details jsonb NULL,
                resolved_at timestamptz NULL,
                CONSTRAINT ck_data_quality_issues__issue_type CHECK (issue_type IN (
                    'MISSING_SESSION', 'OHLC_INVALID', 'DUPLICATE', 'PRICE_SPIKE', 'ZERO_VOLUME', 'STALE_DATA', 'PROVIDER_GAP'
                )),
                CONSTRAINT ck_data_quality_issues__severity CHECK (severity IN ('INFO', 'WARN', 'ERROR'))
            );
            CREATE INDEX ix_data_quality_issues__instrument_id_trade_date ON data_quality_issues (instrument_id, trade_date);
            CREATE INDEX ix_data_quality_issues__ingestion_run_id ON data_quality_issues (ingestion_run_id);

            CREATE TABLE market_calendar (
                exchange text NOT NULL,
                calendar_date date NOT NULL,
                is_trading_day boolean NOT NULL,
                session_open time NULL,
                session_close time NULL,
                note text NULL,
                PRIMARY KEY (exchange, calendar_date),
                CONSTRAINT ck_market_calendar__exchange CHECK (exchange IN ('NSE')),
                CONSTRAINT ck_market_calendar__holiday_has_no_session
                    CHECK (is_trading_day OR (session_open IS NULL AND session_close IS NULL)),
                CONSTRAINT ck_market_calendar__session_order
                    CHECK (session_open IS NULL OR session_close IS NULL OR session_close > session_open)
            );
            SQL);
    }

    public function down(): void
    {
        DB::unprepared(<<<'SQL'
            ALTER TABLE trading_preferences DROP CONSTRAINT IF EXISTS fk_trading_preferences__universe_id;
            DROP TABLE IF EXISTS market_calendar, data_quality_issues, corporate_actions, candles, ingestion_runs,
                universe_memberships, universes, instrument_snapshots, instrument_provider_refs, instruments;
            SQL);
    }
};
