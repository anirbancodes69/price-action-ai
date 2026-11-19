<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Database\Seeders\RulesetSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Tests\TestCase;

/** `GET/PUT /api/v1/risk-profile` (P3, P4). */
class RiskProfileTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        $this->seed(RulesetSeeder::class);
    }

    private function user(): User
    {
        $u = new User(['email' => 'owner@example.test', 'password' => 'a-long-enough-pass']);
        $u->forceFill(['status' => 'ACTIVE'])->save();

        return $u;
    }

    /** @return array<string, mixed> */
    private function body(array $over = []): array
    {
        return $over + [
            'trading_capital' => '250000', 'risk_per_trade_pct' => '0.75', 'max_position_value' => '80000', 'daily_loss_limit_pct' => '2',
            'max_consecutive_losses' => 4, 'max_open_positions' => 3, 'max_open_risk_pct' => '1.5', 'min_rr' => null, 'max_entry_gap_pct' => null,
        ];
    }

    public function test_it_requires_a_session(): void
    {
        $this->getJson('/api/v1/risk-profile')->assertStatus(401);
        $this->putJson('/api/v1/risk-profile', $this->body())->assertStatus(401);
    }

    public function test_without_a_stored_profile_it_returns_the_ruleset_defaults_and_bounds(): void
    {
        $d = $this->actingAs($this->user(), 'web')->getJson('/api/v1/risk-profile')->assertOk()->json('data');

        $this->assertNull($d['version']);
        $this->assertSame(['100000.00', '0.5', '50000.00', '1.5', 3, 2, '1'], [
            $d['trading_capital'], $d['risk_per_trade_pct'], $d['max_position_value'], $d['daily_loss_limit_pct'],
            $d['max_consecutive_losses'], $d['max_open_positions'], $d['max_open_risk_pct'],
        ]);
        $this->assertSame(['2', '0.3'], [$d['ruleset_bounds']['min_rr'], $d['ruleset_bounds']['max_entry_gap_pct']]);
        $this->assertEquals(['min' => 0.1, 'max' => 2], $d['ruleset_bounds']['ranges']['risk_per_trade_pct']);
    }

    public function test_a_put_stores_a_new_current_version_and_keeps_the_old_one(): void
    {
        $u = $this->user();

        $first = $this->actingAs($u, 'web')->putJson('/api/v1/risk-profile', $this->body())->assertCreated()->json('data');
        $second = $this->actingAs($u, 'web')->putJson('/api/v1/risk-profile', $this->body(['trading_capital' => '300000', 'min_rr' => '2.5', 'max_entry_gap_pct' => '0.2']))
            ->assertCreated()->json('data');

        $this->assertSame([1, 2], [$first['version'], $second['version']]);
        $this->assertSame(['300000.00', '2.5', '0.2'], [$second['trading_capital'], $second['min_rr'], $second['max_entry_gap_pct']]);
        $this->assertSame(2, DB::table('risk_profiles')->count());
        $this->assertSame([2], DB::table('risk_profiles')->where('is_current', true)->pluck('version')->map(fn ($v) => (int) $v)->all());
        $this->actingAs($u, 'web')->getJson('/api/v1/risk-profile')->assertJsonPath('data.version', 2)->assertJsonPath('data.max_open_positions', 3);
    }

    public function test_values_outside_the_ranges_are_rejected(): void
    {
        $u = $this->user();
        foreach ([['trading_capital' => '5000'], ['risk_per_trade_pct' => '2.5'], ['risk_per_trade_pct' => '0.05'], ['daily_loss_limit_pct' => '6'],
            ['max_consecutive_losses' => 11], ['max_open_positions' => 0], ['max_position_value' => '999'], ['max_open_risk_pct' => '0.1']] as $bad) {
            $this->actingAs($u, 'web')->putJson('/api/v1/risk-profile', $this->body($bad))->assertStatus(422);
        }
        $incomplete = $this->body();
        unset($incomplete['min_rr']);
        $this->actingAs($u, 'web')->putJson('/api/v1/risk-profile', $incomplete)->assertStatus(422);
        $this->assertSame(0, DB::table('risk_profiles')->count());
    }

    public function test_the_stricter_than_ruleset_rules(): void
    {
        $u = $this->user();

        $this->actingAs($u, 'web')->putJson('/api/v1/risk-profile', $this->body(['min_rr' => '1.5']))->assertStatus(422)->assertJsonPath('error.code', 'MIN_RR_BELOW_RULESET');
        $this->actingAs($u, 'web')->putJson('/api/v1/risk-profile', $this->body(['max_entry_gap_pct' => '0.5']))->assertStatus(422)->assertJsonPath('error.code', 'MAX_ENTRY_GAP_ABOVE_RULESET');
        $this->actingAs($u, 'web')->putJson('/api/v1/risk-profile', $this->body(['min_rr' => '2', 'max_entry_gap_pct' => '0.3']))->assertCreated();
    }
}
