<?php

namespace App\Services;

use App\Models\User;
use Illuminate\Support\Facades\DB;

/**
 * The owner's current risk profile, or the ruleset defaults with the planning capital when none is stored yet
 * (the risk-profile endpoints are not built). Values are decimal strings.
 */
class RiskProfileResolver
{
    public function __construct(private readonly RulesetParameters $ruleset) {}

    /** The trading capital alone: the stored profile's, else the planning default (needs no ruleset). */
    public function capital(User $user): string
    {
        $stored = DB::table('risk_profiles')->where('user_id', $user->getKey())->where('is_current', true)->value('trading_capital');

        return $stored === null ? (string) config('trading.capital') : (string) $stored;
    }

    /**
     * @return array{capital: string, risk_pct: string, max_position_value: string, daily_loss_limit_pct: string,
     *     max_consecutive_losses: int, max_open_positions: int, max_open_risk_pct: string, min_rr: string|null}
     */
    public function for(User $user): array
    {
        $defaults = [
            'capital' => (string) config('trading.capital'),
            'risk_pct' => (string) $this->ruleset->get('risk.default_risk_per_trade_pct'),
            'max_position_value' => (string) $this->ruleset->get('risk.default_max_position_value'),
            'daily_loss_limit_pct' => (string) $this->ruleset->get('risk.default_daily_loss_limit_pct'),
            'max_consecutive_losses' => (int) $this->ruleset->get('risk.default_max_consecutive_losses'),
            'max_open_positions' => (int) $this->ruleset->get('risk.default_max_open_positions'),
            'max_open_risk_pct' => (string) $this->ruleset->get('risk.default_max_open_risk_pct'),
            'min_rr' => null,
        ];
        $p = DB::table('risk_profiles')->where('user_id', $user->getKey())->where('is_current', true)->first();
        if ($p === null) {
            return $defaults;
        }

        // A stored value wins; columns left null (the newer intraday limits) fall back to the ruleset default.
        $stored = [
            'capital' => $p->trading_capital, 'risk_pct' => $p->risk_per_trade_pct,
            'max_position_value' => $p->max_position_value, 'daily_loss_limit_pct' => $p->daily_loss_limit_pct,
            'max_consecutive_losses' => $p->max_consecutive_losses, 'max_open_positions' => $p->max_open_positions,
            'max_open_risk_pct' => $p->max_open_risk_pct, 'min_rr' => $p->min_rr,
        ];
        foreach ($stored as $key => $value) {
            if ($value !== null) {
                $defaults[$key] = in_array($key, ['max_consecutive_losses', 'max_open_positions'], true) ? (int) $value : (string) $value;
            }
        }

        return $defaults;
    }
}
