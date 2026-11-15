<?php

namespace Tests\Feature\Database;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Tests\TestCase;

/** ARC-03 §6: market-data invariants enforced by the database itself. */
class MarketDataSchemaTest extends TestCase
{
    use AssertsDatabaseRejects;
    use RefreshDatabase;

    private function id(): string
    {
        return (string) Str::uuid7();
    }

    private function instrument(array $override = []): string
    {
        $id = $this->id();
        DB::table('instruments')->insert(array_merge([
            'id' => $id, 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'SYM'.substr($id, -6),
            'name' => 'Test Co', 'status' => 'ACTIVE',
        ], $override));

        return $id;
    }

    private function dataSource(): string
    {
        $id = $this->id();
        DB::table('data_sources')->insert(['id' => $id, 'mode' => 'DEMO', 'provider' => 'DEMO', 'name' => 'Demo']);

        return $id;
    }

    private function ingestionRun(string $source, array $override = []): string
    {
        $id = $this->id();
        DB::table('ingestion_runs')->insert(array_merge([
            'id' => $id, 'data_source_id' => $source, 'kind' => 'DAILY_CANDLES', 'status' => 'COMPLETED',
        ], $override));

        return $id;
    }

    private function universe(string $code = 'NIFTY500'): string
    {
        $id = $this->id();
        DB::table('universes')->insert(['id' => $id, 'code' => $code, 'name' => $code]);

        return $id;
    }

    private function candle(string $source, string $instrument, string $run, array $override = []): array
    {
        return array_merge([
            'data_source_id' => $source, 'instrument_id' => $instrument, 'timeframe' => '1D',
            'trade_date' => '2026-01-05', 'open' => 100, 'high' => 105, 'low' => 99, 'close' => 104,
            'volume' => 1000, 'ingestion_run_id' => $run,
        ], $override);
    }

    public function test_valid_candle_is_stored_and_primary_key_prevents_duplicates(): void
    {
        [$source, $instrument] = [$this->dataSource(), $this->instrument()];
        $run = $this->ingestionRun($source);

        DB::table('candles')->insert($this->candle($source, $instrument, $run));
        $this->assertSame(1, DB::table('candles')->count());

        $this->assertRejected(fn () => DB::table('candles')->insert($this->candle($source, $instrument, $run)));
    }

    public function test_invalid_ohlc_prices_and_volume_are_rejected(): void
    {
        [$source, $instrument] = [$this->dataSource(), $this->instrument()];
        $run = $this->ingestionRun($source);

        foreach ([
            ['high' => 103, 'close' => 104],            // high below close
            ['low' => 101, 'open' => 100],              // low above open
            ['low' => 105, 'high' => 99],               // inverted range
            ['open' => 0],                              // non-positive price
            ['close' => -1],
            ['volume' => -1],
            ['timeframe' => '1W'],
        ] as $i => $bad) {
            $this->assertRejected(fn () => DB::table('candles')->insert(
                $this->candle($source, $instrument, $run, array_merge(['trade_date' => '2026-02-0'.($i + 1)], $bad))
            ));
        }
    }

    public function test_candle_requires_existing_source_instrument_and_run(): void
    {
        [$source, $instrument] = [$this->dataSource(), $this->instrument()];
        $run = $this->ingestionRun($source);

        $this->assertRejected(fn () => DB::table('candles')->insert($this->candle($source, $this->id(), $run)));
        $this->assertRejected(fn () => DB::table('candles')->insert($this->candle($this->id(), $instrument, $run)));
        $this->assertRejected(fn () => DB::table('candles')->insert($this->candle($source, $instrument, $this->id())));
    }

    public function test_only_one_active_instrument_per_symbol_but_symbols_can_be_reused_after_delisting(): void
    {
        $this->instrument(['trading_symbol' => 'ABC', 'status' => 'DELISTED']);
        $this->instrument(['trading_symbol' => 'ABC', 'status' => 'ACTIVE']);

        $this->assertRejected(fn () => $this->instrument(['trading_symbol' => 'ABC', 'status' => 'ACTIVE']));
    }

    public function test_isin_is_unique_when_present_and_optional_otherwise(): void
    {
        $this->instrument(['isin' => 'INE000A01010']);
        $this->instrument();
        $this->instrument();

        $this->assertRejected(fn () => $this->instrument(['isin' => 'INE000A01010']));
    }

    public function test_universe_memberships_cannot_overlap_but_can_be_adjacent(): void
    {
        [$universe, $instrument] = [$this->universe(), $this->instrument()];
        $membership = fn (string $from, ?string $to, ?string $u = null) => [
            'id' => $this->id(), 'universe_id' => $u ?? $universe, 'instrument_id' => $instrument,
            'effective_from' => $from, 'effective_to' => $to,
        ];

        DB::table('universe_memberships')->insert($membership('2025-01-01', '2025-07-01'));
        DB::table('universe_memberships')->insert($membership('2025-07-01', null));       // adjacent: [from, to)
        DB::table('universe_memberships')->insert($membership('2025-01-01', null, $this->universe('NIFTY50')));

        $this->assertRejected(fn () => DB::table('universe_memberships')->insert($membership('2026-01-01', null)));
        $this->assertRejected(fn () => DB::table('universe_memberships')->insert($membership('2025-03-01', '2025-02-01')));
    }

