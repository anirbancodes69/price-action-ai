<?php

namespace App\Services\Trades;

use App\Support\ApiException;

/**
 * Position bookkeeping of one actual trade from its fills (running average cost, chronological). This is accounting of
 * what the owner did at the broker, not a trading rule. Fills must be sorted by execution time.
 */
final class FillLedger
{
    /**
     * @param  list<array{side: string, quantity: int, price: string, fees: string|null}>  $fills
     * @return array{quantity_open: int, avg_entry_price: string|null, avg_exit_price: string|null, realized_pnl: string|null, charges: string|null}
     */
    public static function summarise(array $fills): array
    {
        $qty = 0;
        $avg = '0';
        $realised = '0';
        $sold = 0;
        $proceeds = '0';
        $hasSell = false;
        $charges = null;

        foreach ($fills as $f) {
            $price = $f['price'];
            if ($f['side'] === 'BUY') {
                $total = $qty + $f['quantity'];
                $cost = bcadd(bcmul($avg, (string) $qty, 8), bcmul($price, (string) $f['quantity'], 8), 8);
                $avg = bcdiv($cost, (string) $total, 8);
                $qty = $total;
            } else {
                if ($f['quantity'] > $qty) {
                    throw new ApiException('OVERSELL_NOT_ALLOWED', 'The sell quantity is larger than the open quantity.', 422);
                }
                $realised = bcadd($realised, bcmul(bcsub($price, $avg, 8), (string) $f['quantity'], 8), 8);
                $qty -= $f['quantity'];
                $sold += $f['quantity'];
                $proceeds = bcadd($proceeds, bcmul($price, (string) $f['quantity'], 8), 8);
                $hasSell = true;
            }
            if ($f['fees'] !== null) {
                $charges = bcadd($charges ?? '0', $f['fees'], 8);
            }
        }

        return [
            'quantity_open' => $qty,
            'avg_entry_price' => $avg === '0' ? null : bcadd($avg, '0', 4),
            'avg_exit_price' => $sold > 0 ? bcadd(bcdiv($proceeds, (string) $sold, 8), '0', 4) : null,
            'realized_pnl' => $hasSell ? bcadd($realised, '0', 2) : null,
            'charges' => $charges === null ? null : bcadd($charges, '0', 2),
        ];
    }
}
