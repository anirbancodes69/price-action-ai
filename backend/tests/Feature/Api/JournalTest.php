<?php

namespace Tests\Feature\Api;

use App\Models\User;
use App\Services\Trades\ActualTradeService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Illuminate\Testing\TestResponse;
use Tests\TestCase;

/** Journal of closed actual trades (J1-J3). Expected values are hand-computed. */
class JournalTest extends TestCase
{
    use RefreshDatabase;

    private string $instrument;

    protected function setUp(): void
    {
        parent::setUp();
        $this->instrument = (string) Str::uuid7();
        DB::table('instruments')->insert([
            'id' => $this->instrument, 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'AAA', 'name' => 'Alpha', 'status' => 'ACTIVE',
        ]);
    }

    private function user(string $email = 'owner@example.test'): User
    {
        $u = new User(['email' => $email, 'password' => 'a-long-enough-pass']);
        $u->forceFill(['status' => 'ACTIVE'])->save();

        return $u;
    }

    /** A round trip: buy 10 at 100 (fees 5), sell all at $exit (fees 4). */
    private function trade(User $u, string $exit, string $day = '2026-11-18'): string
    {
        $svc = app(ActualTradeService::class);
        $id = $svc->open($u, $this->instrument, null, ['side' => 'BUY', 'quantity' => 10, 'price' => '100.00', 'executed_at' => "{$day}T10:00:00+05:30", 'fees' => '5.00']);
        $svc->addFill($id, ['side' => 'SELL', 'quantity' => 10, 'price' => $exit, 'executed_at' => "{$day}T11:00:00+05:30", 'fees' => '4.00']);

        return $id;
    }

    private function list(User $u, string $query = 'kind=ACTUAL'): TestResponse
    {
        return $this->actingAs($u, 'web')->getJson('/api/v1/journal?'.$query);
    }

    public function test_it_requires_a_session(): void
    {
        $this->getJson('/api/v1/journal')->assertStatus(401);
    }

    public function test_closing_a_trade_creates_one_draft_entry_with_its_figures(): void
    {
        $u = $this->user();
        $this->trade($u, '110.00');

        $entry = $this->list($u)->assertOk()->assertJsonPath('meta.total', 1)->json('data.0');

        $this->assertSame(['ACTUAL', 'DRAFT'], [$entry['kind'], $entry['status']]);
        $this->assertSame([
            'symbol' => 'AAA', 'setup_type' => null, 'direction' => 'LONG', 'entry_at' => '2026-11-18T10:00:00+05:30', 'exit_at' => '2026-11-18T11:00:00+05:30',
            'entry_price' => '100.00', 'exit_price' => '110.00', 'quantity' => 10, 'net_pnl' => '91.00', 'r_multiple' => null, 'outcome' => 'WIN',
        ], $entry['trade']); // (110 - 100) x 10 - 9 of charges
        $this->assertSame([[], [], [], null, null, null, null], [$entry['tags'], $entry['emotions'], $entry['mistakes'], $entry['notes'], $entry['lessons'], $entry['rating'], $entry['followed_plan']]);
    }

    public function test_an_open_trade_has_no_entry_and_a_closed_one_is_not_duplicated(): void
    {
        $u = $this->user();
        $svc = app(ActualTradeService::class);
        $id = $svc->open($u, $this->instrument, null, ['side' => 'BUY', 'quantity' => 10, 'price' => '100.00', 'executed_at' => '2026-11-18T10:00:00+05:30']);
        $this->assertSame(0, DB::table('journal_entries')->count());

        $svc->addFill($id, ['side' => 'SELL', 'quantity' => 4, 'price' => '101.00', 'executed_at' => '2026-11-18T10:30:00+05:30']);
        $this->assertSame(0, DB::table('journal_entries')->count(), 'a partial sell does not close the trade');
        $svc->addFill($id, ['side' => 'SELL', 'quantity' => 6, 'price' => '99.00', 'executed_at' => '2026-11-18T11:00:00+05:30']);
        $svc->addFill($id, ['side' => 'BUY', 'quantity' => 1, 'price' => '99.00', 'executed_at' => '2026-11-18T11:30:00+05:30']);
        $svc->addFill($id, ['side' => 'SELL', 'quantity' => 1, 'price' => '99.00', 'executed_at' => '2026-11-18T11:45:00+05:30']);

        $this->assertSame(1, DB::table('journal_entries')->count());
    }

