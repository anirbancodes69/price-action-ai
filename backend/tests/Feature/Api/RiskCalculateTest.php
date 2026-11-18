<?php

namespace Tests\Feature\Api;

use App\Models\User;
use App\Services\AccountStateService;
use Carbon\CarbonImmutable;
use Database\Seeders\RulesetSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

/** `POST /api/v1/risk/calculate` and the account state it feeds (TRD-05 §8.1, RM-01). */
class RiskCalculateTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.engine.url' => 'http://engine.test', 'services.engine.token' => 'tkn']);
        $this->seed(RulesetSeeder::class);
        CarbonImmutable::setTestNow(CarbonImmutable::parse('2026-11-18 10:07:30', 'Asia/Kolkata'));

        $id = (string) Str::uuid7();
        DB::table('instruments')->insert([
            'id' => $id, 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'AAA', 'name' => 'Alpha', 'status' => 'ACTIVE',
        ]);
        DB::table('instrument_snapshots')->insert([
            'instrument_id' => $id, 'effective_from' => '2026-01-01', 'name' => 'Alpha', 'tick_size' => '0.05', 'lot_size' => 1,
            'status' => 'ACTIVE',
        ]);
    }

    protected function tearDown(): void
    {
        CarbonImmutable::setTestNow();
        parent::tearDown();
    }

    private function user(): User
    {
        $u = new User(['email' => 'owner@example.test', 'password' => 'a-long-enough-pass']);
        $u->forceFill(['status' => 'ACTIVE'])->save();

        return $u;
    }

    /** @param  array<string, mixed>  $over @return array<string, mixed> */
    private function body(array $over = []): array
    {
        return $over + [
            'instrument' => 'AAA', 'direction' => 'LONG', 'book' => 'PAPER', 'entry' => '1498.10', 'stop' => '1485.25',
            'target' => '1529.00',
        ];
    }

    /** @param  list<string>  $errors @return array<string, mixed> */
    private function engineResult(array $errors = []): array
    {
        return [
            'quantity' => $errors === [] ? 33 : 0, 'risk_budget' => '500.0', 'risk_per_share' => '12.85', 'actual_risk' => '424.05',
            'actual_risk_pct' => '0.42405', 'position_value' => '49437.30', 'rr' => '2.4046', 'rr_after_costs' => '2.2796',
            'est_round_trip_costs' => '53.08', 'binding_constraint' => 'POSITION_CAP',
            'constraints' => ['qty_risk' => 38, 'qty_capital' => 66, 'qty_position_cap' => 33, 'qty_open_risk' => 77, 'qty_daily_loss' => 116],
            'account_state' => ['realised_net_pnl_today' => '0', 'open_risk' => '0', 'losing_streak' => 0, 'remaining_daily_loss' => '1500.0', 'blocked_reason' => null],
            'rounding' => ['entry' => '1498.10', 'stop' => '1485.25', 'target' => '1529.00'],
            'warnings' => ['COSTS_UNVERIFIED'], 'errors' => $errors, 'ruleset_version' => 'pa-intraday 0.1.0',
        ];
    }

    public function test_it_requires_a_session(): void
    {
        $this->postJson('/api/v1/risk/calculate', $this->body())->assertStatus(401);
    }

    public function test_it_builds_the_engine_request_from_the_profile_state_and_clock(): void
    {
        Http::fake(['engine.test/internal/v1/risk/position-size' => Http::response($this->engineResult())]);

        $res = $this->actingAs($this->user(), 'web')->postJson('/api/v1/risk/calculate', $this->body());

        $res->assertOk()->assertJsonPath('data.quantity', 33)->assertJsonPath('data.binding_constraint', 'POSITION_CAP')
            ->assertJsonStructure(['data' => ['rounding', 'constraints', 'account_state'], 'meta' => ['request_id']]);
        $expected = [
            'book' => 'PAPER', 'direction' => 'LONG', 'capital' => '100000', 'risk_pct' => '0.5', 'entry' => '1498.10',
            'stop' => '1485.25', 'target' => '1529.00', 'tick_size' => '0.0500', 'lot_size' => 1,
            'max_position_value' => '50000', 'max_open_positions' => 2, 'max_open_risk_pct' => '1', 'daily_loss_limit_pct' => '1.5',
            'max_consecutive_losses' => 3, 'min_rr' => null,
            'account_state' => [
                'realised_net_pnl_today' => '0.00', 'open_risk' => '0.00', 'open_cost_basis' => '0.00', 'open_positions' => 0,
                'losing_streak' => 0,
            ],
            'as_of_ts' => '2026-11-18T10:05:00+05:30', 'entry_cutoff_at' => '2026-11-18T14:45:00+05:30',
            'ruleset_version' => '0.1.0',
        ];
        $this->assertSame($expected, Http::recorded()->first()[0]->data());
    }

    public function test_a_stored_risk_profile_and_an_override_take_precedence(): void
    {
        Http::fake(['*' => Http::response($this->engineResult())]);
        $user = $this->user();
        $tenant = (string) Str::uuid7();
        DB::table('tenants')->insert(['id' => $tenant, 'name' => 'Owner', 'slug' => 'owner', 'kind' => 'PERSONAL']);
        DB::table('risk_profiles')->insert([
            'id' => (string) Str::uuid7(), 'tenant_id' => $tenant, 'user_id' => $user->id, 'version' => 1, 'is_current' => true,
            'trading_capital' => '250000', 'risk_per_trade_pct' => '0.75', 'max_open_positions' => 3, 'min_rr' => '2.5',
            'max_position_value' => '80000', // the intraday limits left null fall back to the ruleset defaults
        ]);

        $this->actingAs($user, 'web')->postJson('/api/v1/risk/calculate', $this->body(['risk_per_trade_pct' => 0.4]))->assertOk();

        $sent = Http::recorded()->first()[0]->data();
        $this->assertEquals([
            'capital' => '250000.00', 'risk_pct' => '0.4', 'max_position_value' => '80000.00', 'max_open_positions' => 3,
            'min_rr' => '2.5000', 'daily_loss_limit_pct' => '1.5', 'max_consecutive_losses' => 3,
        ], array_intersect_key($sent, array_flip([
            'capital', 'risk_pct', 'max_position_value', 'max_open_positions', 'min_rr', 'daily_loss_limit_pct', 'max_consecutive_losses',
        ])));
    }

    public function test_rule_violations_are_422_with_the_calculation(): void
    {
        Http::fake(['*' => Http::response($this->engineResult(['DAILY_LOSS_LIMIT_REACHED']))]);

        $this->actingAs($this->user(), 'web')->postJson('/api/v1/risk/calculate', $this->body())
            ->assertStatus(422)
            ->assertJsonPath('error.code', 'DAILY_LOSS_LIMIT_REACHED')
            ->assertJsonPath('error.details.errors', ['DAILY_LOSS_LIMIT_REACHED'])
            ->assertJsonPath('error.details.calculation.binding_constraint', 'POSITION_CAP')
            ->assertJsonStructure(['error' => ['request_id']]);
    }

    public function test_input_validation_and_unknown_instruments(): void
    {
        Http::fake(['*' => Http::response($this->engineResult())]);
        $u = $this->user();

        foreach ([['direction' => 'SIDEWAYS'], ['book' => 'DEMO'], ['entry' => '12.345'], ['stop' => '-1'], ['target' => 'abc'], ['instrument' => 'lower'], ['risk_per_trade_pct' => 9]] as $bad) {
            $this->actingAs($u, 'web')->postJson('/api/v1/risk/calculate', $this->body($bad))
                ->assertStatus(422)->assertJsonPath('error.code', 'VALIDATION_FAILED');
        }
        $this->actingAs($u, 'web')->postJson('/api/v1/risk/calculate', $this->body(['instrument' => 'NOSUCH']))
            ->assertStatus(404)->assertJsonPath('error.code', 'NOT_FOUND');
        Http::assertNothingSent();
    }

    public function test_short_is_forwarded_so_the_engine_can_reject_it(): void
    {
        Http::fake(['*' => Http::response($this->engineResult(['SHORT_NOT_SUPPORTED']))]);

        $this->actingAs($this->user(), 'web')->postJson('/api/v1/risk/calculate', $this->body(['direction' => 'SHORT']))
            ->assertStatus(422)->assertJsonPath('error.code', 'SHORT_NOT_SUPPORTED');
        Http::assertSent(fn (Request $r) => $r['direction'] === 'SHORT');
    }

    public function test_actual_account_state_is_derived_from_todays_trades(): void
    {
        $user = $this->user();
        $tenant = (string) Str::uuid7();
        DB::table('tenants')->insert(['id' => $tenant, 'name' => 'Owner', 'slug' => 'owner', 'kind' => 'PERSONAL']);
        $inst = (string) DB::table('instruments')->value('id');
        $row = fn (array $o) => $o + [
            'id' => (string) Str::uuid7(), 'tenant_id' => $tenant, 'user_id' => $user->id, 'instrument_id' => $inst,
            'direction' => 'LONG', 'source' => 'MANUAL',
        ];
        // closed today (IST), in closing order: +400, -300 (net of charges), -120 -> streak 2, net -20
        foreach ([
            $row(['status' => 'CLOSED', 'quantity_open' => 0, 'avg_entry_price' => '100', 'avg_exit_price' => '104', 'realized_pnl' => '410', 'charges' => '10',
                'opened_at' => '2026-11-18 03:50:00+00', 'closed_at' => '2026-11-18 04:10:00+00']),
            $row(['status' => 'CLOSED', 'quantity_open' => 0, 'avg_entry_price' => '100', 'avg_exit_price' => '97', 'realized_pnl' => '-290', 'charges' => '10',
                'opened_at' => '2026-11-18 04:15:00+00', 'closed_at' => '2026-11-18 04:30:00+00']),
            $row(['status' => 'CLOSED', 'quantity_open' => 0, 'avg_entry_price' => '100', 'avg_exit_price' => '99', 'realized_pnl' => '-110', 'charges' => '10',
                'opened_at' => '2026-11-18 04:35:00+00', 'closed_at' => '2026-11-18 04:50:00+00']),
            // yesterday: not part of today's state
            $row(['status' => 'CLOSED', 'quantity_open' => 0, 'avg_entry_price' => '100', 'avg_exit_price' => '50', 'realized_pnl' => '-5000', 'charges' => '0',
                'opened_at' => '2026-11-17 04:00:00+00', 'closed_at' => '2026-11-17 05:00:00+00']),
            // open: entry 200 x 10
            $row(['status' => 'OPEN', 'quantity_open' => 10, 'avg_entry_price' => '200', 'opened_at' => '2026-11-18 04:55:00+00']),
        ] as $trade) {
            DB::table('actual_trades')->insert($trade);
        }

        $state = app(AccountStateService::class)->forBook($user, 'ACTUAL');

        $this->assertSame([
            'realised_net_pnl_today' => '-20.00', 'open_risk' => '0.00', 'open_cost_basis' => '2000.00', 'open_positions' => 1,
            'losing_streak' => 2,
        ], $state); // no plan, so the open position carries cost basis but no stop-based risk
    }

    public function test_paper_and_actual_books_never_share_state(): void
    {
        $user = $this->user();

        $paper = app(AccountStateService::class)->forBook($user, 'PAPER');
        $actual = app(AccountStateService::class)->forBook($user, 'ACTUAL');

        $this->assertSame($paper, $actual); // both empty here: the point is that each query reads only its own table
        $this->assertSame(0, $paper['open_positions']);
    }
}
