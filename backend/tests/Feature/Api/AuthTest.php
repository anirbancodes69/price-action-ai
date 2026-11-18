<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Tests\TestCase;

/** Owner login and the API envelope (ARC-04 §2.4, §2.5, A3, A4, A9). */
class AuthTest extends TestCase
{
    use RefreshDatabase;

    private const ORIGIN = ['Origin' => 'http://localhost:3000']; // a stateful (SPA) origin

    /** A request as the SPA sends it: stateful origin plus a valid CSRF token (Sanctum validates it). */
    private function spa(): static
    {
        return $this->withSession(['_token' => 'test-csrf-token'])
            ->withHeaders(self::ORIGIN + ['X-CSRF-TOKEN' => 'test-csrf-token']);
    }

    private function owner(string $status = 'ACTIVE', string $password = 'correct horse battery'): User
    {
        $user = new User(['email' => 'owner@example.test', 'password' => $password]);
        $user->forceFill(['email_verified_at' => now(), 'status' => $status])->save();

        return $user;
    }

    public function test_login_returns_the_user_and_starts_a_session(): void
    {
        $user = $this->owner();

        $response = $this->spa()->postJson('/api/v1/auth/login', [
            'email' => 'owner@example.test', 'password' => 'correct horse battery',
        ]);

        $response->assertOk()
            ->assertJsonPath('data.user.id', $user->id)
            ->assertJsonPath('data.user.email', 'owner@example.test')
            ->assertJsonPath('data.user.email_verified', true)
            ->assertJsonPath('data.user.display_name', null)
            ->assertJsonStructure(['data' => ['user'], 'meta' => ['request_id']]);
        $this->assertAuthenticatedAs($user, 'web');
        $this->assertNotNull($user->fresh()->last_login_at);
        $this->assertSame($response->json('meta.request_id'), $response->headers->get('X-Request-Id'));
    }

    public function test_wrong_password_and_unknown_email_fail_the_same_generic_way(): void
    {
        $this->owner();

        $wrong = $this->spa()->postJson('/api/v1/auth/login', [
            'email' => 'owner@example.test', 'password' => 'nope-nope-nope',
        ]);
        $unknown = $this->spa()->postJson('/api/v1/auth/login', [
            'email' => 'nobody@example.test', 'password' => 'nope-nope-nope',
        ]);

        foreach ([$wrong, $unknown] as $r) {
            $r->assertStatus(422)->assertJsonPath('error.code', 'INVALID_CREDENTIALS');
        }
        $this->assertSame($wrong->json('error.message'), $unknown->json('error.message'));
        $this->assertGuest('web');
    }

    public function test_a_suspended_account_gets_423_after_a_correct_password(): void
    {
        $this->owner('SUSPENDED');

        $this->spa()->postJson('/api/v1/auth/login', [
            'email' => 'owner@example.test', 'password' => 'correct horse battery',
        ])->assertStatus(423)->assertJsonPath('error.code', 'ACCOUNT_SUSPENDED');
        $this->assertGuest('web');
    }

    public function test_malformed_login_is_a_validation_error_with_field_errors(): void
    {
        $this->spa()->postJson('/api/v1/auth/login', ['email' => 'not-an-email'])
            ->assertStatus(422)
            ->assertJsonPath('error.code', 'VALIDATION_FAILED')
            ->assertJsonStructure(['error' => ['details' => ['field_errors' => ['email', 'password']], 'request_id']]);
    }

    public function test_login_attempts_are_rate_limited(): void
    {
        $this->owner();
        $body = ['email' => 'owner@example.test', 'password' => 'wrong-wrong-wrong'];

        for ($i = 0; $i < 5; $i++) {
            $status = $this->spa()->postJson('/api/v1/auth/login', $body)->getStatusCode();
            $this->assertSame(422, $status, "attempt {$i}");
        }
        $this->spa()->postJson('/api/v1/auth/login', $body)
            ->assertStatus(429)
            ->assertJsonPath('error.code', 'RATE_LIMITED')
            ->assertHeader('Retry-After');
    }

    public function test_me_requires_a_session(): void
    {
        $this->getJson('/api/v1/me')
            ->assertStatus(401)
            ->assertJsonPath('error.code', 'UNAUTHENTICATED')
            ->assertJsonStructure(['error' => ['code', 'message', 'request_id']]);
    }

    public function test_me_returns_the_user_summary(): void
    {
        $user = $this->owner();

        $response = $this->actingAs($user, 'web')->getJson('/api/v1/me');

        $response->assertOk()->assertExactJson([
            'data' => ['user' => [
                'id' => $user->id, 'email' => 'owner@example.test', 'email_verified' => true,
                'display_name' => null, 'experience_level' => null, 'timezone' => null,
            ]],
            'meta' => ['request_id' => $response->headers->get('X-Request-Id')],
        ]);
    }

    public function test_a_stateful_post_without_a_csrf_token_is_rejected(): void
    {
        // Laravel skips CSRF validation when the environment is `testing` (CI sets APP_ENV=testing at the OS level,
        // which also beats phpunit.xml). Pin a normal environment so this test means the same everywhere.
        $this->app['env'] = 'local';
        $this->owner();

        $this->withHeaders(self::ORIGIN)->postJson('/api/v1/auth/login', [
            'email' => 'owner@example.test', 'password' => 'correct horse battery',
        ])->assertStatus(419)->assertJsonPath('error.code', 'CSRF_TOKEN_MISMATCH');
        $this->assertGuest('web');
    }

    public function test_logout_ends_the_session(): void
    {
        $user = $this->owner();

        $this->actingAs($user, 'web')->spa()->postJson('/api/v1/auth/logout')->assertNoContent();
        $this->assertGuest('web');
    }

    public function test_request_ids_are_echoed_when_valid_and_generated_otherwise(): void
    {
        $this->getJson('/api/v1/me', ['X-Request-Id' => 'req-12345678'])->assertHeader('X-Request-Id', 'req-12345678');

        $generated = $this->getJson('/api/v1/me', ['X-Request-Id' => "bad id\n"])->headers->get('X-Request-Id');
        $this->assertMatchesRegularExpression('/^[0-9a-f-]{36}$/', (string) $generated);
    }

    public function test_unknown_api_paths_use_the_error_envelope(): void
    {
        $this->getJson('/api/v1/nope')->assertStatus(404)->assertJsonPath('error.code', 'NOT_FOUND');
    }

    public function test_owner_create_makes_a_hashed_verified_active_user_and_resets_on_rerun(): void
    {
        $this->artisan('owner:create', ['email' => 'Owner@Example.test', '--password' => 'a-long-enough-pass'])
            ->assertSuccessful();

        $user = User::query()->where('email', 'owner@example.test')->firstOrFail();
        $this->assertSame('ACTIVE', $user->status);
        $this->assertNotNull($user->email_verified_at);
        $this->assertTrue(Hash::check('a-long-enough-pass', $user->password));
        $this->assertStringNotContainsString('a-long-enough-pass', $user->getRawOriginal('password'));

        $this->artisan('owner:create', ['email' => 'owner@example.test', '--password' => 'another-long-pass'])
            ->assertSuccessful();
        $this->assertSame(1, User::query()->count());
        $this->assertTrue(Hash::check('another-long-pass', $user->fresh()->password));
    }

    public function test_owner_create_rejects_a_short_password(): void
    {
        $this->artisan('owner:create', ['email' => 'owner@example.test', '--password' => 'short'])->assertFailed();
        $this->assertSame(0, User::query()->count());
    }
}