    public function test_instrument_snapshots_cannot_overlap(): void
    {
        $instrument = $this->instrument();
        $snapshot = fn (string $from, ?string $to, string $tick = '0.05') => [
            'instrument_id' => $instrument, 'effective_from' => $from, 'effective_to' => $to,
            'name' => 'Test Co', 'tick_size' => $tick, 'status' => 'ACTIVE',
        ];

        DB::table('instrument_snapshots')->insert($snapshot('2024-01-01', '2025-01-01'));
        DB::table('instrument_snapshots')->insert($snapshot('2025-01-01', null, '0.01'));

        $this->assertRejected(fn () => DB::table('instrument_snapshots')->insert($snapshot('2025-06-01', null)));
        $this->assertRejected(fn () => DB::table('instrument_snapshots')->insert($snapshot('2023-01-01', '2023-06-01', '0')));
    }

    public function test_only_one_queued_or_running_ingestion_run_per_source_kind_and_date(): void
    {
        $source = $this->dataSource();
        $queue = fn (string $status, ?string $date = '2026-01-05') => $this->ingestionRun($source, ['status' => $status, 'trade_date' => $date]);

        $queue('COMPLETED');
        $queue('FAILED');
        $queue('RUNNING');

        $this->assertRejected(fn () => $queue('QUEUED'));
        $queue('QUEUED', '2026-01-06');                      // other date is fine
        $this->assertRejected(fn () => $this->ingestionRun($source, ['kind' => 'DAILY_CANDLES', 'status' => 'RUNNING', 'trade_date' => '2026-01-06']));
    }

    public function test_ingestion_run_enums_and_counters_are_checked(): void
    {
        $source = $this->dataSource();

        $this->assertRejected(fn () => $this->ingestionRun($source, ['kind' => 'NIGHTLY']));
        $this->assertRejected(fn () => $this->ingestionRun($source, ['status' => 'DONE']));
        $this->assertRejected(fn () => $this->ingestionRun($source, ['rows_inserted' => -1]));
        $this->assertRejected(fn () => $this->ingestionRun($source, ['range_from' => '2026-02-01', 'range_to' => '2026-01-01']));
    }

    public function test_universe_codes_are_restricted_and_unique(): void
    {
        $this->universe('NIFTY500');

        $this->assertRejected(fn () => $this->universe('NIFTY500'));
        $this->assertRejected(fn () => $this->universe('SENSEX'));
    }

    public function test_trading_preference_universe_must_exist(): void
    {
        $tenant = $this->id();
        $user = $this->id();
        DB::table('tenants')->insert(['id' => $tenant, 'name' => 't', 'slug' => 't', 'kind' => 'PERSONAL']);
        DB::table('users')->insert(['id' => $user, 'email' => 'u@example.com', 'password' => 'x']);
        $preference = fn (?string $universe) => [
            'id' => $this->id(), 'tenant_id' => $tenant, 'user_id' => $user, 'universe_id' => $universe,
        ];

        $this->assertRejected(fn () => DB::table('trading_preferences')->insert($preference($this->id())));
        DB::table('trading_preferences')->insert($preference($this->universe()));
        $this->assertSame(1, DB::table('trading_preferences')->count());
    }

    public function test_corporate_action_rules(): void
    {
        $instrument = $this->instrument();
        $action = fn (array $o = []) => array_merge([
            'id' => $this->id(), 'instrument_id' => $instrument, 'action_type' => 'SPLIT',
            'ex_date' => '2025-09-01', 'ratio_from' => 1, 'ratio_to' => 2, 'source' => 'manual',
        ], $o);

        DB::table('corporate_actions')->insert($action());
        DB::table('corporate_actions')->insert($action(['action_type' => 'DIVIDEND', 'ratio_from' => null, 'ratio_to' => null, 'cash_amount' => 5]));

        $this->assertRejected(fn () => DB::table('corporate_actions')->insert($action()));                     // duplicate
        $this->assertRejected(fn () => DB::table('corporate_actions')->insert($action(['action_type' => 'BONUS', 'ratio_to' => 0])));
        $this->assertRejected(fn () => DB::table('corporate_actions')->insert($action(['action_type' => 'SPIN', 'ex_date' => '2025-10-01'])));
    }

    public function test_market_calendar_rules(): void
    {
        $day = fn (string $date, bool $trading, ?string $open, ?string $close) => [
            'exchange' => 'NSE', 'calendar_date' => $date, 'is_trading_day' => $trading,
            'session_open' => $open, 'session_close' => $close,
        ];

        DB::table('market_calendar')->insert($day('2026-01-05', true, '09:15', '15:30'));
        DB::table('market_calendar')->insert($day('2026-01-26', false, null, null));

        $this->assertRejected(fn () => DB::table('market_calendar')->insert($day('2026-01-05', true, '09:15', '15:30')));
        $this->assertRejected(fn () => DB::table('market_calendar')->insert($day('2026-01-27', false, '09:15', '15:30')));
        $this->assertRejected(fn () => DB::table('market_calendar')->insert($day('2026-01-28', true, '15:30', '09:15')));
        $this->assertRejected(fn () => DB::table('market_calendar')->insert(array_merge($day('2026-01-29', true, '09:15', '15:30'), ['exchange' => 'BSE'])));
    }

    public function test_data_quality_issue_enums_and_run_link(): void
    {
        $run = $this->ingestionRun($this->dataSource());
        $issue = fn (array $o = []) => array_merge([
            'id' => $this->id(), 'ingestion_run_id' => $run, 'issue_type' => 'PRICE_SPIKE', 'severity' => 'WARN',
        ], $o);

        DB::table('data_quality_issues')->insert($issue());

        $this->assertRejected(fn () => DB::table('data_quality_issues')->insert($issue(['severity' => 'FATAL'])));
        $this->assertRejected(fn () => DB::table('data_quality_issues')->insert($issue(['issue_type' => 'OTHER'])));
        $this->assertRejected(fn () => DB::table('data_quality_issues')->insert($issue(['ingestion_run_id' => $this->id()])));
    }
}
