<?php

namespace Tests\Feature\Console;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Tests\TestCase;

/** `source:create-kite`: the PERSONAL Kite data source the token-file shortcut never created. */
class CreateKiteSourceTest extends TestCase
{
    use RefreshDatabase;

    private function owner(string $email = 'owner@example.test'): User
    {
        $u = new User(['email' => $email, 'password' => 'a-long-enough-pass']);
        $u->forceFill(['status' => 'ACTIVE'])->save();

        return $u;
    }

    public function test_it_creates_the_tenant_connection_and_personal_source_and_selects_it(): void
    {
        $owner = $this->owner();

        $this->artisan('source:create-kite')->assertSuccessful()->expectsOutputToContain('Created the PERSONAL Kite data source.');

        $source = DB::table('data_sources')->where('mode', 'PERSONAL')->first();
        $this->assertSame('ZERODHA_KITE', $source->provider);
        $conn = DB::table('provider_connections')->where('id', $source->provider_connection_id)->first();
        $this->assertSame(['CONNECTED', 'ZERODHA_KITE', 'local-token-file', null, $owner->getKey()], [$conn->status, $conn->provider, $conn->provider_user_id, $conn->access_token_encrypted, $conn->user_id]);
        $this->assertSame($conn->tenant_id, $source->tenant_id);
        $this->assertSame($source->id, DB::table('data_source_selections')->where('tenant_id', $source->tenant_id)->value('data_source_id'));
        $this->assertSame(1, DB::table('tenants')->where('kind', 'PERSONAL')->count());
    }

    public function test_running_it_again_changes_nothing_and_prints_the_same_id(): void
    {
        $this->owner();
        $this->artisan('source:create-kite')->assertSuccessful();
        $id = DB::table('data_sources')->where('mode', 'PERSONAL')->value('id');

        $this->artisan('source:create-kite')->assertSuccessful()->expectsOutputToContain('already exists')->expectsOutputToContain($id);

        $this->assertSame(1, DB::table('data_sources')->where('mode', 'PERSONAL')->count());
        $this->assertSame(1, DB::table('provider_connections')->count());
    }

    public function test_it_needs_exactly_one_matching_user(): void
    {
        $this->artisan('source:create-kite')->assertFailed()->expectsOutputToContain('No such user');

        $this->owner('a@example.test');
        $this->owner('b@example.test');
        $this->artisan('source:create-kite')->assertFailed()->expectsOutputToContain('More than one user');
        $this->artisan('source:create-kite', ['email' => 'B@example.test'])->assertSuccessful();
        $this->assertSame(1, DB::table('data_sources')->where('mode', 'PERSONAL')->count());
    }

    public function test_the_global_demo_source_is_left_alone(): void
    {
        DB::table('data_sources')->insert(['id' => '22222222-2222-4222-8222-222222222222', 'mode' => 'DEMO', 'provider' => 'DEMO', 'name' => 'Demo']);
        $this->owner();

        $this->artisan('source:create-kite')->assertSuccessful();

        $this->assertSame(['DEMO', 'PERSONAL'], DB::table('data_sources')->orderBy('mode')->pluck('mode')->all());
    }
}
