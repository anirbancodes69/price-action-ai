<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

/** `GET /api/v1/analysis/{symbol}` served live from the engine (ADR-016). Expected values are hand-computed. */
class AnalysisTest extends TestCase
{
    use RefreshDatabase;

    private const SOURCE = '22222222-2222-4222-8222-222222222222';

    protected function setUp(): void
    {
        parent::setUp();
        config([
            'services.engine.url' => 'http://engine.test', 'services.engine.token' => 'tkn',
            'services.engine.data_source_id' => self::SOURCE,
        ]);
        DB::table('data_sources')->insert(['id' => self::SOURCE, 'mode' => 'DEMO', 'provider' => 'DEMO', 'name' => 'Demo']);
        $id = (string) Str::uuid7();
        DB::table('instruments')->insert([
            'id' => $id, 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'AAA', 'name' => 'Alpha Ltd', 'status' => 'ACTIVE',
        ]);
        DB::table('instrument_snapshots')->insert([
            'instrument_id' => $id, 'effective_from' => '2026-01-01', 'name' => 'Alpha Ltd', 'tick_size' => '0.05', 'lot_size' => 1,
            'status' => 'ACTIVE',
        ]);
        DB::table('ruleset_versions')->where('status', 'ACTIVE')->exists()
            || DB::table('ruleset_versions')->insert([
                'id' => (string) Str::uuid7(), 'ruleset_code' => 'pa-intraday', 'version' => '0.1.0', 'status' => 'ACTIVE',
                'score_version' => 'paqs-intraday-0.1.0', 'parameters' => json_encode([
                    'session.entry_cutoff_minutes_before_close' => 45, 'session.exit_minutes_before_close' => 15,
                ]), 'parameters_hash' => str_repeat('a', 64), 'activated_at' => now(), 'validation_status' => 'HYPOTHESIS',
            ]);
    }

    private function user(): User
    {
        $u = new User(['email' => 'owner@example.test', 'password' => 'a-long-enough-pass']);
        $u->forceFill(['status' => 'ACTIVE'])->save();

        return $u;
    }

    /** @return array<string, mixed> */
    private function detail(): array
    {
        return [
            'symbol' => 'AAA', 'session_date' => '2026-11-18', 'as_of_ts' => '2026-11-18T05:30:00+00:00', 'status' => 'VALID',
            'problems' => [], 'ruleset_version' => 'pa-intraday 0.1.0', 'state_5m' => 'BULLISH', 'protected_low_5m' => '1480.00',
            'protected_high_5m' => null, 'transition_direction_5m' => null, 'state_15m' => 'SIDEWAYS',
            'levels' => [
                'pdh' => '1500.00', 'pdl' => '1470.00', 'pdc' => '1480.00', 'or_high' => '1496.50', 'or_low' => '1488.00',
                'session_high' => '1499.00', 'session_low' => '1486.00',
            ],
            'pivots' => [[
                'kind' => 'LOW', 'bar_start' => '2026-11-18T04:00:00+00:00', 'price' => '1486.00', 'label' => 'HL',
                'confirmed_at' => '2026-11-18T04:15:00+00:00',
            ]],
            'events' => [[
                'type' => 'BOS', 'direction' => 'UP', 'level' => '1496.50', 'level_bar_start' => '2026-11-18T04:05:00+00:00',
                'break_bar_start' => '2026-11-18T05:20:00+00:00', 'close' => '1498.10', 'close_inside_buffer' => false,
            ]],
            'zones' => [
                ['role' => 'SUPPORT', 'low' => '1485.00', 'high' => '1488.00', 'touches' => 3, 'strength' => 70, 'strength_bucket' => 'STRONG',
                    'status' => 'ACTIVE', 'role_reversed' => false, 'htf_member' => true, 'formed_at' => '2026-11-18T04:20:00+00:00'],
                ['role' => 'INSIDE', 'low' => '1497.00', 'high' => '1499.00', 'touches' => 1, 'strength' => 20, 'strength_bucket' => 'WEAK',
                    'status' => 'ACTIVE', 'role_reversed' => false, 'htf_member' => false, 'formed_at' => '2026-11-18T05:00:00+00:00'],
            ],
            'pools' => [],
            'setups' => [
                $this->engineSetup('PREV_DAY_HIGH_BREAK', 'AWAITING_CONFIRMATION', 66),
                $this->engineSetup('OPENING_RANGE_BREAKOUT', 'ENTRY_CONFIRMED', 90),
            ],
            'signal' => ['signal' => 'ENTRY_CONFIRMED', 'reasons' => ['OR_BREAK'], 'signal_at' => '2026-11-18T05:30:00+00:00', 'valid_until' => '2026-11-18T05:35:00+00:00'],
            'no_setup_reasons' => [],
        ];
    }

