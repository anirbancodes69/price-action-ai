<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Illuminate\Testing\TestResponse;
use Tests\TestCase;

/** Manual trade log (X7, X8, X9, X11). Expected values are hand-computed. */
class ActualTradeTest extends TestCase
{
    use RefreshDatabase;

    private const SOURCE = '22222222-2222-4222-8222-222222222222';

    private string $instrument;

    protected function setUp(): void
    {
        parent::setUp();
        config(['services.engine.data_source_id' => self::SOURCE]);
        DB::table('data_sources')->insert(['id' => self::SOURCE, 'mode' => 'DEMO', 'provider' => 'DEMO', 'name' => 'Demo']);
        $this->instrument = (string) Str::uuid7();
        DB::table('instruments')->insert([
            'id' => $this->instrument, 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'AAA', 'name' => 'Alpha Ltd', 'status' => 'ACTIVE',
        ]);
    }

    private function user(string $email = 'owner@example.test'): User
    {
        $u = new User(['email' => $email, 'password' => 'a-long-enough-pass']);
        $u->forceFill(['status' => 'ACTIVE'])->save();

        return $u;
    }

    /** @return array<string, mixed> */
    private function open(User $u, array $over = [], array $headers = []): TestResponse
    {
        return $this->actingAs($u, 'web')->postJson('/api/v1/actual-trades', $over + [
            'instrument' => 'AAA',
            'fill' => ['side' => 'BUY', 'quantity' => 10, 'price' => '100.00', 'executed_at' => '2026-11-18T10:00:00+05:30', 'fees' => '5.00'],
        ], $headers);
    }

    public function test_it_requires_a_session(): void
    {
        $this->getJson('/api/v1/actual-trades')->assertStatus(401);
        $this->postJson('/api/v1/actual-trades', [])->assertStatus(401);
    }

    public function test_a_buy_opens_a_trade_in_the_owners_personal_tenant(): void
    {
        $u = $this->user();

        $d = $this->open($u)->assertCreated()->json('data');

        $this->assertSame('OPEN', $d['status']);
        $this->assertSame(10, $d['quantity_open']);
        $this->assertSame('100.00', $d['avg_entry_price']);
        $this->assertNull($d['realized_pnl']);
        $this->assertSame('5.00', $d['charges']);
        $this->assertSame('AAA', $d['instrument']['symbol']);
        $this->assertCount(1, $d['fills']);
        $this->assertSame('2026-11-18T10:00:00+05:30', $d['fills'][0]['executed_at']);
        $tenant = DB::table('tenant_memberships')->where('user_id', $u->getKey())->first();
        $this->assertSame('OWNER', $tenant->role);
        $this->assertSame(1, DB::table('tenants')->where('kind', 'PERSONAL')->count());
    }

    public function test_sells_close_the_trade_and_realise_the_pnl(): void
    {
        $u = $this->user();
        $id = $this->open($u)->json('data.id');

        $part = $this->actingAs($u, 'web')->postJson("/api/v1/actual-trades/{$id}/fills", [
            'side' => 'SELL', 'quantity' => 4, 'price' => '110.00', 'executed_at' => '2026-11-18T11:00:00+05:30', 'fees' => '3.00',
        ])->assertCreated()->json('data');
        $this->assertSame([6, 'OPEN', '40.00', '8.00'], [$part['quantity_open'], $part['status'], $part['realized_pnl'], $part['charges']]);

        $done = $this->actingAs($u, 'web')->postJson("/api/v1/actual-trades/{$id}/fills", [
            'side' => 'SELL', 'quantity' => 6, 'price' => '95.00', 'executed_at' => '2026-11-18T12:00:00+05:30',
        ])->assertCreated()->json('data');

        $this->assertSame('CLOSED', $done['status']);
        $this->assertSame('10.00', $done['realized_pnl']); // 4 x 10 - 6 x 5, gross of charges
        $this->assertSame('8.00', $done['charges']);
        $this->assertSame('101.00', $done['avg_exit_price']); // (4 x 110 + 6 x 95) / 10
        $this->assertCount(3, $done['fills']);
        $this->assertNotNull(DB::table('actual_trades')->where('id', $id)->value('closed_at'));
    }

    public function test_overselling_is_rejected_and_nothing_is_stored(): void
    {
        $u = $this->user();
        $id = $this->open($u)->json('data.id');

        $this->actingAs($u, 'web')->postJson("/api/v1/actual-trades/{$id}/fills", [
            'side' => 'SELL', 'quantity' => 11, 'price' => '99.00', 'executed_at' => '2026-11-18T11:00:00+05:30',
        ])->assertStatus(422)->assertJsonPath('error.code', 'OVERSELL_NOT_ALLOWED');

        $this->assertSame(1, DB::table('actual_trade_fills')->where('actual_trade_id', $id)->count());
        $this->assertSame(10, (int) DB::table('actual_trades')->where('id', $id)->value('quantity_open'));
    }

