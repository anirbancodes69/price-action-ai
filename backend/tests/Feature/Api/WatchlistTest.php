<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Tests\TestCase;

/** Watchlists (W1-W6). */
class WatchlistTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        foreach (['AAA', 'BBB', 'CCC'] as $symbol) {
            DB::table('instruments')->insert([
                'id' => (string) Str::uuid7(), 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => $symbol, 'name' => $symbol.' Ltd', 'status' => 'ACTIVE',
            ]);
        }
    }

    private function user(string $email = 'owner@example.test'): User
    {
        $u = new User(['email' => $email, 'password' => 'a-long-enough-pass']);
        $u->forceFill(['status' => 'ACTIVE'])->save();

        return $u;
    }

    private function as(User $u): static
    {
        return $this->actingAs($u, 'web');
    }

    public function test_it_requires_a_session(): void
    {
        $this->getJson('/api/v1/watchlists')->assertStatus(401);
        $this->postJson('/api/v1/watchlists', ['name' => 'x'])->assertStatus(401);
    }

    public function test_the_first_read_creates_one_default_list_once(): void
    {
        $u = $this->user();

        $a = $this->as($u)->getJson('/api/v1/watchlists')->assertOk()->json('data');
        $b = $this->as($u)->getJson('/api/v1/watchlists')->assertOk()->json('data');

        $this->assertCount(1, $a);
        $this->assertSame(['My watchlist', []], [$a[0]['name'], $a[0]['items']]);
        $this->assertSame($a[0]['id'], $b[0]['id']);
    }

    public function test_create_rename_and_names_are_unique_ignoring_case(): void
    {
        $u = $this->user();
        $id = $this->as($u)->postJson('/api/v1/watchlists', ['name' => ' Breakouts '])->assertCreated()->json('data.id');

        $this->as($u)->postJson('/api/v1/watchlists', ['name' => 'breakouts'])->assertStatus(422)->assertJsonPath('error.code', 'NAME_TAKEN');
        $this->as($u)->patchJson("/api/v1/watchlists/{$id}", ['name' => 'Retests', 'sort_order' => 5])->assertOk()->assertJsonPath('data.name', 'Retests')->assertJsonPath('data.sort_order', 5);
        $this->as($u)->patchJson("/api/v1/watchlists/{$id}", ['name' => 'RETESTS'])->assertOk(); // its own name is not a clash
        $this->as($u)->postJson('/api/v1/watchlists', ['name' => ''])->assertStatus(422);
        $this->as($u)->postJson('/api/v1/watchlists', ['name' => str_repeat('x', 61)])->assertStatus(422);
    }

    public function test_a_client_supplied_id_is_used_once(): void
    {
        $u = $this->user();
        $id = (string) Str::uuid();

        $this->as($u)->postJson('/api/v1/watchlists', ['name' => 'Mine', 'id' => $id])->assertCreated()->assertJsonPath('data.id', $id);
        $this->as($u)->postJson('/api/v1/watchlists', ['name' => 'Other', 'id' => $id])->assertStatus(422);
        $this->assertSame(1, DB::table('watchlists')->where('id', $id)->count());
    }

    public function test_items_are_added_idempotently_and_removed(): void
    {
        $u = $this->user();
        $id = $this->as($u)->getJson('/api/v1/watchlists')->json('data.0.id');

        $this->as($u)->putJson("/api/v1/watchlists/{$id}/items/aaa")->assertOk();
        $this->as($u)->putJson("/api/v1/watchlists/{$id}/items/AAA")->assertOk();
        $list = $this->as($u)->putJson("/api/v1/watchlists/{$id}/items/BBB")->assertOk()->json('data');

        $this->assertSame(['AAA', 'BBB'], array_column($list['items'], 'symbol'));
        $this->assertMatchesRegularExpression('/^\d{4}-\d{2}-\d{2}T[\d:]+\+05:30$/', $list['items'][0]['added_at']);
        $this->as($u)->deleteJson("/api/v1/watchlists/{$id}/items/AAA")->assertNoContent();
        $this->as($u)->deleteJson("/api/v1/watchlists/{$id}/items/AAA")->assertNoContent(); // removing twice is fine
        $this->assertSame(['BBB'], array_column($this->as($u)->getJson('/api/v1/watchlists')->json('data.0.items'), 'symbol'));
        $this->as($u)->putJson("/api/v1/watchlists/{$id}/items/NOPE")->assertStatus(404);
    }

    public function test_a_list_holds_at_most_200_symbols(): void
    {
        $u = $this->user();
        $id = $this->as($u)->getJson('/api/v1/watchlists')->json('data.0.id');
        $instrument = DB::table('instruments')->where('trading_symbol', 'AAA')->value('id');
        $rows = [];
        for ($i = 0; $i < 200; $i++) {
            $other = (string) Str::uuid7();
            DB::table('instruments')->insert(['id' => $other, 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'X'.$i, 'name' => 'x', 'status' => 'ACTIVE']);
            $rows[] = ['watchlist_id' => $id, 'instrument_id' => $other, 'sort_order' => $i];
        }
        DB::table('watchlist_items')->insert($rows);

        $this->as($u)->putJson("/api/v1/watchlists/{$id}/items/AAA")->assertStatus(422)->assertJsonPath('error.code', 'WATCHLIST_FULL');
        $this->as($u)->putJson("/api/v1/watchlists/{$id}/items/X5")->assertOk(); // already present: still fine
        $this->assertNotNull($instrument);
    }

    public function test_the_last_list_cannot_be_deleted_but_others_can(): void
    {
        $u = $this->user();
        $first = $this->as($u)->getJson('/api/v1/watchlists')->json('data.0.id');

        $this->as($u)->deleteJson("/api/v1/watchlists/{$first}")->assertStatus(409)->assertJsonPath('error.code', 'LAST_WATCHLIST');
        $second = $this->as($u)->postJson('/api/v1/watchlists', ['name' => 'Second'])->json('data.id');
        $this->as($u)->putJson("/api/v1/watchlists/{$second}/items/AAA")->assertOk();
        $this->as($u)->deleteJson("/api/v1/watchlists/{$second}")->assertNoContent();

        $this->assertSame(0, DB::table('watchlist_items')->count(), 'items go with their list');
        $this->assertSame(1, DB::table('watchlists')->count());
    }

    public function test_lists_of_another_user_are_invisible(): void
    {
        $owner = $this->user();
        $id = $this->as($owner)->getJson('/api/v1/watchlists')->json('data.0.id');
        $other = $this->user('other@example.test');
        $this->app['auth']->forgetGuards(); // the sanctum guard caches the first request's user within one test

        $this->as($other)->putJson("/api/v1/watchlists/{$id}/items/AAA")->assertStatus(404);
        $this->as($other)->patchJson("/api/v1/watchlists/{$id}", ['name' => 'x'])->assertStatus(404);
        $this->as($other)->deleteJson("/api/v1/watchlists/{$id}")->assertStatus(404);
        $this->as($other)->deleteJson("/api/v1/watchlists/{$id}/items/AAA")->assertStatus(404);
        $this->assertNotSame($id, $this->as($other)->getJson('/api/v1/watchlists')->json('data.0.id'));
    }
}