    /** @return array<string, mixed> */
    private function engineSetup(string $type, string $status, int $paqs): array
    {
        return [
            'type' => $type, 'direction' => 'LONG', 'informational' => false, 'status' => $status,
            'detected_at' => '2026-11-18T05:30:00+00:00', 'trigger_price' => '1496.50', 'entry' => '1498.10', 'stop' => '1485.25',
            'target' => '1529.00', 'target_source' => 'ZONE', 'rr' => '2.404669260700389', 'rr_below_min' => false, 'paqs' => $paqs,
            'paqs_version' => 'paqs-intraday-0.1.0',
            'paqs_components' => [['name' => 'structure', 'points' => 20, 'maximum' => 25, 'missing' => false]], 'end_reason' => null,
        ];
    }

    private function fake(): void
    {
        Http::fake(['engine.test/internal/v1/analysis' => Http::response($this->detail())]);
    }

    public function test_it_requires_a_session(): void
    {
        $this->getJson('/api/v1/analysis/AAA')->assertStatus(401);
    }

    public function test_unknown_symbol_is_404_without_calling_the_engine(): void
    {
        Http::fake();

        $this->actingAs($this->user(), 'web')->getJson('/api/v1/analysis/NOPE')->assertStatus(404)->assertJsonPath('error.code', 'NOT_FOUND');
        Http::assertNothingSent();
    }

    public function test_it_calls_the_engine_and_maps_the_analysis_run(): void
    {
        $this->fake();

        $res = $this->actingAs($this->user(), 'web')->getJson('/api/v1/analysis/aaa')->assertOk();

        Http::assertSent(fn (Request $r) => $r->data() === ['data_source_id' => self::SOURCE, 'symbol' => 'AAA']
            && $r->hasHeader('Authorization', 'Bearer tkn'));
        $d = $res->json('data');
        $this->assertSame('2026-11-18T11:00:00+05:30', $d['as_of']);
        $this->assertSame('COMPLETED', $d['status']);
        $this->assertSame('5m', $d['timeframe']);
        $this->assertSame(['code' => 'pa-intraday', 'version' => '0.1.0', 'validation_status' => 'HYPOTHESIS'], $d['ruleset']);
        $this->assertSame('SIDEWAYS', $d['context']['htf_state']);
        $this->assertSame('2026-11-18T14:45:00+05:30', $d['context']['session']['entry_cutoff_at']);
        $this->assertSame('2026-11-18T15:15:00+05:30', $d['context']['session']['session_end_exit_at']);
        $this->assertSame('1496.50', $d['context']['session']['or_high']);
        $this->assertSame(['state' => 'BULLISH', 'transition_direction' => null, 'protected_low' => '1480.00', 'protected_high' => null,
            'summary_text' => '5m structure BULLISH; 15m structure SIDEWAYS.'], $d['structure']);
        $this->assertSame('ENTRY_CONFIRMED', $d['signal']['state']);
        $this->assertSame('2026-11-18T11:05:00+05:30', $d['signal']['valid_until']);
        $this->assertSame('2026-11-18T11:05:00+05:30', $res->json('meta.next_bar_close'));
        $this->assertSame('DEMO', $res->json('meta.data_mode'));

        $swing = $d['swings'][0];
        $this->assertSame(['kind' => 'LOW', 'label' => 'HL', 'price' => '1486.00', 'bar_start' => '2026-11-18T09:30:00+05:30'], [
            'kind' => $swing['kind'], 'label' => $swing['label'], 'price' => $swing['price'], 'bar_start' => $swing['bar_start'],
        ]);
        $this->assertSame('2026-11-18T09:35:00+05:30', $d['events'][0]['level_bar_start']);
        $this->assertSame('1498.10', $d['events'][0]['break_close']);
        $this->assertCount(1, $d['zones'], 'INSIDE zones have no side in the contract');
        $this->assertSame(70, $d['zones'][0]['strength_score']);
    }

