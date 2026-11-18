<?php

namespace App\Services;

use App\Models\User;
use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;

/**
 * Account state of one book for the current session, derived from the trade tables on demand and never stored
 * (docs/trading/05_RISK_MANAGEMENT_RULES.md §8.1). The engine applies the limits; this only supplies the inputs.
 */
class AccountStateService
{
    public const TZ = 'Asia/Kolkata';

    /**
     * @return array{realised_net_pnl_today: string, open_risk: string, open_cost_basis: string,
     *     open_positions: int, losing_streak: int}
     */
    public function forBook(User $user, string $book, ?CarbonImmutable $now = null): array
    {
        $dayStart = ($now ?? CarbonImmutable::now())->setTimezone(self::TZ)->startOfDay();
        [$closed, $open] = $book === 'PAPER' ? $this->paper($user, $dayStart) : $this->actual($user, $dayStart);

        $pnl = '0';
        $streak = 0;
        foreach ($closed as $net) { // closing order
            $pnl = bcadd($pnl, $net, 8);
            $streak = bccomp($net, '0', 8) < 0 ? $streak + 1 : 0;
        }
        $risk = '0';
        $basis = '0';
        foreach ($open as [$entry, $stop, $qty]) {
            $perShare = bcsub($entry, $stop, 8);
            if (bccomp($perShare, '0', 8) > 0) { // a stop moved above the entry carries no open risk
                $risk = bcadd($risk, bcmul($perShare, (string) $qty, 8), 8);
            }
            $basis = bcadd($basis, bcmul($entry, (string) $qty, 8), 8);
        }

        return [
            'realised_net_pnl_today' => bcadd($pnl, '0', 2), 'open_risk' => bcadd($risk, '0', 2),
            'open_cost_basis' => bcadd($basis, '0', 2), 'open_positions' => count($open), 'losing_streak' => $streak,
        ];
    }

    /** @return array{0: list<string>, 1: list<array{0: string, 1: string, 2: int}>} */
    private function paper(User $user, CarbonImmutable $dayStart): array
    {
        $base = DB::table('paper_trades')->where('user_id', $user->getKey());
        $closed = (clone $base)->where('status', 'CLOSED')
            ->where('exit_at', '>=', $dayStart)->where('exit_at', '<', $dayStart->addDay())
            ->orderBy('exit_at')->pluck('net_pnl')->map(fn ($v) => (string) $v)->all();
        $open = (clone $base)->where('status', 'OPEN')->get(['entry_price', 'current_stop', 'quantity'])
            ->map(fn ($r) => [(string) $r->entry_price, (string) $r->current_stop, (int) $r->quantity])->all();

        return [$closed, $open];
    }

    /** @return array{0: list<string>, 1: list<array{0: string, 1: string, 2: int}>} */
    private function actual(User $user, CarbonImmutable $dayStart): array
    {
        $base = DB::table('actual_trades')->where('actual_trades.user_id', $user->getKey());
        $closed = (clone $base)->where('actual_trades.status', 'CLOSED')
            ->where('closed_at', '>=', $dayStart)->where('closed_at', '<', $dayStart->addDay())
            ->orderBy('closed_at')->get(['realized_pnl', 'charges'])
            ->map(fn ($r) => bcsub((string) $r->realized_pnl, (string) ($r->charges ?? '0'), 8))->all();
        // The stop of an open actual position is the stop of its plan (the trade row has none); without a plan the
        // position contributes cost basis but no open risk.
        $open = (clone $base)->where('actual_trades.status', 'OPEN')->where('quantity_open', '>', 0)
            ->leftJoin('trade_plans', 'trade_plans.id', '=', 'actual_trades.trade_plan_id')
            ->get(['actual_trades.avg_entry_price', 'trade_plans.stop_price', 'actual_trades.quantity_open'])
            ->map(fn ($r) => [(string) $r->avg_entry_price, (string) ($r->stop_price ?? $r->avg_entry_price), (int) $r->quantity_open])->all();

        return [$closed, $open];
    }
}
