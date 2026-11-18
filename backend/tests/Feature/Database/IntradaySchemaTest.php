<?php

namespace Tests\Feature\Database;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Tests\TestCase;

/** ADR-015, ARC-03 §2.2: the intraday time model, bar revisions, intraday ingestion runs and risk limits. */
class IntradaySchemaTest extends TestCase
{
    use AssertsDatabaseRejects;
    use RefreshDatabase;

    private function id(): string
    {
        return (string) Str::uuid7();
    }

    /** @return array{source: string, instrument: string, run: string} */
    private function base(): array
    {
        $in = ['source' => $this->id(), 'instrument' => $this->id(), 'run' => $this->id()];
        DB::table('data_sources')->insert(['id' => $in['source'], 'mode' => 'DEMO', 'provider' => 'DEMO', 'name' => 'Demo']);
        DB::table('instruments')->insert([
            'id' => $in['instrument'], 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'T'.substr($in['instrument'], -6),
            'name' => 'Test', 'status' => 'ACTIVE',
        ]);
        DB::table('ingestion_runs')->insert([
            'id' => $in['run'], 'data_source_id' => $in['source'], 'kind' => 'BACKFILL', 'timeframe' => '5m', 'status' => 'COMPLETED',
        ]);

        return $in;
    }

    private function bar(array $in, array $o = []): array
    {
        return array_merge([
            'data_source_id' => $in['source'], 'instrument_id' => $in['instrument'], 'timeframe' => '5m',
            'bar_start' => '2026-01-05T10:30:00+05:30', 'trade_date' => '2026-01-05',
            'open' => 100, 'high' => 101, 'low' => 99.5, 'close' => 100.5, 'volume' => 1000, 'ingestion_run_id' => $in['run'],
        ], $o);
    }

    public function test_intraday_bars_are_keyed_by_start_time(): void
    {
        $in = $this->base();
        DB::table('candles')->insert($this->bar($in));
        DB::table('candles')->insert($this->bar($in, ['bar_start' => '2026-01-05T10:35:00+05:30']));       // next 5m bar, same date
        DB::table('candles')->insert($this->bar($in, ['timeframe' => '15m', 'bar_start' => '2026-01-05T10:30:00+05:30']));
        DB::table('candles')->insert($this->bar($in, ['timeframe' => '1m', 'bar_start' => '2026-01-05T10:31:00+05:30']));

        $this->assertRejected(fn () => DB::table('candles')->insert($this->bar($in)));                     // same key
        $this->assertRejected(fn () => DB::table('candles')->insert($this->bar($in, ['timeframe' => '1W', 'bar_start' => '2026-01-05T11:00:00+05:30'])));
        $this->assertRejected(fn () => DB::table('candles')->insert($this->bar($in, ['bar_start' => '2026-01-05T10:40:30+05:30'])));  // not a whole minute
        // trade_date is the IST session date: 20:00 UTC on 01-05 is 01:30 IST on 01-06.
        $this->assertRejected(fn () => DB::table('candles')->insert($this->bar($in, ['bar_start' => '2026-01-05T20:00:00+00:00'])));
        $this->assertRejected(fn () => DB::table('candles')->insert($this->bar($in, ['bar_start' => null])));
        $this->assertSame(4, DB::table('candles')->count());
    }

    public function test_intraday_quality_issue_types_are_accepted(): void
    {
        $in = $this->base();
        foreach (['MISSING_BAR', 'LATE_BAR', 'MISALIGNED_BAR', 'OUTSIDE_SESSION', 'AGGREGATE_MISMATCH', 'OHLC_INVALID', 'DUPLICATE'] as $type) {
            DB::table('data_quality_issues')->insert([
                'id' => $this->id(), 'ingestion_run_id' => $in['run'], 'instrument_id' => $in['instrument'],
                'trade_date' => '2026-01-05', 'issue_type' => $type, 'severity' => 'WARN',
            ]);
        }
        $this->assertSame(7, DB::table('data_quality_issues')->count());
        $this->assertRejected(fn () => DB::table('data_quality_issues')->insert([
            'id' => $this->id(), 'ingestion_run_id' => $in['run'], 'issue_type' => 'INVALID_OHLC', 'severity' => 'WARN',
        ]));
    }