    public function test_input_is_validated(): void
    {
        $u = $this->user();
        $bad = fn (array $fill) => $this->open($u, ['fill' => $fill + ['side' => 'BUY', 'quantity' => 1, 'price' => '1.00', 'executed_at' => '2026-11-18T10:00:00+05:30']]);

        $bad(['price' => '0'])->assertStatus(422);
        $bad(['quantity' => 0])->assertStatus(422);
        $bad(['price' => '1.234'])->assertStatus(422);
        $bad(['side' => 'SELL'])->assertStatus(422);
        $bad(['executed_at' => '2099-01-01T10:00:00+05:30'])->assertStatus(422);
        $this->open($u, ['instrument' => 'NOPE'])->assertStatus(404);
        $this->open($u, ['trade_plan_id' => (string) Str::uuid()])->assertStatus(404);
        $this->assertSame(0, DB::table('actual_trades')->count());
    }

    public function test_an_idempotency_key_creates_the_trade_once(): void
    {
        $u = $this->user();

        $a = $this->open($u, [], ['Idempotency-Key' => 'abc-1'])->assertCreated()->json('data.id');
        $b = $this->open($u, [], ['Idempotency-Key' => 'abc-1'])->assertCreated()->json('data.id');

        $this->assertSame($a, $b);
        $this->assertSame(1, DB::table('actual_trades')->count());
    }

    public function test_trades_of_another_user_are_invisible(): void
    {
        $id = $this->open($this->user())->json('data.id');
        $other = $this->user('other@example.test');
        $this->app['auth']->forgetGuards(); // the sanctum guard caches the first request's user within one test

        $this->actingAs($other, 'web')->getJson('/api/v1/actual-trades')->assertOk()->assertJsonPath('meta.total', 0);
        $this->actingAs($other, 'web')->postJson("/api/v1/actual-trades/{$id}/fills", [
            'side' => 'SELL', 'quantity' => 1, 'price' => '1.00', 'executed_at' => '2026-11-18T11:00:00+05:30',
        ])->assertStatus(404);
    }

    public function test_the_list_filters_by_status_and_pages(): void
    {
        $u = $this->user();
        $first = $this->open($u)->json('data.id');
        $this->actingAs($u, 'web')->postJson("/api/v1/actual-trades/{$first}/fills", [
            'side' => 'SELL', 'quantity' => 10, 'price' => '101.00', 'executed_at' => '2026-11-18T11:00:00+05:30',
        ])->assertCreated();
        $this->open($u, ['fill' => ['side' => 'BUY', 'quantity' => 2, 'price' => '50.00', 'executed_at' => '2026-11-18T12:00:00+05:30']])->assertCreated();

        $open = $this->actingAs($u, 'web')->getJson('/api/v1/actual-trades?status=OPEN')->assertOk();
        $this->assertSame([2], array_column($open->json('data'), 'quantity_open'));
        $this->actingAs($u, 'web')->getJson('/api/v1/actual-trades?status=CLOSED')->assertOk()->assertJsonPath('meta.total', 1);

        $page = $this->actingAs($u, 'web')->getJson('/api/v1/actual-trades?limit=1')->assertOk();
        $this->assertCount(1, $page->json('data'));
        $this->assertNotNull($page->json('meta.next_cursor'));
        $this->actingAs($u, 'web')->getJson('/api/v1/actual-trades?status=OTHER')->assertStatus(422);
    }

    public function test_live_positions_price_open_trades_at_the_latest_stored_5m_close(): void
    {
        $u = $this->user();
        $this->open($u)->assertCreated();
        $run = (string) Str::uuid7();
        DB::table('ingestion_runs')->insert(['id' => $run, 'data_source_id' => self::SOURCE, 'kind' => 'BACKFILL', 'status' => 'COMPLETED', 'started_at' => now()]);
        foreach (['2026-11-18 05:25:00+00' => '104.00', '2026-11-18 05:30:00+00' => '103.00'] as $t => $c) {
            DB::table('candles')->insert([
                'data_source_id' => self::SOURCE, 'instrument_id' => $this->instrument, 'timeframe' => '5m', 'trade_date' => '2026-11-18',
                'bar_start' => $t, 'open' => $c, 'high' => $c, 'low' => $c, 'close' => $c, 'volume' => 1, 'ingestion_run_id' => $run,
            ]);
        }

        $res = $this->actingAs($u, 'web')->getJson('/api/v1/positions/live?book=ACTUAL')->assertOk();

        $p = $res->json('data.0');
        $this->assertSame('AAA', $p['symbol']);
        $this->assertSame('103.00', $p['current_price']);
        $this->assertSame('2026-11-18T11:05:00+05:30', $p['price_at']);
        $this->assertSame('30.00', $p['unrealised_pnl']); // (103 - 100) x 10
        $this->assertNull($p['stop']);
        $this->assertNull($p['signal']);
        $this->assertSame('DEMO', $res->json('meta.data_mode'));
        $this->actingAs($u, 'web')->getJson('/api/v1/positions/live?book=PAPER')->assertOk()->assertJsonCount(0, 'data');
        $this->actingAs($u, 'web')->getJson('/api/v1/positions/live')->assertStatus(422)->assertJsonPath('error.code', 'BOOK_REQUIRED');
    }
}
