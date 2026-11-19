<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\User;
use App\Services\PersonalTenant;
use App\Services\RiskProfileResolver;
use App\Services\RulesetParameters;
use App\Support\ApiException;
use App\Support\ApiResponse;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * `GET/PUT /api/v1/risk-profile` (P3, P4): the owner's sizing and account limits. A PUT stores a new version and makes it
 * current; old versions stay. The ranges are the registry's (TRD-01 §6) and the stricter-than-ruleset rules of P4.
 */
class RiskProfileController extends Controller
{
    /** Allowed ranges; the same bounds the table's CHECK constraints enforce. */
    private const RANGES = [
        'trading_capital' => [10000, 100000000], 'risk_per_trade_pct' => [0.1, 2.0], 'max_position_value' => [5000, 1000000],
        'daily_loss_limit_pct' => [0.5, 5.0], 'max_consecutive_losses' => [1, 10], 'max_open_positions' => [1, 20],
        'max_open_risk_pct' => [0.25, 5.0],
    ];

    public function show(Request $request, RiskProfileResolver $profiles, RulesetParameters $ruleset): JsonResponse
    {
        $user = $this->user($request);
        $p = $profiles->for($user);
        $row = DB::table('risk_profiles')->where('user_id', $user->getKey())->where('is_current', true)->first(['version', 'max_entry_gap_pct']);

        return ApiResponse::ok([
            'version' => $row === null ? null : (int) $row->version,
            'trading_capital' => $this->money($p['capital']),
            'risk_per_trade_pct' => $this->ratio($p['risk_pct']),
            'max_position_value' => $this->money($p['max_position_value']),
            'daily_loss_limit_pct' => $this->ratio($p['daily_loss_limit_pct']),
            'max_consecutive_losses' => $p['max_consecutive_losses'],
            'max_open_positions' => $p['max_open_positions'],
            'max_open_risk_pct' => $this->ratio($p['max_open_risk_pct']),
            'min_rr' => $p['min_rr'] === null ? null : $this->ratio($p['min_rr']),
            'max_entry_gap_pct' => $row?->max_entry_gap_pct === null ? null : $this->ratio((string) $row->max_entry_gap_pct),
            'ruleset_bounds' => [
                'ruleset' => $ruleset->active()['code'].' '.$ruleset->version(),
                'min_rr' => $this->ratio((string) $ruleset->get('risk.min_rr')),
                'max_entry_gap_pct' => $this->ratio((string) $ruleset->get('risk.max_entry_gap_pct')),
                'ranges' => array_map(fn (array $r) => ['min' => $r[0], 'max' => $r[1]], self::RANGES),
            ],
        ]);
    }

    public function update(Request $request, PersonalTenant $tenants, RulesetParameters $ruleset): JsonResponse
    {
        $user = $this->user($request);
        $rules = [];
        foreach (self::RANGES as $field => [$min, $max]) {
            $integer = in_array($field, ['max_consecutive_losses', 'max_open_positions'], true);
            $rules[$field] = ['required', $integer ? 'integer' : 'numeric', "min:$min", "max:$max"];
        }
        $rules['min_rr'] = ['present', 'nullable', 'numeric', 'gt:0', 'max:100'];
        $rules['max_entry_gap_pct'] = ['present', 'nullable', 'numeric', 'gt:0', 'max:100'];
        $v = $request->validate($rules);

        if ($v['min_rr'] !== null && bccomp((string) $v['min_rr'], (string) $ruleset->get('risk.min_rr'), 4) < 0) {
            throw new ApiException('MIN_RR_BELOW_RULESET', 'The minimum reward-to-risk cannot be below the ruleset value.', 422, ['field_errors' => ['min_rr' => ['Below the ruleset minimum.']]]);
        }
        if ($v['max_entry_gap_pct'] !== null && bccomp((string) $v['max_entry_gap_pct'], (string) $ruleset->get('risk.max_entry_gap_pct'), 4) > 0) {
            throw new ApiException('MAX_ENTRY_GAP_ABOVE_RULESET', 'The maximum entry gap cannot exceed the ruleset value.', 422, ['field_errors' => ['max_entry_gap_pct' => ['Above the ruleset maximum.']]]);
        }

        $tenant = $tenants->idFor($user);
        DB::transaction(function () use ($user, $tenant, $v) {
            $version = 1 + (int) DB::table('risk_profiles')->where('tenant_id', $tenant)->where('user_id', $user->getKey())->max('version');
            DB::table('risk_profiles')->where('tenant_id', $tenant)->where('user_id', $user->getKey())->where('is_current', true)->update(['is_current' => false]);
            DB::table('risk_profiles')->insert([
                'id' => (string) Str::uuid7(), 'tenant_id' => $tenant, 'user_id' => $user->getKey(), 'version' => $version,
                'is_current' => true, 'trading_capital' => $v['trading_capital'], 'risk_per_trade_pct' => $v['risk_per_trade_pct'],
                'max_open_positions' => $v['max_open_positions'], 'max_position_value' => $v['max_position_value'],
                'daily_loss_limit_pct' => $v['daily_loss_limit_pct'], 'max_consecutive_losses' => $v['max_consecutive_losses'],
                'max_open_risk_pct' => $v['max_open_risk_pct'], 'min_rr' => $v['min_rr'], 'max_entry_gap_pct' => $v['max_entry_gap_pct'],
            ]);
        });

        return $this->show($request, app(RiskProfileResolver::class), $ruleset)->setStatusCode(201);
    }

    private function user(Request $request): User
    {
        /** @var User $user */
        $user = $request->user();

        return $user;
    }

    private function money(string $v): string
    {
        return bcadd($v, '0', 2);
    }

    private function ratio(string $v): string
    {
        $out = bcadd($v, '0', 4);

        return str_contains($out, '.') ? rtrim(rtrim($out, '0'), '.') : $out;
    }
}
