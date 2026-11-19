<?php

namespace App\Services\Trades;

use App\Models\User;
use App\Services\PersonalTenant;
use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * Records the trades the owner placed at the broker (ADR-010: the app never places orders). Every fill is stored and the
 * trade row is recomputed from all its fills in one transaction, so the row can never drift from the fills.
 */
class ActualTradeService
{
    /**
     * @param  array{side: string, quantity: int, price: string, executed_at: string, broker_order_id?: string|null, broker_trade_id?: string|null, fees?: string|null}  $fill
     */
    public function open(User $user, string $instrumentId, ?string $planId, array $fill, ?string $stop = null, ?string $target = null): string
    {
        return DB::transaction(function () use ($user, $instrumentId, $planId, $fill, $stop, $target) {
            $id = (string) Str::uuid7();
            DB::table('actual_trades')->insert([
                'id' => $id, 'tenant_id' => app(PersonalTenant::class)->idFor($user), 'user_id' => $user->getKey(), 'instrument_id' => $instrumentId,
                'trade_plan_id' => $planId, 'direction' => 'LONG', 'status' => 'OPEN', 'quantity_open' => 0, 'source' => 'MANUAL', 'stop_price' => $stop, 'target_price' => $target,
            ]);
            $this->addFill($id, $fill);
            if ($planId !== null) { // the plan has been acted on
                DB::table('trade_plans')->where('id', $planId)->whereIn('status', ['PENDING', 'TRIGGERED'])
                    ->update(['status' => 'FILLED', 'status_reason' => 'TRADE_LOGGED', 'lock_version' => DB::raw('lock_version + 1'), 'updated_at' => CarbonImmutable::now()]);
            }

            return $id;
        });
    }

    /**
     * @param  array{side: string, quantity: int, price: string, executed_at: string, broker_order_id?: string|null, broker_trade_id?: string|null, fees?: string|null}  $fill
     */
    public function addFill(string $tradeId, array $fill): void
    {
        DB::transaction(function () use ($tradeId, $fill) {
            DB::table('actual_trades')->where('id', $tradeId)->lockForUpdate()->first(['id']);
            DB::table('actual_trade_fills')->insert([
                'id' => (string) Str::uuid7(), 'actual_trade_id' => $tradeId, 'side' => $fill['side'], 'quantity' => $fill['quantity'],
                'price' => $fill['price'], 'executed_at' => $fill['executed_at'], 'broker_order_id' => $fill['broker_order_id'] ?? null,
                'broker_trade_id' => $fill['broker_trade_id'] ?? null, 'fees' => $fill['fees'] ?? null,
            ]);
            $this->recompute($tradeId);
        });
    }

    private function recompute(string $tradeId): void
    {
        $rows = DB::table('actual_trade_fills')->where('actual_trade_id', $tradeId)->orderBy('executed_at')->orderBy('created_at')->orderBy('id')->get();
        $fills = $rows->map(fn ($r) => [
            'side' => $r->side, 'quantity' => (int) $r->quantity, 'price' => (string) $r->price, 'fees' => $r->fees === null ? null : (string) $r->fees,
        ])->all();
        $s = FillLedger::summarise($fills); // throws OVERSELL_NOT_ALLOWED, which rolls the transaction back

        $firstBuy = $rows->firstWhere('side', 'BUY');
        $closed = $s['quantity_open'] === 0;
        DB::table('actual_trades')->where('id', $tradeId)->update([
            'status' => $closed ? 'CLOSED' : 'OPEN',
            'quantity_open' => $s['quantity_open'],
            'avg_entry_price' => $s['avg_entry_price'],
            'avg_exit_price' => $s['avg_exit_price'],
            'realized_pnl' => $s['realized_pnl'],
            'charges' => $s['charges'],
            'opened_at' => $firstBuy?->executed_at,
            'closed_at' => $closed ? $rows->last()->executed_at : null,
            'updated_at' => CarbonImmutable::now(),
        ]);
        if ($closed) {
            $this->ensureJournalEntry($tradeId);
        }
    }

    /** Every closed actual trade has one journal entry, created as a draft the first time it closes. */
    private function ensureJournalEntry(string $tradeId): void
    {
        $t = DB::table('actual_trades')->where('id', $tradeId)->first(['tenant_id', 'user_id']);
        DB::table('journal_entries')->insertOrIgnore([
            'id' => (string) Str::uuid7(), 'tenant_id' => $t->tenant_id, 'user_id' => $t->user_id, 'trade_kind' => 'ACTUAL',
            'actual_trade_id' => $tradeId, 'status' => 'DRAFT',
        ]);
    }
}
