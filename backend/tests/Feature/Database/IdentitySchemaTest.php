<?php

namespace Tests\Feature\Database;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Tests\TestCase;

/** ARC-03 §4–§5: constraints that must hold even if application code has a bug. */
class IdentitySchemaTest extends TestCase
{
    use AssertsDatabaseRejects;
    use RefreshDatabase;

    private function tenant(string $slug = 'acme'): string
    {
        $id = (string) Str::uuid7();
        DB::table('tenants')->insert(['id' => $id, 'name' => $slug, 'slug' => $slug, 'kind' => 'PERSONAL']);

        return $id;
    }

    private function user(string $email = 'a@example.com'): string
    {
        $id = (string) Str::uuid7();
        DB::table('users')->insert(['id' => $id, 'email' => $email, 'password' => 'x']);

        return $id;
    }

    public function test_emails_and_slugs_are_case_insensitive_unique(): void
    {
        $this->user('Trader@Example.com');
        $this->tenant('Alpha');

        $this->assertRejected(fn () => $this->user('trader@example.COM'));
        $this->assertRejected(fn () => $this->tenant('ALPHA'));
    }

    public function test_enum_checks_reject_unknown_values(): void
    {
        $this->assertRejected(fn () => DB::table('tenants')->insert(
            ['id' => (string) Str::uuid7(), 'name' => 'x', 'slug' => 'x', 'kind' => 'TEAM']
        ));
        $this->assertRejected(fn () => DB::table('users')->insert(
            ['id' => (string) Str::uuid7(), 'email' => 'b@example.com', 'password' => 'x', 'status' => 'BANNED']
        ));
    }

    public function test_membership_is_unique_per_tenant_and_user(): void
    {
        [$tenant, $user] = [$this->tenant(), $this->user()];
        $row = fn () => ['id' => (string) Str::uuid7(), 'tenant_id' => $tenant, 'user_id' => $user, 'role' => 'OWNER'];

        DB::table('tenant_memberships')->insert($row());
        $this->assertRejected(fn () => DB::table('tenant_memberships')->insert($row()));
    }

    public function test_only_one_current_risk_profile_per_user(): void
    {
        [$tenant, $user] = [$this->tenant(), $this->user()];
        $profile = fn (int $version, bool $current, array $override = []) => array_merge([
            'id' => (string) Str::uuid7(), 'tenant_id' => $tenant, 'user_id' => $user, 'version' => $version,
            'is_current' => $current, 'trading_capital' => 500000, 'risk_per_trade_pct' => 1,
            'max_open_positions' => 5, 'max_portfolio_heat_pct' => 5, 'max_position_pct' => 25,
        ], $override);

        DB::table('risk_profiles')->insert($profile(1, false));
        DB::table('risk_profiles')->insert($profile(2, true));

        $this->assertRejected(fn () => DB::table('risk_profiles')->insert($profile(3, true)));
    }

    public function test_risk_profile_ranges_are_enforced(): void
    {
        [$tenant, $user] = [$this->tenant(), $this->user()];
        $base = ['tenant_id' => $tenant, 'user_id' => $user, 'is_current' => false, 'trading_capital' => 500000,
            'risk_per_trade_pct' => 1, 'max_open_positions' => 5, 'max_portfolio_heat_pct' => 5, 'max_position_pct' => 25];

        foreach ([
            ['trading_capital' => 9999],
            ['risk_per_trade_pct' => 2.5],
            ['risk_per_trade_pct' => 0.05],
            ['max_open_positions' => 21],
            ['max_portfolio_heat_pct' => 11],
            ['max_position_pct' => 4],
        ] as $i => $bad) {
            $this->assertRejected(fn () => DB::table('risk_profiles')->insert(
                array_merge($base, ['id' => (string) Str::uuid7(), 'version' => $i + 1], $bad)
            ));
        }
    }

    public function test_active_entitlements_cannot_overlap_but_expired_ones_can(): void
    {
        $tenant = $this->tenant();
        $entitlement = fn (string $status, string $from, ?string $to) => [
            'id' => (string) Str::uuid7(), 'tenant_id' => $tenant, 'plan_code' => 'PERSONAL',
            'status' => $status, 'source' => 'DEFAULT', 'valid_from' => $from, 'valid_to' => $to,
        ];

        DB::table('subscription_entitlements')->insert($entitlement('ACTIVE', '2026-01-01', '2026-06-01'));
        DB::table('subscription_entitlements')->insert($entitlement('EXPIRED', '2026-02-01', '2026-03-01'));
        DB::table('subscription_entitlements')->insert($entitlement('ACTIVE', '2026-06-01', null));

        $this->assertRejected(fn () => DB::table('subscription_entitlements')->insert(
            $entitlement('ACTIVE', '2026-07-01', null)
        ));
    }

    public function test_data_source_mode_ownership_rules(): void
    {
        [$tenant, $user] = [$this->tenant(), $this->user()];
        $connection = (string) Str::uuid7();
        DB::table('provider_connections')->insert([
            'id' => $connection, 'tenant_id' => $tenant, 'user_id' => $user,
            'provider' => 'ZERODHA_KITE', 'status' => 'PENDING',
        ]);
        $source = fn (array $override) => array_merge(
            ['id' => (string) Str::uuid7(), 'name' => 'src', 'status' => 'ACTIVE'], $override
        );

        // Valid: global DEMO source, tenant-owned PERSONAL source with a connection.
        DB::table('data_sources')->insert($source(['mode' => 'DEMO', 'provider' => 'DEMO']));
        DB::table('data_sources')->insert($source([
            'mode' => 'PERSONAL', 'provider' => 'ZERODHA_KITE',
            'tenant_id' => $tenant, 'provider_connection_id' => $connection,
        ]));

        // PERSONAL without a tenant/connection, DEMO owned by a tenant, and a second global DEMO are all invalid.
        $this->assertRejected(fn () => DB::table('data_sources')->insert($source(['mode' => 'PERSONAL', 'provider' => 'ZERODHA_KITE'])));
        $this->assertRejected(fn () => DB::table('data_sources')->insert($source(['mode' => 'DEMO', 'provider' => 'DEMO', 'tenant_id' => $tenant])));
        $this->assertRejected(fn () => DB::table('data_sources')->insert($source(['mode' => 'DEMO', 'provider' => 'DEMO'])));
    }

    public function test_audit_log_ids_are_generated_and_cannot_be_supplied(): void
    {
        DB::table('audit_logs')->insert(['actor_type' => 'SYSTEM', 'action' => 'test.first']);
        DB::table('audit_logs')->insert(['actor_type' => 'SYSTEM', 'action' => 'test.second']);

        $ids = DB::table('audit_logs')->orderBy('id')->pluck('id')->all();
        $this->assertCount(2, $ids);
        $this->assertLessThan($ids[1], $ids[0]);

        $this->assertRejected(fn () => DB::table('audit_logs')->insert(['id' => 999, 'actor_type' => 'SYSTEM', 'action' => 'x']));
        $this->assertRejected(fn () => DB::table('audit_logs')->insert(['actor_type' => 'ROBOT', 'action' => 'x']));
    }
}
