<?php

namespace Tests\Feature\Api;

use App\Models\User;
use App\Services\SessionClock;
use App\Services\Trades\ActualTradeService;
use Carbon\CarbonImmutable;
use Database\Seeders\RulesetSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

/** `GET /api/v1/risk/today` (R2): the state is derived here, the limits are the engine's. Expected values are hand-computed. */
class RiskTodayTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.engine.url' => 'http://engine.test', 'services.engine.token' => 'tkn']);
        $this->seed(RulesetSeeder::class);
        CarbonImmutable::setTestNow(CarbonImmutable::parse('2026-11-18 10:07:30', 'Asia/Kolkata')); // a Wednesday
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

    /** @return array<string, mixed> */
    private function engineAnswer(?string $blocked = null): array
    {
        return [
            'account_state' => [
                'realised_net_pnl_today' => '-59', 'open_risk' => '0', 'losing_streak' => 1, 'remaining_daily_loss' => '1441',
                'blocked_reason' => $blocked,
            ],
            'daily_loss_limit' => '1500.0', 'max_consecutive_losses' => 3, 'max_open_positions' => 2,
        ];
    }

    public function test_it_requires_a_session_and_a_book(): void
    {
        $this->getJson('/api/v1/risk/today?book=ACTUAL')->assertStatus(401);
        $this->actingAs($this->user(), 'web')->getJson('/api/v1/risk/today')->assertStatus(422)->assertJsonPath('error.code', 'BOOK_REQUIRED');
    }

    public function test_it_derives_the_state_sends_it_to_the_engine_and_maps_the_answer(): void
    {
        $u = $this->user();
        $inst = (string) Str::uuid7();
        DB::table('instruments')->insert(['id' => $inst, 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'AAA', 'name' => 'Alpha', 'status' => 'ACTIVE']);
        $trades = app(ActualTradeService::class);
        $id = $trades->open($u, $inst, null, ['side' => 'BUY', 'quantity' => 10, 'price' => '100.00', 'executed_at' => '2026-11-18T10:00:00+05:30', 'fees' => '5.00']);
        $trades->addFill($id, ['side' => 'SELL', 'quantity' => 10, 'price' => '95.00', 'executed_at' => '2026-11-18T10:05:00+05:30', 'fees' => '4.00']);
        Http::fake(['engine.test/internal/v1/risk/account-state' => Http::response($this->engineAnswer())]);

        $res = $this->actingAs($u, 'web')->getJson('/api/v1/risk/today?book=ACTUAL')->assertOk();

        Http::assertSent(fn (Request $r) => $r->hasHeader('Authorization', 'Bearer tkn') && $r->data() === [
            'book' => 'ACTUAL', 'capital' => '100000', 'daily_loss_limit_pct' => '1.5', 'max_consecutive_losses' => 3,
            'max_open_positions' => 2,
            // sold 10 at 95 against a cost of 100: -50 gross, 9 of charges
            'account_state' => ['realised_net_pnl_today' => '-59.00', 'open_risk' => '0.00', 'open_cost_basis' => '0.00', 'open_positions' => 0, 'losing_streak' => 1],
            'session_open' => true, 'as_of_ts' => '2026-11-18T10:05:00+05:30', 'entry_cutoff_at' => '2026-11-18T14:45:00+05:30',
        ]);
        $this->assertSame([
            'book' => 'ACTUAL', 'session_date' => '2026-11-18', 'realised_net_pnl_today' => '-59.00', 'open_risk' => '0.00', 'losing_streak' => 1,
            'open_positions' => 0, 'daily_loss_limit' => '1500.00', 'remaining_daily_loss' => '1441.00', 'max_consecutive_losses' => 3,
            'max_open_positions' => 2, 'blocked_reason' => null, 'entry_cutoff_at' => '2026-11-18T14:45:00+05:30',
            'session_end_exit_at' => '2026-11-18T15:15:00+05:30',
        ], $res->json('data'));
    }

    public function test_an_open_trades_own_stop_counts_as_open_risk(): void
    {
        $u = $this->user();
        $inst = (string) Str::uuid7();
        DB::table('instruments')->insert(['id' => $inst, 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'AAA', 'name' => 'Alpha', 'status' => 'ACTIVE']);
        app(ActualTradeService::class)->open($u, $inst, null, ['side' => 'BUY', 'quantity' => 10, 'price' => '100.00', 'executed_at' => '2026-11-18T10:00:00+05:30'], '96.00');
        app(ActualTradeService::class)->open($u, $inst, null, ['side' => 'BUY', 'quantity' => 5, 'price' => '50.00', 'executed_at' => '2026-11-18T10:01:00+05:30']);
        Http::fake(['engine.test/internal/v1/risk/account-state' => Http::response($this->engineAnswer())]);

        $this->actingAs($u, 'web')->getJson('/api/v1/risk/today?book=ACTUAL')->assertOk();

        // 10 shares x (100 - 96) = 40 of risk; the trade without a stop adds none but still counts as a position
        Http::assertSent(fn (Request $r) => $r->data()['account_state']['open_risk'] === '40.00'
            && $r->data()['account_state']['open_positions'] === 2 && $r->data()['account_state']['open_cost_basis'] === '1250.00');
    }

    public function test_the_engines_blocking_reason_is_passed_through(): void
    {
        Http::fake(['engine.test/internal/v1/risk/account-state' => Http::response($this->engineAnswer('DAILY_LOSS_LIMIT_REACHED'))]);

        $this->actingAs($this->user(), 'web')->getJson('/api/v1/risk/today?book=PAPER')->assertOk()
            ->assertJsonPath('data.blocked_reason', 'DAILY_LOSS_LIMIT_REACHED');
    }

    public function test_the_session_is_open_only_on_trading_days_between_open_and_close(): void
    {
        $clock = app(SessionClock::class);
        $at = fn (string $t) => CarbonImmutable::parse($t, 'Asia/Kolkata');

        $this->assertTrue($clock->isOpen($at('2026-11-18 09:15:00')));
        $this->assertFalse($clock->isOpen($at('2026-11-18 09:14:00')));
        $this->assertFalse($clock->isOpen($at('2026-11-18 15:30:00')), 'the close is exclusive');
        $this->assertFalse($clock->isOpen($at('2026-11-21 11:00:00')), 'a Saturday');
        DB::table('market_calendar')->insert(['exchange' => 'NSE', 'calendar_date' => '2026-11-19', 'is_trading_day' => false, 'note' => 'holiday']);
        $this->assertFalse($clock->isOpen($at('2026-11-19 11:00:00')), 'a calendar holiday');
    }
}