    public function test_the_confirmed_setup_is_primary_and_carries_the_signal_window(): void
    {
        $this->fake();

        $d = $this->actingAs($this->user(), 'web')->getJson('/api/v1/analysis/AAA')->assertOk()->json('data');
        $byType = collect($d['setups'])->keyBy('type');

        $this->assertSame($byType['OPENING_RANGE_BREAKOUT']['id'], $d['primary_setup_id']);
        $this->assertSame('2026-11-18T11:05:00+05:30', $byType['OPENING_RANGE_BREAKOUT']['valid_until']);
        $this->assertNull($byType['PREV_DAY_HIGH_BREAK']['valid_until']);
        $this->assertSame('2.4046', $byType['OPENING_RANGE_BREAKOUT']['levels']['rr']);
        $this->assertTrue($byType['OPENING_RANGE_BREAKOUT']['entry_window_open']);
        $this->assertSame(90, $byType['OPENING_RANGE_BREAKOUT']['quality']['score']);
    }

    public function test_ids_are_stable_for_the_same_analysis(): void
    {
        $this->fake();
        $u = $this->user();

        $a = $this->actingAs($u, 'web')->getJson('/api/v1/analysis/AAA')->json('data');
        $b = $this->actingAs($u, 'web')->getJson('/api/v1/analysis/AAA')->json('data');

        $this->assertSame($a['id'], $b['id']);
        $this->assertSame($a['setups'][0]['id'], $b['setups'][0]['id']);
    }

    public function test_as_of_is_passed_to_the_engine_in_utc(): void
    {
        $this->fake();

        $this->actingAs($this->user(), 'web')->getJson('/api/v1/analysis/AAA?as_of='.urlencode('2026-11-18T11:00:00+05:30'))->assertOk();

        Http::assertSent(fn (Request $r) => ($r->data()['as_of_ts'] ?? null) === '2026-11-18T05:30:00Z');
    }

    public function test_include_candles_returns_the_session_5m_bars_before_as_of(): void
    {
        $this->fake();
        $inst = DB::table('instruments')->where('trading_symbol', 'AAA')->value('id');
        $run = (string) Str::uuid7();
        DB::table('ingestion_runs')->insert([
            'id' => $run, 'data_source_id' => self::SOURCE, 'kind' => 'BACKFILL', 'status' => 'COMPLETED', 'started_at' => now(),
        ]);
        foreach (['2026-11-18 05:20:00+00' => '1497.00', '2026-11-18 05:25:00+00' => '1498.00', '2026-11-18 05:30:00+00' => '1499.00'] as $t => $c) {
            DB::table('candles')->insert([
                'data_source_id' => self::SOURCE, 'instrument_id' => $inst, 'timeframe' => '5m', 'trade_date' => '2026-11-18',
                'bar_start' => $t, 'open' => $c, 'high' => $c, 'low' => $c, 'close' => $c, 'volume' => 10, 'ingestion_run_id' => $run,
            ]);
        }

        $res = $this->actingAs($this->user(), 'web')->getJson('/api/v1/analysis/AAA?include=candles')->assertOk();

        $candles = $res->json('data.candles');
        $this->assertCount(2, $candles, 'the 11:00 bar is not closed at as_of 11:00');
        $this->assertSame('2026-11-18T10:55:00+05:30', $candles[1]['start']);
        $this->assertSame('2026-11-18T11:00:00+05:30', $candles[1]['end']);
        $this->assertSame('1498.00', $candles[1]['close']);
        $this->assertSame('DEMO', $res->json('meta.data_mode'));
    }

    public function test_snapshot_statuses_map_to_run_statuses(): void
    {
        $statuses = ['VALID' => 'COMPLETED', 'INSUFFICIENT_HISTORY' => 'INSUFFICIENT_HISTORY', 'INVALID_INPUT' => 'INVALID_INPUT'];
        $sequence = Http::sequence();
        foreach (array_keys($statuses) as $engine) {
            $sequence->push(['status' => $engine] + $this->detail());
        }
        Http::fake(['engine.test/internal/v1/analysis' => $sequence]);
        $u = $this->user();

        foreach ($statuses as $api) {
            $this->assertSame($api, $this->actingAs($u, 'web')->getJson('/api/v1/analysis/AAA')->assertOk()->json('data.status'));
        }
    }

    public function test_an_unavailable_engine_is_503(): void
    {
        Http::fake(['engine.test/*' => Http::response([], 500)]);

        $this->actingAs($this->user(), 'web')->getJson('/api/v1/analysis/AAA')->assertStatus(503)->assertJsonPath('error.code', 'ENGINE_UNAVAILABLE');
    }
}
