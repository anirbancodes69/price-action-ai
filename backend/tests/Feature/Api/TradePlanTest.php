<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Carbon\CarbonImmutable;
use Database\Seeders\RulesetSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Factory as HttpFactory;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Illuminate\Testing\TestResponse;
use Tests\TestCase;

/** Trade plans (T1-T5, ADR-017): made from the live analysis or by hand, sized by the engine. Expected values are hand-computed. */
class TradePlanTest extends TestCase
{
    use RefreshDatabase;

    private const SOURCE = '22222222-2222-4222-8222-222222222222';

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.engine.url' => 'http://engine.test', 'services.engine.token' => 'tkn', 'services.engine.data_source_id' => self::SOURCE]);
        $this->seed(RulesetSeeder::class);
        CarbonImmutable::setTestNow(CarbonImmutable::parse('2026-11-18 11:00:30', 'Asia/Kolkata')); // a Wednesday
        DB::table('data_sources')->insert(['id' => self::SOURCE, 'mode' => 'DEMO', 'provider' => 'DEMO', 'name' => 'Demo']);
        $id = (string) Str::uuid7();
        DB::table('instruments')->insert(['id' => $id, 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'AAA', 'name' => 'Alpha', 'status' => 'ACTIVE']);
        DB::table('instrument_snapshots')->insert(['instrument_id' => $id, 'effective_from' => '2026-01-01', 'name' => 'Alpha', 'tick_size' => '0.05', 'lot_size' => 1, 'status' => 'ACTIVE']);
    }

    protected function tearDown(): void
    {
        CarbonImmutable::setTestNow();
        parent::tearDown();
    }

    private function user(string $email = 'owner@example.test'): User
    {
        $u = new User(['email' => $email, 'password' => 'a-long-enough-pass']);
        $u->forceFill(['status' => 'ACTIVE'])->save();

        return $u;
    }

    /** @param  array<string, mixed>  $over @return array<string, mixed> */
    private function orbSetup(array $over = []): array
    {
        return $over + [
            'type' => 'OPENING_RANGE_BREAKOUT', 'direction' => 'LONG', 'informational' => false, 'status' => 'ENTRY_CONFIRMED',
            'detected_at' => '2026-11-18T05:30:00+00:00', 'trigger_price' => '1496.50', 'entry' => '1498.10', 'stop' => '1485.25', 'target' => '1529.00',
            'target_source' => 'ZONE', 'rr' => '2.4046', 'rr_below_min' => false, 'paqs' => 90, 'paqs_version' => 'paqs-intraday-0.1.0', 'paqs_components' => [], 'end_reason' => null,
        ];
    }

    /** @param  list<array<string, mixed>>  $setups */
    private function fakeEngine(array $setups, string $asOf = '2026-11-18T05:30:00+00:00', ?array $risk = null): void
    {
        Http::swap(new HttpFactory); // a fresh fake: the first stub registered would otherwise keep winning
        Http::fake([
            'engine.test/internal/v1/analysis' => Http::response([
                'symbol' => 'AAA', 'session_date' => '2026-11-18', 'as_of_ts' => $asOf, 'status' => 'VALID', 'problems' => [], 'ruleset_version' => 'pa-intraday 0.1.0',
                'state_5m' => 'BULLISH', 'state_15m' => 'BULLISH', 'protected_low_5m' => null, 'protected_high_5m' => null, 'transition_direction_5m' => null,
                'levels' => null, 'pivots' => [], 'events' => [], 'zones' => [], 'pools' => [], 'setups' => $setups, 'signal' => null, 'no_setup_reasons' => [],
            ]),
            'engine.test/internal/v1/risk/position-size' => Http::response($risk ?? [
                'quantity' => 33, 'risk_budget' => '500.0', 'risk_per_share' => '12.85', 'actual_risk' => '424.05', 'actual_risk_pct' => '0.42',
                'position_value' => '49437.30', 'rr' => '2.404669', 'rr_after_costs' => '2.28', 'est_round_trip_costs' => '53.08', 'binding_constraint' => 'POSITION_CAP',
                'constraints' => [], 'account_state' => [], 'rounding' => ['entry' => '1498.10', 'stop' => '1485.25', 'target' => '1529.00'], 'warnings' => [], 'errors' => [],
                'ruleset_version' => 'pa-intraday 0.1.0',
            ]),
        ]);
    }

    private function create(User $u, array $body = [], array $headers = []): TestResponse
    {
        return $this->actingAs($u, 'web')->postJson('/api/v1/trade-plans', $body + ['instrument' => 'AAA', 'setup_type' => 'OPENING_RANGE_BREAKOUT'], $headers);
    }

    public function test_it_requires_a_session(): void
    {
        $this->getJson('/api/v1/trade-plans')->assertStatus(401);
        $this->postJson('/api/v1/trade-plans', [])->assertStatus(401);
    }

    public function test_a_plan_from_a_live_setup_is_sized_by_the_engine_and_records_what_it_came_from(): void
    {
        $this->fakeEngine([$this->orbSetup()]);
        $u = $this->user();

        $p = $this->create($u, ['note' => 'ORB over the opening high'])->assertCreated()->json('data');

        Http::assertSent(fn (Request $r) => str_ends_with($r->url(), '/risk/position-size') && $r->data()['book'] === 'ACTUAL' && $r->data()['direction'] === 'LONG'
            && [$r->data()['entry'], $r->data()['stop'], $r->data()['target']] === ['1498.10', '1485.25', '1529.00'] && $r->data()['capital'] === '100000');
        $this->assertSame(
            ['TP-0001', 'PENDING', 'ENGINE', 'LONG', '1498.10', '1485.25', '1529.00', 33, '500.00', '424.05', '49437.30', '2.4047', 'POSITION_CAP'],
            [$p['plan_number'], $p['status'], $p['source'], $p['direction'], $p['entry'], $p['stop'], $p['target'], $p['quantity'], $p['risk_budget'], $p['risk_amount'],
                $p['position_value'], $p['rr'], $p['binding_constraint']],
        );
        $this->assertSame(['entry' => '1498.10', 'stop' => '1485.25', 'target' => '1529.00'], $p['engine_levels']);
        $this->assertSame([false, 'OPENING_RANGE_BREAKOUT', 90, '2026-11-18T11:00:00+05:30', 'pa-intraday 0.1.0', '2026-11-18T14:45:00+05:30', 0, null, 'ORB over the opening high'],
            [$p['levels_overridden'], $p['setup_type'], $p['paqs'], $p['as_of'], $p['ruleset_version'], $p['valid_until'], $p['lock_version'], $p['analysis_run_id'], $p['note']]);
        $this->assertSame(['paper_trade_id' => null, 'actual_trade_ids' => []], $p['linked']);
        $this->assertSame(64, strlen((string) DB::table('trade_plans')->value('setup_key')));
        $this->assertSame(1, DB::table('risk_profiles')->where('is_current', true)->count(), 'the plan records the profile it was sized with');
        $this->assertSame('TP-0002', $this->create($u)->json('data.plan_number'));
    }

    public function test_changed_levels_are_flagged_as_overridden(): void
    {
        $this->fakeEngine([$this->orbSetup()], risk: [
            'quantity' => 40, 'risk_budget' => '500.0', 'actual_risk' => '400.00', 'position_value' => '59924.00', 'rr' => '2.5', 'binding_constraint' => 'RISK_BUDGET',
            'rounding' => ['entry' => '1498.10', 'stop' => '1488.10', 'target' => '1529.00'], 'errors' => [], 'warnings' => [],
        ]);

        $p = $this->create($this->user(), ['stop' => '1488.10'])->assertCreated()->json('data');

        $this->assertSame([true, '1488.10', 'ENGINE', 40], [$p['levels_overridden'], $p['stop'], $p['source'], $p['quantity']]);
        $this->assertSame('1485.25', $p['engine_levels']['stop'], 'the engine\'s own level is kept beside the owner\'s');
    }

    public function test_setups_that_cannot_be_planned_are_refused(): void
    {
        $u = $this->user();
        $cases = [
            'SETUP_NOT_ACTIONABLE' => [[], '2026-11-18T05:30:00+00:00'],
            'SETUP_TERMINAL' => [[$this->orbSetup(['status' => 'INVALIDATED'])], '2026-11-18T05:30:00+00:00'],
            'ENTRY_WINDOW_ELAPSED' => [[$this->orbSetup()], '2026-11-18T09:20:00+00:00'], // 14:50 IST, after the 14:45 cutoff
        ];
        foreach ($cases as $code => [$setups, $asOf]) {
            $this->fakeEngine($setups, $asOf);
            $this->create($u)->assertStatus(422)->assertJsonPath('error.code', $code);
        }
        foreach ([['status' => 'FORMING'], ['informational' => true], ['direction' => 'SHORT'], ['rr_below_min' => true], ['entry' => null]] as $over) {
            $this->fakeEngine([$this->orbSetup($over)]);
            $this->create($u)->assertStatus(422)->assertJsonPath('error.code', 'SETUP_NOT_ACTIONABLE');
        }
        $this->assertSame(0, DB::table('trade_plans')->count());
    }

    public function test_a_risk_rule_violation_is_the_error_and_nothing_is_stored(): void
    {
        $this->fakeEngine([$this->orbSetup()], risk: ['quantity' => 0, 'errors' => ['DAILY_LOSS_LIMIT_REACHED'], 'warnings' => [], 'rounding' => ['entry' => '1498.10', 'stop' => '1485.25', 'target' => '1529.00']]);

        $this->create($this->user())->assertStatus(422)->assertJsonPath('error.code', 'DAILY_LOSS_LIMIT_REACHED');

        $this->assertSame(0, DB::table('trade_plans')->count());
    }

    public function test_a_manual_plan_needs_all_three_levels_and_never_calls_the_analysis(): void
    {
        $this->fakeEngine([]);
        $u = $this->user();

        $this->actingAs($u, 'web')->postJson('/api/v1/trade-plans', ['instrument' => 'AAA', 'entry' => '1498.10'])->assertStatus(422);
        $p = $this->actingAs($u, 'web')->postJson('/api/v1/trade-plans', ['instrument' => 'AAA', 'entry' => '1498.10', 'stop' => '1485.25', 'target' => '1529.00'])
            ->assertCreated()->json('data');

        $this->assertSame(['MANUAL', null, null, null, false], [$p['source'], $p['engine_levels'], $p['setup_type'], $p['paqs'], $p['levels_overridden']]);
        Http::assertNotSent(fn (Request $r) => str_ends_with($r->url(), '/internal/v1/analysis'));
    }

    public function test_the_client_cannot_set_the_quantity_a_run_or_a_setup_id_and_unknown_instruments_are_404(): void
    {
        $this->fakeEngine([$this->orbSetup()]);
        $u = $this->user();

        $this->create($u, ['quantity' => 500])->assertStatus(422);
        $this->create($u, ['analysis_run_id' => (string) Str::uuid()])->assertStatus(422);
        $this->create($u, ['setup_type' => 'NOT_A_SETUP'])->assertStatus(422);
        $this->create($u, ['instrument' => 'NOPE'])->assertStatus(404);
    }

    public function test_an_idempotency_key_creates_the_plan_once(): void
    {
        $this->fakeEngine([$this->orbSetup()]);
        $u = $this->user();

        $a = $this->create($u, [], ['Idempotency-Key' => 'k1'])->assertCreated()->json('data.id');
        $b = $this->create($u, [], ['Idempotency-Key' => 'k1'])->assertCreated()->json('data.id');

        $this->assertSame($a, $b);
        $this->assertSame(1, DB::table('trade_plans')->count());
    }

    public function test_the_list_filters_sorts_and_totals_the_open_plans(): void
    {
        $this->fakeEngine([$this->orbSetup()]);
        $u = $this->user();
        $first = $this->create($u)->json('data.id');
        $this->create($u)->assertCreated();
        $this->actingAs($u, 'web')->postJson("/api/v1/trade-plans/{$first}/cancel")->assertOk();

        $all = $this->actingAs($u, 'web')->getJson('/api/v1/trade-plans')->assertOk();
        $this->assertSame(['TP-0002', 'TP-0001'], array_column($all->json('data'), 'plan_number'), 'newest first');
        $this->assertSame([1, 1, '424.05', '2.4047'], [$all->json('meta.totals.open_count'), $all->json('meta.totals.pending_count'), $all->json('meta.totals.planned_risk'), $all->json('meta.totals.avg_rr_open')]);
        $this->assertSame(['CANCELLED'], array_column($this->actingAs($u, 'web')->getJson('/api/v1/trade-plans?status=CANCELLED')->json('data'), 'status'));
        $this->assertSame(['TP-0001', 'TP-0002'], array_column($this->actingAs($u, 'web')->getJson('/api/v1/trade-plans?sort=plan_number')->json('data'), 'plan_number'));
        $this->assertSame(2, $this->actingAs($u, 'web')->getJson('/api/v1/trade-plans?symbol=aaa')->json('meta.total'));
        $this->assertSame(0, $this->actingAs($u, 'web')->getJson('/api/v1/trade-plans?symbol=ZZZ')->json('meta.total'));
        $this->actingAs($u, 'web')->getJson('/api/v1/trade-plans?status=MAYBE')->assertStatus(422);
        $this->actingAs($u, 'web')->getJson("/api/v1/trade-plans/{$first}")->assertOk()->assertJsonPath('data.status', 'CANCELLED')->assertJsonPath('data.events', []);
    }

    public function test_editing_recomputes_the_size_and_guards_the_version(): void
    {
        $this->fakeEngine([$this->orbSetup()]);
        $u = $this->user();
        $id = $this->create($u)->json('data.id');
        Http::swap(new HttpFactory);
        Http::fake(['engine.test/internal/v1/risk/position-size' => Http::response([
            'quantity' => 40, 'risk_budget' => '500.0', 'actual_risk' => '400.00', 'position_value' => '59924.00', 'rr' => '2.5', 'binding_constraint' => 'RISK_BUDGET',
            'rounding' => ['entry' => '1498.10', 'stop' => '1488.10', 'target' => '1529.00'], 'errors' => [], 'warnings' => [],
        ])]);

        $p = $this->actingAs($u, 'web')->patchJson("/api/v1/trade-plans/{$id}", ['lock_version' => 0, 'stop' => '1488.10', 'note' => 'tighter stop'])->assertOk()->json('data');

        $this->assertSame(['1488.10', 40, '400.00', true, 1, 'tighter stop'], [$p['stop'], $p['quantity'], $p['risk_amount'], $p['levels_overridden'], $p['lock_version'], $p['note']]);
        $this->actingAs($u, 'web')->patchJson("/api/v1/trade-plans/{$id}", ['lock_version' => 0, 'note' => 'stale'])->assertStatus(409)->assertJsonPath('error.code', 'STALE_VERSION');
        $this->actingAs($u, 'web')->patchJson("/api/v1/trade-plans/{$id}", ['note' => 'no version'])->assertStatus(422);
        $this->actingAs($u, 'web')->patchJson("/api/v1/trade-plans/{$id}", ['lock_version' => 1, 'note' => 'note only', 'paper_tracking' => false])->assertOk()->assertJsonPath('data.quantity', 40);
    }

    public function test_only_a_pending_plan_is_editable_and_only_an_open_one_cancellable(): void
    {
        $this->fakeEngine([$this->orbSetup()]);
        $u = $this->user();
        $id = $this->create($u)->json('data.id');

        $c = $this->actingAs($u, 'web')->postJson("/api/v1/trade-plans/{$id}/cancel", ['reason' => 'changed my mind'])->assertOk()->json('data');
        $this->assertSame(['CANCELLED', 'changed my mind'], [$c['status'], $c['status_reason']]);
        $this->actingAs($u, 'web')->postJson("/api/v1/trade-plans/{$id}/cancel")->assertStatus(409)->assertJsonPath('error.code', 'PLAN_NOT_CANCELLABLE');
        $this->actingAs($u, 'web')->patchJson("/api/v1/trade-plans/{$id}", ['lock_version' => 1, 'note' => 'x'])->assertStatus(409)->assertJsonPath('error.code', 'PLAN_NOT_EDITABLE');
    }

    public function test_a_plan_lists_the_trades_logged_against_it(): void
    {
        $this->fakeEngine([$this->orbSetup()]);
        $u = $this->user();
        $plan = $this->create($u)->json('data.id');

        $trade = $this->actingAs($u, 'web')->postJson('/api/v1/actual-trades', [
            'instrument' => 'AAA', 'trade_plan_id' => $plan, 'fill' => ['side' => 'BUY', 'quantity' => 33, 'price' => '1498.10', 'executed_at' => '2026-11-18T10:00:00+05:30'],
        ])->assertCreated()->json('data.id');

        $this->actingAs($u, 'web')->getJson("/api/v1/trade-plans/{$plan}")->assertJsonPath('data.linked.actual_trade_ids', [$trade]);
    }

    /** @return array<string, mixed> */
    private function buy(string $plan, array $over = []): array
    {
        return $over + [
            'instrument' => 'AAA', 'trade_plan_id' => $plan,
            'fill' => ['side' => 'BUY', 'quantity' => 10, 'price' => '1498.10', 'executed_at' => '2026-11-18T10:00:00+05:30'],
        ];
    }

    public function test_logging_a_trade_against_a_plan_takes_its_levels_and_marks_it_filled(): void
    {
        $this->fakeEngine([$this->orbSetup()]);
        $u = $this->user();
        $plan = $this->create($u)->json('data.id');

        $t = $this->actingAs($u, 'web')->postJson('/api/v1/actual-trades', $this->buy($plan))->assertCreated()->json('data');

        $this->assertSame(['1485.25', '1529.00', $plan], [$t['stop'], $t['target'], $t['trade_plan_id']]);
        $p = $this->actingAs($u, 'web')->getJson("/api/v1/trade-plans/{$plan}")->json('data');
        $this->assertSame(['FILLED', 'TRADE_LOGGED', 1, [$t['id']]], [$p['status'], $p['status_reason'], $p['lock_version'], $p['linked']['actual_trade_ids']]);
        $this->actingAs($u, 'web')->postJson("/api/v1/trade-plans/{$plan}/cancel")->assertStatus(409); // already acted on
    }

    public function test_the_owners_own_levels_beat_the_plans_and_a_stop_above_the_fill_is_not_inherited(): void
    {
        $this->fakeEngine([$this->orbSetup()]);
        $u = $this->user();
        $plan = $this->create($u)->json('data.id');

        $own = $this->actingAs($u, 'web')->postJson('/api/v1/actual-trades', $this->buy($plan, ['stop' => '1490.00']))->assertCreated()->json('data');
        $this->assertSame(['1490.00', '1529.00'], [$own['stop'], $own['target']]);

        $plan2 = $this->create($u)->json('data.id');
        $gap = $this->buy($plan2);
        $gap['fill']['price'] = '1480.00'; // filled below the plan's stop: the stop is not inherited
        $t = $this->actingAs($u, 'web')->postJson('/api/v1/actual-trades', $gap)->assertCreated()->json('data');
        $this->assertSame([null, '1529.00'], [$t['stop'], $t['target']]);
    }

    public function test_a_plan_cannot_be_used_for_another_instrument(): void
    {
        $this->fakeEngine([$this->orbSetup()]);
        $u = $this->user();
        $plan = $this->create($u)->json('data.id');
        DB::table('instruments')->insert(['id' => (string) Str::uuid7(), 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'BBB', 'name' => 'Beta', 'status' => 'ACTIVE']);

        $this->actingAs($u, 'web')->postJson('/api/v1/actual-trades', $this->buy($plan, ['instrument' => 'BBB']))->assertStatus(422);

        $this->assertSame('PENDING', DB::table('trade_plans')->where('id', $plan)->value('status'));
        $this->assertSame(0, DB::table('actual_trades')->count());
    }

    public function test_the_journal_takes_the_setup_type_and_r_multiple_from_the_plan(): void
    {
        $this->fakeEngine([$this->orbSetup()]);
        $u = $this->user();
        $plan = $this->create($u)->json('data.id');
        $trade = $this->actingAs($u, 'web')->postJson('/api/v1/actual-trades', $this->buy($plan))->json('data.id');

        $this->actingAs($u, 'web')->postJson("/api/v1/actual-trades/{$trade}/fills", [
            'side' => 'SELL', 'quantity' => 10, 'price' => '1510.00', 'executed_at' => '2026-11-18T11:00:00+05:30',
        ])->assertCreated();

        $t = $this->actingAs($u, 'web')->getJson('/api/v1/journal?kind=ACTUAL')->assertOk()->json('data.0.trade');
        // gross (1510 - 1498.10) x 10 = 119; risk (1498.10 - 1485.25) x 10 = 128.5; 119 / 128.5 truncated to four decimals
        $this->assertSame(['OPENING_RANGE_BREAKOUT', '119.00', '0.926', 'WIN'], [$t['setup_type'], $t['net_pnl'], $t['r_multiple'], $t['outcome']]);
    }

    public function test_plans_of_another_user_are_invisible(): void
    {
        $this->fakeEngine([$this->orbSetup()]);
        $id = $this->create($this->user())->json('data.id');
        $other = $this->user('other@example.test');
        $this->app['auth']->forgetGuards(); // the sanctum guard caches the first request's user within one test

        $this->actingAs($other, 'web')->getJson('/api/v1/trade-plans')->assertJsonPath('meta.total', 0);
        $this->actingAs($other, 'web')->getJson("/api/v1/trade-plans/{$id}")->assertStatus(404);
        $this->actingAs($other, 'web')->postJson("/api/v1/trade-plans/{$id}/cancel")->assertStatus(404);
        $this->actingAs($other, 'web')->patchJson("/api/v1/trade-plans/{$id}", ['lock_version' => 0, 'note' => 'x'])->assertStatus(404);
    }
}
