<?php

namespace Tests\Feature\Console;

use App\Models\User;
use App\Services\PersonalTenant;
use App\Services\RiskProfileResolver;
use Carbon\CarbonImmutable;
use Database\Seeders\RulesetSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Tests\TestCase;

class ExpirePlansTest extends TestCase
{
    use RefreshDatabase;

    protected function tearDown(): void
    {
        CarbonImmutable::setTestNow();
        parent::tearDown();
    }

    /** @return array<string, mixed> a plan row insertable on its own, copied from a plan made through the API tests' shape */
    private function plan(string $status, ?string $validUntil): string
    {
        $this->seed(RulesetSeeder::class);

        return $this->insertPlan($status, $validUntil);
    }

    private function insertPlan(string $status, ?string $validUntil): string
    {
        static $n = 0;
        $n++;
        $user = User::query()->first() ?? tap(new User(['email' => 'o@example.test', 'password' => 'a-long-enough-pass']), fn ($u) => $u->forceFill(['status' => 'ACTIVE'])->save());
        $tenant = app(PersonalTenant::class)->idFor($user);
        $inst = DB::table('instruments')->value('id') ?? tap((string) Str::uuid7(), fn ($i) => DB::table('instruments')->insert(['id' => $i, 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'AAA', 'name' => 'Alpha', 'status' => 'ACTIVE']));
        $id = (string) Str::uuid7();
        DB::table('trade_plans')->insert([
            'id' => $id, 'tenant_id' => $tenant, 'user_id' => $user->getKey(), 'plan_number' => $n, 'instrument_id' => $inst, 'source' => 'MANUAL',
            'direction' => 'LONG', 'status' => $status, 'entry_price' => '100.00', 'stop_price' => '98.00', 'target_price' => '105.00', 'quantity' => 10,
            'risk_budget' => '500', 'risk_amount' => '20', 'position_value' => '1000', 'rr' => '2.5', 'binding_constraint' => 'RISK_BUDGET',
            'risk_profile_id' => app(RiskProfileResolver::class)->ensureStored($user),
            'ruleset_version_id' => DB::table('ruleset_versions')->value('id'), 'paper_tracking' => false, 'valid_until' => $validUntil,
        ]);

        return $id;
    }

    public function test_it_closes_plans_past_their_cutoff_and_leaves_the_rest(): void
    {
        CarbonImmutable::setTestNow(CarbonImmutable::parse('2026-11-18 14:50:00', 'Asia/Kolkata'));
        $past = '2026-11-18T14:45:00+05:30';
        $future = '2026-11-18T14:55:00+05:30';
        $pending = $this->plan('PENDING', $past);
        $triggered = $this->insertPlan('TRIGGERED', $past);
        $filled = $this->insertPlan('FILLED', $past);
        $cancelled = $this->insertPlan('CANCELLED', $past);
        $open = $this->insertPlan('PENDING', $future);
        $manual = $this->insertPlan('PENDING', null);

        $this->artisan('plans:expire')->expectsOutput('Closed 2 plan(s) past the entry cutoff.')->assertSuccessful();

        $row = fn (string $id) => DB::table('trade_plans')->where('id', $id)->first(['status', 'status_reason', 'lock_version']);
        $this->assertSame(['EXPIRED', 'SESSION_CUTOFF', 1], [$row($pending)->status, $row($pending)->status_reason, (int) $row($pending)->lock_version]);
        $this->assertSame(['SKIPPED', 'SKIPPED_SESSION_CUTOFF'], [$row($triggered)->status, $row($triggered)->status_reason]);
        $this->assertSame('FILLED', $row($filled)->status);
        $this->assertSame('CANCELLED', $row($cancelled)->status);
        $this->assertSame('PENDING', $row($open)->status);
        $this->assertSame('PENDING', $row($manual)->status);
    }
}
