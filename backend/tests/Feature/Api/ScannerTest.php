<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

/** `GET /api/v1/scanner` served live from the engine (ADR-016). Expected values are hand-computed. */
class ScannerTest extends TestCase
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
        foreach (['AAA' => 'Alpha Ltd', 'BBB' => 'Beta Ltd', 'CCC' => 'Gamma Ltd'] as $symbol => $name) {
            $id = (string) Str::uuid7();
            DB::table('instruments')->insert([
                'id' => $id, 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => $symbol, 'name' => $name,
                'status' => 'ACTIVE',
            ]);
            DB::table('instrument_snapshots')->insert([
                'instrument_id' => $id, 'effective_from' => '2026-01-01', 'name' => $name, 'tick_size' => '0.05',
                'lot_size' => 1, 'status' => 'ACTIVE',
            ]);
        }
    }

    private function user(): User
    {
        $u = new User(['email' => 'owner@example.test', 'password' => 'a-long-enough-pass']);
        $u->forceFill(['status' => 'ACTIVE'])->save();

        return $u;
    }

    /** @param  array<string, mixed>  $over @return array<string, mixed> */
    private function engineRow(string $symbol, array $over = []): array
    {
        return $over + [
            'symbol' => $symbol, 'signal' => 'NO_TRADE', 'setup_type' => null, 'setup_status' => null,
            'direction' => null, 'trigger_price' => null, 'paqs' => null, 'entry' => null, 'stop' => null,
            'target' => null, 'target_source' => null, 'rr' => null, 'quantity' => null, 'risk_amount' => null,
            'position_value' => null, 'binding_constraint' => null, 'reasons' => ['NO_SETUP'], 'signal_at' => null,
            'valid_until' => null, 'last_bar_end' => '2026-11-18T09:55:00+00:00', 'stale' => false,
            'htf_state' => 'BULLISH', 'structure_state' => 'SIDEWAYS', 'last_close' => '1498.10',
            'prev_day_close' => '1480.00',
        ];
    }

    /** @param  list<array<string, mixed>>  $rows */
    private function fakeEngine(array $rows, string $mode = 'DEMO'): void
    {
        Http::fake(['engine.test/internal/v1/scan' => Http::response([
            'as_of_ts' => '2026-11-18T09:56:00+00:00', 'data_mode' => $mode, 'provider' => 'DEMO',
            'ruleset_version' => 'pa-intraday 0.1.0', 'notice' => 'Decision support only.', 'rows' => $rows,
        ])]);
    }

    /** @return list<array<string, mixed>> */
    private function threeRows(): array
    {
        return [
            $this->engineRow('AAA', [
                'signal' => 'ENTRY_CONFIRMED', 'setup_type' => 'OPENING_RANGE_BREAKOUT', 'setup_status' => 'ENTRY_CONFIRMED',
                'direction' => 'LONG', 'trigger_price' => '1496.50', 'paqs' => 90, 'entry' => '1498.10', 'stop' => '1485.25',
                'target' => '1529.00', 'target_source' => 'ZONE', 'rr' => '2.404669260700389', 'quantity' => 33,
                'signal_at' => '2026-11-18T09:55:00+00:00', 'valid_until' => '2026-11-18T10:00:00+00:00',
            ]),
            $this->engineRow('BBB', [
                'signal' => 'BUY_WATCH', 'setup_type' => 'PREV_DAY_HIGH_BREAK', 'setup_status' => 'AWAITING_CONFIRMATION',
                'direction' => 'LONG', 'trigger_price' => '500.00', 'paqs' => 66, 'entry' => '500.00', 'stop' => '495.00',
                'target' => '515.00', 'target_source' => 'PDH', 'rr' => '3', 'htf_state' => 'SIDEWAYS',
                'last_close' => '499.50', 'prev_day_close' => '505.00', 'signal_at' => '2026-11-18T09:55:00+00:00',
                'valid_until' => '2026-11-18T10:30:00+00:00',
            ]),
            $this->engineRow('CCC', [
                'signal' => 'INSUFFICIENT_HISTORY', 'reasons' => ['5m bars 3 < 150'], 'htf_state' => null,
                'structure_state' => null, 'prev_day_close' => null,
            ]),
        ];
    }

    public function test_it_requires_a_session(): void
    {
        $this->getJson('/api/v1/scanner')->assertStatus(401)->assertJsonPath('error.code', 'UNAUTHENTICATED');
    }

    public function test_it_calls_the_engine_with_the_data_source_universe_and_capital(): void
    {
        $this->fakeEngine([]);

        $this->actingAs($this->user(), 'web')->getJson('/api/v1/scanner')->assertOk();

        Http::assertSent(fn (Request $r) => $r->data() === [
            'data_source_id' => self::SOURCE, 'universe_code' => 'NIFTY50', 'account' => ['capital' => '100000'],
            'include_no_trade' => true,
        ] && $r->hasHeader('Authorization', 'Bearer tkn'));
    }

    public function test_rows_are_mapped_to_the_api_shape(): void
    {
        $this->fakeEngine($this->threeRows());

        $res = $this->actingAs($this->user(), 'web')->getJson('/api/v1/scanner')->assertOk();
        $rows = collect($res->json('data'))->keyBy('instrument.symbol');

        $a = $rows['AAA'];
        $this->assertSame('1498.10', $a['last_close']);
        $this->assertSame('18.10', $a['change']);
        $this->assertSame('1.2229', $a['change_pct']); // 18.10 / 1480.00 x 100, truncated to four decimals
        $this->assertNull($a['volume']);
        $this->assertNull($a['analysis_run_id']);
        $this->assertSame('2026-11-18T15:25:00+05:30', $a['as_of']);
        $this->assertSame('ENTRY_CONFIRMED', $a['signal_state']);
        $this->assertSame('2026-11-18T15:25:00+05:30', $a['signal_at']);
        $this->assertSame('2026-11-18T15:30:00+05:30', $a['valid_until']);
        $this->assertSame([
            'type' => 'OPENING_RANGE_BREAKOUT', 'direction' => 'LONG', 'status' => 'ENTRY_CONFIRMED',
            'levels' => [
                'trigger' => '1496.50', 'entry' => '1498.10', 'stop' => '1485.25', 'target' => '1529.00',
                'rr' => '2.4046', 'target_source' => 'ZONE',
            ],
            'quality_score' => 90,
        ], $a['primary_setup']);
        $this->assertSame([
            'id' => $a['instrument']['id'], 'symbol' => 'AAA', 'name' => 'Alpha Ltd', 'exchange' => 'NSE',
            'segment' => 'EQ', 'sector' => null, 'isin' => null, 'status' => 'ACTIVE', 'tick_size' => '0.0500', 'lot_size' => 1,
        ], $a['instrument'] + ['tick_size' => '0.0500']);

        $this->assertSame('-5.50', $rows['BBB']['change']);
        $this->assertSame('-1.0891', $rows['BBB']['change_pct']);

        $c = $rows['CCC']; // a short-history symbol is a plain NO_TRADE row
        $this->assertSame('NO_TRADE', $c['signal_state']);
        $this->assertNull($c['primary_setup']);
        $this->assertNull($c['structure_state']);
        $this->assertNull($c['change']);
        $this->assertNull($c['change_pct']);
    }

    public function test_meta_carries_data_mode_as_of_and_the_next_bar_close(): void
    {
        $this->fakeEngine($this->threeRows(), 'PERSONAL');

        $meta = $this->actingAs($this->user(), 'web')->getJson('/api/v1/scanner')->json('meta');

        $this->assertSame('PERSONAL', $meta['data_mode']);
        $this->assertSame('2026-11-18T15:25:00+05:30', $meta['as_of']);
        $this->assertSame('2026-11-18T15:30:00+05:30', $meta['next_bar_close']);
        $this->assertNull($meta['next_cursor']);
        $this->assertSame(3, $meta['total']);
        $this->assertNotEmpty($meta['request_id']);
    }

    public function test_filters(): void
    {
        $this->fakeEngine($this->threeRows());
        $u = $this->user();
        $symbols = fn (string $qs) => collect($this->actingAs($u, 'web')->getJson('/api/v1/scanner?'.$qs)->assertOk()->json('data'))
            ->pluck('instrument.symbol')->all();

        $this->assertSame(['AAA'], $symbols('signal=ENTRY_CONFIRMED'));
        $this->assertSame(['BBB'], $symbols('setup_type=PREV_DAY_HIGH_BREAK'));
        $this->assertSame(['AAA', 'BBB'], $symbols('min_score=60'));
        $this->assertSame(['AAA'], $symbols('min_score=70'));
        $this->assertSame(['AAA', 'BBB'], $symbols('min_rr=2.4'));
        $this->assertSame(['BBB'], $symbols('min_rr=2.5')); // AAA is 2.4046
        $this->assertSame(['AAA', 'BBB'], $symbols('min_rr=2'));
        $this->assertSame(['BBB'], $symbols('htf_state=SIDEWAYS'));
        $this->assertSame(['CCC'], $symbols('q=gamma'));
        $this->assertSame(['AAA'], $symbols('setup_status=ENTRY_CONFIRMED&direction=LONG'));
        $this->assertSame([], $symbols('structure=BULLISH'));
    }

    public function test_sorting_and_cursor_pagination(): void
    {
        $this->fakeEngine($this->threeRows());
        $u = $this->user();

        $sorted = $this->actingAs($u, 'web')->getJson('/api/v1/scanner?sort=-change_pct');
        $this->assertSame(['AAA', 'BBB', 'CCC'], collect($sorted->json('data'))->pluck('instrument.symbol')->all());
        $this->assertSame(['AAA', 'BBB', 'CCC'], collect($this->actingAs($u, 'web')->getJson('/api/v1/scanner?sort=symbol')->json('data'))->pluck('instrument.symbol')->all());

        $first = $this->actingAs($u, 'web')->getJson('/api/v1/scanner?limit=2')->assertOk();
        $this->assertCount(2, $first->json('data'));
        $cursor = $first->json('meta.next_cursor');
        $this->assertNotNull($cursor);

        $second = $this->actingAs($u, 'web')->getJson('/api/v1/scanner?limit=2&cursor='.$cursor)->assertOk();
        $this->assertSame(['CCC'], collect($second->json('data'))->pluck('instrument.symbol')->all());
        $this->assertNull($second->json('meta.next_cursor'));
    }

    public function test_bad_parameters_are_rejected(): void
    {
        $this->fakeEngine($this->threeRows());
        $u = $this->user();

        $this->actingAs($u, 'web')->getJson('/api/v1/scanner?cursor=!!!')->assertStatus(400)->assertJsonPath('error.code', 'INVALID_CURSOR');
        $this->actingAs($u, 'web')->getJson('/api/v1/scanner?signal=HOLD')->assertStatus(422)->assertJsonPath('error.code', 'VALIDATION_FAILED');
        $this->actingAs($u, 'web')->getJson('/api/v1/scanner?limit=101')->assertStatus(422);
        $this->actingAs($u, 'web')->getJson('/api/v1/scanner?sort=-secret')->assertStatus(422);
        // not available from the live engine (ADR-016)
        $this->actingAs($u, 'web')->getJson('/api/v1/scanner?near=SUPPORT')->assertStatus(422)->assertJsonStructure(['error' => ['details' => ['field_errors' => ['near']]]]);
    }

    public function test_setup_type_filter_follows_the_strategy_registry(): void
    {
        $this->fakeEngine($this->threeRows());
        $u = $this->user();

        // implemented, informational and research types the engine can emit are valid filters
        foreach (['OPENING_RANGE_BREAKOUT', 'PREV_DAY_HIGH_BREAK', 'PREV_DAY_LOW_BREAK', 'BREAKOUT_RETEST', 'LIQUIDITY_SWEEP_REVERSAL', 'FAILED_BREAKDOWN_RECLAIM'] as $type) {
            $this->actingAs($u, 'web')->getJson('/api/v1/scanner?setup_type='.$type)->assertOk();
        }
        // unsupported and legacy identifiers must not silently return an empty list (Phase 1 P4)
        foreach (['TREND_CONTINUATION', 'SUPPORT_REJECTION', 'TREND_PULLBACK'] as $type) {
            $this->actingAs($u, 'web')->getJson('/api/v1/scanner?setup_type='.$type)->assertStatus(422)->assertJsonPath('error.code', 'VALIDATION_FAILED');
        }
    }

    public function test_an_unavailable_engine_is_a_503_envelope(): void
    {
        Http::fake(['*' => Http::response([], 500)]);

        $this->actingAs($this->user(), 'web')->getJson('/api/v1/scanner')
            ->assertStatus(503)->assertJsonPath('error.code', 'ENGINE_UNAVAILABLE')
            ->assertJsonStructure(['error' => ['code', 'message', 'request_id']]);
    }
}
