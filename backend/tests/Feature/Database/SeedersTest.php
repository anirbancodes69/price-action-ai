<?php

namespace Tests\Feature\Database;

use Database\Seeders\DatabaseSeeder;
use Database\Seeders\Demo\DemoIntradayGenerator;
use Database\Seeders\Demo\DemoUniverse;
use Database\Seeders\DemoSeeder;
use Database\Seeders\MarketCalendarSeeder;
use Database\Seeders\RulesetSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Tests\TestCase;

/** T-102 / T-I09: reference and DEMO seed data load into the real schema, satisfy its constraints, and are idempotent. */
class SeedersTest extends TestCase
{
    use RefreshDatabase;

    private function counts(): array
    {
        return array_combine($t = [
            'ruleset_versions', 'universes', 'universe_memberships', 'data_sources', 'instruments', 'instrument_provider_refs',
            'instrument_snapshots', 'ingestion_runs', 'candles', 'market_calendar',
        ], array_map(fn ($table) => DB::table($table)->count(), $t));
    }

    public function test_seeds_pa_intraday_active_and_pa_core_retired(): void
    {
        $this->seed(DatabaseSeeder::class);

        $intraday = DB::table('ruleset_versions')->where(['ruleset_code' => 'pa-intraday', 'version' => '0.1.0'])->sole();
        $core = DB::table('ruleset_versions')->where(['ruleset_code' => 'pa-core', 'version' => '0.1.0'])->sole();
        $params = RulesetSeeder::parameters('pa-intraday', '0.1.0');

        $this->assertSame(['ACTIVE', 'HYPOTHESIS', 'paqs-intraday-0.1.0'], [$intraday->status, $intraday->validation_status, $intraday->score_version]);
        $this->assertSame(RulesetSeeder::parametersHash($params), $intraday->parameters_hash);
        $this->assertEqualsCanonicalizing($params, json_decode($intraday->parameters, true));
        $this->assertCount(41, $params, 'TRD-01 §6 pa-intraday registry has 41 keys');
        $this->assertSame(50000, $params['risk.default_max_position_value']);
        $this->assertSame(0.5, $params['risk.default_risk_per_trade_pct']);

        $this->assertSame('RETIRED', $core->status);
        $this->assertNotNull($core->retired_at);
        // Cross-language canonical form: contracts/scripts/check_ruleset_hash.py computes the same hash for the engine's copy.
        $this->assertSame('6807859f97e9b52b7b3cc02312efacccc4b03660fe2c6cea498379667ff66deb', $core->parameters_hash);
        $this->assertSame('bef6a910bc16d31811baffc70a6dc4e39591379911c461151072e2a1c6189b17', $intraday->parameters_hash);
    }

    public function test_an_active_pa_core_from_before_adr_014_is_retired_on_reseed(): void
    {
        $params = RulesetSeeder::parameters('pa-core', '0.1.0');
        DB::table('ruleset_versions')->insert([
            'id' => RulesetSeeder::id('pa-core', '0.1.0'), 'ruleset_code' => 'pa-core', 'version' => '0.1.0',
            'parameters' => RulesetSeeder::canonicalJson($params), 'parameters_hash' => RulesetSeeder::parametersHash($params),
            'score_version' => 'paqs-0.1.0', 'status' => 'ACTIVE', 'activated_at' => now(),
        ]);

        $this->seed(RulesetSeeder::class);

        $this->assertSame('RETIRED', DB::table('ruleset_versions')->where('ruleset_code', 'pa-core')->value('status'));
        $this->assertSame('ACTIVE', DB::table('ruleset_versions')->where('ruleset_code', 'pa-intraday')->value('status'));
    }

    public function test_seeds_universes_and_demo_membership(): void
    {
        $this->seed(DatabaseSeeder::class);

        $this->assertEqualsCanonicalizing(
            ['NIFTY500', 'NIFTY50', 'NIFTY100', 'NIFTY200', 'NIFTYMIDCAP150', 'DEMO'],
            DB::table('universes')->pluck('code')->all(),
        );
        $demo = DB::table('universes')->where('code', 'DEMO')->sole();
        $this->assertTrue($demo->is_demo);
        $this->assertSame(count(DemoUniverse::EQUITIES), DB::table('universe_memberships')->where('universe_id', $demo->id)->count());
    }

