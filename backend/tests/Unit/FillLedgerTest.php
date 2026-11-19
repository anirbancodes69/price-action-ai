<?php

namespace Tests\Unit;

use App\Services\Trades\FillLedger;
use App\Support\ApiException;
use PHPUnit\Framework\TestCase;

/** Expected values are hand-computed (running average cost). */
class FillLedgerTest extends TestCase
{
    private function fill(string $side, int $qty, string $price, ?string $fees = null): array
    {
        return ['side' => $side, 'quantity' => $qty, 'price' => $price, 'fees' => $fees];
    }

    public function test_buys_average_the_cost_and_a_partial_sell_realises_against_it(): void
    {
        $s = FillLedger::summarise([$this->fill('BUY', 10, '100.00', '5.00'), $this->fill('BUY', 10, '110.00'), $this->fill('SELL', 5, '120.00', '4.00')]);

        $this->assertSame(15, $s['quantity_open']);
        $this->assertSame('105.0000', $s['avg_entry_price']); // (10 x 100 + 10 x 110) / 20
        $this->assertSame('120.0000', $s['avg_exit_price']);
        $this->assertSame('75.00', $s['realized_pnl']); // (120 - 105) x 5
        $this->assertSame('9.00', $s['charges']);
    }

    public function test_closing_the_rest_at_a_loss_nets_the_realised_pnl(): void
    {
        $s = FillLedger::summarise([
            $this->fill('BUY', 10, '100.00'), $this->fill('BUY', 10, '110.00'), $this->fill('SELL', 5, '120.00'), $this->fill('SELL', 15, '100.00'),
        ]);

        $this->assertSame(0, $s['quantity_open']);
        $this->assertSame('0.00', $s['realized_pnl']); // 75 + (100 - 105) x 15
        $this->assertSame('105.0000', $s['avg_exit_price']); // (5 x 120 + 15 x 100) / 20
        $this->assertNull($s['charges']);
    }

    public function test_a_buy_only_trade_has_no_realised_pnl_or_exit(): void
    {
        $s = FillLedger::summarise([$this->fill('BUY', 3, '50.50')]);

        $this->assertSame([3, '50.5000', null, null, null], [$s['quantity_open'], $s['avg_entry_price'], $s['avg_exit_price'], $s['realized_pnl'], $s['charges']]);
    }

    public function test_selling_more_than_is_open_is_rejected(): void
    {
        $this->expectException(ApiException::class);
        $this->expectExceptionMessage('larger than the open quantity');

        FillLedger::summarise([$this->fill('BUY', 10, '100.00'), $this->fill('SELL', 11, '101.00')]);
    }
}