    public function test_outcome_filter_search_and_order(): void
    {
        $u = $this->user();
        $this->trade($u, '110.00', '2026-11-17'); // net +91
        $this->trade($u, '95.00', '2026-11-18'); // -50 - 9 = -59
        $this->trade($u, '100.90', '2026-11-19'); // +9 - 9 = 0

        $outcomes = fn (string $q) => array_column(array_column($this->list($u, $q)->json('data'), 'trade'), 'outcome');
        $this->assertSame(['WIN'], $outcomes('kind=ACTUAL&outcome=WIN'));
        $this->assertSame('-59.00', $this->list($u, 'kind=ACTUAL&outcome=LOSS')->json('data.0.trade.net_pnl'));
        $this->assertSame(['BREAKEVEN'], $outcomes('kind=ACTUAL&outcome=BREAKEVEN'));
        $this->assertSame(3, $this->list($u, 'kind=ACTUAL&q=aa')->json('meta.total'));
        $this->assertSame(0, $this->list($u, 'kind=ACTUAL&q=zzz')->json('meta.total'));
        $this->assertSame(
            ['2026-11-19T11:00:00+05:30', '2026-11-18T11:00:00+05:30', '2026-11-17T11:00:00+05:30'],
            array_column(array_column($this->list($u)->json('data'), 'trade'), 'exit_at'),
            'newest close first',
        );
        $this->assertSame(1, $this->list($u, 'kind=ACTUAL&from='.urlencode('2026-11-18T00:00:00+05:30').'&to='.urlencode('2026-11-18T23:59:00+05:30'))->json('meta.total'));
        $this->list($u, 'kind=ACTUAL&outcome=MAYBE')->assertStatus(422);
    }

    public function test_the_paper_journal_is_empty_and_is_the_default(): void
    {
        $u = $this->user();
        $this->trade($u, '110.00');

        $this->list($u, 'kind=PAPER')->assertOk()->assertJsonCount(0, 'data');
        $this->list($u, '')->assertOk()->assertJsonCount(0, 'data');
    }

    public function test_the_owner_writes_notes_tags_and_a_rating(): void
    {
        $u = $this->user();
        $this->trade($u, '110.00');
        $id = $this->list($u)->json('data.0.id');

        $res = $this->actingAs($u, 'web')->patchJson("/api/v1/journal/{$id}", [
            'notes' => "Waited for the retest; it's clean", 'tags' => ['orb', 'a "quoted" tag'], 'emotions' => ['calm'], 'mistakes' => [],
            'lessons' => 'Stay patient', 'rating' => 4, 'followed_plan' => true, 'status' => 'COMPLETE',
        ])->assertOk()->json('data');

        $this->assertSame(["Waited for the retest; it's clean", ['orb', 'a "quoted" tag'], ['calm'], 4, true, 'COMPLETE'], [
            $res['notes'], $res['tags'], $res['emotions'], $res['rating'], $res['followed_plan'], $res['status'],
        ]);
        $this->assertSame('91.00', $res['trade']['net_pnl'], 'trade figures are not editable');
        $this->actingAs($u, 'web')->getJson("/api/v1/journal/{$id}")->assertOk()->assertJsonPath('data.lessons', 'Stay patient');

        $this->actingAs($u, 'web')->patchJson("/api/v1/journal/{$id}", ['rating' => 6])->assertStatus(422);
        $this->actingAs($u, 'web')->patchJson("/api/v1/journal/{$id}", ['tags' => array_fill(0, 21, 'x')])->assertStatus(422);
        $this->actingAs($u, 'web')->patchJson("/api/v1/journal/{$id}", ['notes' => null, 'rating' => null])->assertOk()->assertJsonPath('data.rating', null);
    }

    public function test_entries_of_another_user_are_invisible(): void
    {
        $owner = $this->user();
        $this->trade($owner, '110.00');
        $id = $this->list($owner)->json('data.0.id');
        $other = $this->user('other@example.test');
        $this->app['auth']->forgetGuards(); // the sanctum guard caches the first request's user within one test

        $this->list($other)->assertOk()->assertJsonPath('meta.total', 0);
        $this->actingAs($other, 'web')->getJson("/api/v1/journal/{$id}")->assertStatus(404);
        $this->actingAs($other, 'web')->patchJson("/api/v1/journal/{$id}", ['notes' => 'x'])->assertStatus(404);
    }
}