    public function test_seeds_calendar_with_unverified_weekday_defaults(): void
    {
        $this->seed(DatabaseSeeder::class);

        $config = MarketCalendarSeeder::config();
        $this->assertFalse($config['verified'], 'flip only after loading the official NSE holiday list');
        $saturday = DB::table('market_calendar')->where('calendar_date', '2026-11-14')->sole();
        $friday = DB::table('market_calendar')->where('calendar_date', '2026-11-13')->sole();

        $this->assertFalse($saturday->is_trading_day);
        $this->assertNull($saturday->session_open);
        $this->assertTrue($friday->is_trading_day);
        $this->assertSame(['09:15:00', '15:30:00'], [$friday->session_open, $friday->session_close]);
        $this->assertSame(MarketCalendarSeeder::UNVERIFIED_NOTE, $friday->note);
        $this->assertSame(0, DB::table('market_calendar')->where('is_trading_day', true)->where(function ($q) {
            $q->whereNull('note')->orWhere('note', '<>', MarketCalendarSeeder::UNVERIFIED_NOTE);
        })->count(), 'no weekday is presented as verified');
    }

    public function test_seeds_demo_daily_and_intraday_bars(): void
    {
        $this->seed(DatabaseSeeder::class);

        $equities = count(DemoUniverse::EQUITIES);
        $sessions = DemoSeeder::INTRADAY_SESSIONS;
        $this->assertSame($equities * DemoUniverse::SERIES_LENGTH, DB::table('candles')->where('timeframe', '1D')->count());
        $this->assertSame($equities * $sessions * DemoIntradayGenerator::BARS_5M, DB::table('candles')->where('timeframe', '5m')->count());
        $this->assertSame($equities * $sessions * 25, DB::table('candles')->where('timeframe', '15m')->count());
        $this->assertSame(DemoUniverse::AS_OF, DB::table('candles')->max('trade_date'));
        $this->assertSame(0, DB::table('instruments')->where('is_demo', false)->count());

        // Daily bars start at the 09:15 IST session open; intraday bars run from 09:15 to 15:25 (last 5m start).
        $this->assertSame(0, DB::table('candles')->where('timeframe', '1D')
            ->whereRaw("(bar_start AT TIME ZONE 'Asia/Kolkata')::time <> '09:15'")->count());
        $range = DB::selectOne("SELECT min((bar_start AT TIME ZONE 'Asia/Kolkata')::time) AS lo, max((bar_start AT TIME ZONE 'Asia/Kolkata')::time) AS hi
            FROM candles WHERE timeframe = '5m'");
        $this->assertSame(['09:15:00', '15:25:00'], [$range->lo, $range->hi]);

        // Every intraday session agrees with its daily bar (open, high, low, close, volume) and has 75 bars.
        $mismatch = DB::selectOne("
            WITH d AS (SELECT instrument_id, trade_date, open, high, low, close, volume FROM candles WHERE timeframe = '1D'),
            i AS (SELECT instrument_id, trade_date, max(high) h, min(low) l, sum(volume) v, count(*) n,
                    (array_agg(open ORDER BY bar_start))[1] o, (array_agg(close ORDER BY bar_start DESC))[1] c
                  FROM candles WHERE timeframe = '5m' GROUP BY 1, 2)
            SELECT count(*) AS n FROM i JOIN d USING (instrument_id, trade_date)
            WHERE i.h <> d.high OR i.l <> d.low OR i.o <> d.open OR i.c <> d.close OR i.v <> d.volume OR i.n <> 75");
        $this->assertSame(0, $mismatch->n);

        $runs = DB::table('ingestion_runs')->orderBy('timeframe')->pluck('timeframe')->all();
        $this->assertSame(['15m', '1D', '5m'], $runs);
    }

    public function test_seeding_twice_changes_nothing(): void
    {
        $this->seed(DatabaseSeeder::class);
        $first = $this->counts();
        $rulesets = DB::table('ruleset_versions')->orderBy('ruleset_code')->get();

        $this->seed(DatabaseSeeder::class);

        $this->assertSame($first, $this->counts());
        $this->assertEquals($rulesets, DB::table('ruleset_versions')->orderBy('ruleset_code')->get());
    }
}