    public function test_correcting_a_bar_archives_the_old_values_and_bumps_the_revision(): void
    {
        $in = $this->base();
        DB::table('candles')->insert($this->bar($in));
        $where = ['instrument_id' => $in['instrument'], 'timeframe' => '5m'];

        DB::table('candles')->where($where)->update(['close' => 100.7, 'high' => 101]);
        $this->assertSame(2, (int) DB::table('candles')->where($where)->value('revision'));
        $old = DB::table('candle_revisions')->sole();
        $this->assertSame([1, '100.50'], [(int) $old->revision, $old->close]);

        // An update that does not change the values keeps the revision and archives nothing.
        DB::table('candles')->where($where)->update(['ingestion_run_id' => $in['run']]);
        DB::table('candles')->where($where)->update(['revision' => 9]);                                    // writers cannot set it
        $this->assertSame(2, (int) DB::table('candles')->where($where)->value('revision'));
        $this->assertSame(1, DB::table('candle_revisions')->count());

        $this->assertRejected(fn () => DB::table('candles')->where($where)->update(['bar_start' => '2026-01-05T10:45:00+05:30']));  // key is fixed
        $this->assertRejected(fn () => DB::table('candle_revisions')->update(['close' => 1]));             // history is immutable

        DB::table('candles')->where($where)->delete();
        $this->assertSame(0, DB::table('candle_revisions')->count());                                      // cascades with the bar
    }

    public function test_intraday_ingestion_runs_name_one_bar_close(): void
    {
        $in = $this->base();
        $run = fn (array $o = []) => DB::table('ingestion_runs')->insert(array_merge([
            'id' => $this->id(), 'data_source_id' => $in['source'], 'kind' => 'INTRADAY_BARS', 'timeframe' => '5m',
            'bar_start' => '2026-01-05T10:30:00+05:30', 'status' => 'RUNNING',
        ], $o));

        $run();
        $run(['timeframe' => '15m']);                                                                      // other timeframe, same bar
        $run(['status' => 'COMPLETED']);                                                                   // finished runs may repeat

        $this->assertRejected(fn () => $run());                                                            // concurrent duplicate
        $this->assertRejected(fn () => $run(['bar_start' => null, 'timeframe' => '5m', 'status' => 'COMPLETED']));
        $this->assertRejected(fn () => $run(['timeframe' => '1D', 'status' => 'COMPLETED']));
        $this->assertRejected(fn () => $run(['timeframe' => '2h', 'status' => 'COMPLETED']));
        $this->assertRejected(fn () => $run(['kind' => 'TICKS', 'status' => 'COMPLETED']));
    }

    public function test_risk_profile_intraday_limits_follow_the_registry_ranges(): void
    {
        $tenant = $this->id();
        $user = $this->id();
        DB::table('tenants')->insert(['id' => $tenant, 'name' => 't', 'slug' => 't'.substr($tenant, -8), 'kind' => 'PERSONAL']);
        DB::table('users')->insert(['id' => $user, 'email' => $user.'@example.com', 'password' => 'x']);
        $profile = fn (array $o = []) => DB::table('risk_profiles')->insert(array_merge([
            'id' => $this->id(), 'tenant_id' => $tenant, 'user_id' => $user, 'version' => random_int(1, 1_000_000), 'is_current' => false,
            'trading_capital' => 100000, 'risk_per_trade_pct' => 0.5, 'max_open_positions' => 2,
            'max_position_value' => 50000, 'daily_loss_limit_pct' => 1.5, 'max_consecutive_losses' => 3, 'max_open_risk_pct' => 1.0,
        ], $o));

        $profile();                                                                                        // ADR-014 planning values, no heat/position %
        $this->assertRejected(fn () => $profile(['max_position_value' => 4999]));
        $this->assertRejected(fn () => $profile(['daily_loss_limit_pct' => 0.4]));
        $this->assertRejected(fn () => $profile(['daily_loss_limit_pct' => 5.1]));
        $this->assertRejected(fn () => $profile(['max_consecutive_losses' => 0]));
        $this->assertRejected(fn () => $profile(['max_open_risk_pct' => 0.2]));
        $this->assertRejected(fn () => $profile(['risk_per_trade_pct' => 2.5]));
    }

    public function test_new_tables_follow_the_single_writer_grants(): void
    {
        if (DB::table('pg_roles')->whereIn('rolname', ['app_backend', 'app_engine'])->count() < 2) {
            $this->markTestSkipped('Roles app_backend and app_engine are not present in this database cluster.');
        }
        $can = fn (string $role, string $table, string $privilege) => (bool) DB::selectOne(
            'SELECT has_table_privilege(?, ?, ?) AS ok', [$role, $table, $privilege]
        )->ok;

        foreach (['candle_revisions', 'analysis_run_inputs'] as $table) {
            $this->assertTrue($can('app_engine', $table, 'INSERT'), $table);
            $this->assertTrue($can('app_engine', $table, 'SELECT'), $table);
            $this->assertFalse($can('app_engine', $table, 'UPDATE'), $table);
            $this->assertTrue($can('app_backend', $table, 'SELECT'), $table);
            $this->assertFalse($can('app_backend', $table, 'INSERT'), $table);
        }
        $this->assertTrue((bool) DB::selectOne(
            "SELECT has_column_privilege('app_engine', 'trade_plans', 'triggered_at', 'UPDATE') AS ok"
        )->ok);
    }
}
