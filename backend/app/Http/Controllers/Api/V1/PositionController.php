<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\User;
use App\Services\DataSourceResolver;
use App\Services\Scanner\ScannerRowMapper;
use App\Support\ApiException;
use App\Support\ApiResponse;
use App\Support\Decimals;
use Carbon\CarbonImmutable;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

/**
 * `GET /api/v1/positions/live` (X11): open actual positions priced at the latest stored 5m close. The price is display
 * only and carries its bar time (`price_at`); it never feeds analysis. Stop and target come from the linked plan, or are
 * null for a trade logged without one. The paper book is not built yet, so it lists nothing.
 */
class PositionController extends Controller
{
    public function live(Request $request, DataSourceResolver $sources): JsonResponse
    {
        $book = $request->query('book');
        if (! in_array($book, ['PAPER', 'ACTUAL'], true)) {
            throw new ApiException('BOOK_REQUIRED', 'Choose a book: PAPER or ACTUAL.', 422, ['field_errors' => ['book' => ['Use PAPER or ACTUAL.']]]);
        }
        $source = $sources->id();
        $meta = ['data_mode' => DB::table('data_sources')->where('id', $source)->value('mode')];
        if ($book === 'PAPER') {
            return ApiResponse::ok([], $meta);
        }

        /** @var User $user */
        $user = $request->user();
        $rows = DB::table('actual_trades as t')
            ->join('instruments as i', 'i.id', '=', 't.instrument_id')
            ->leftJoin('trade_plans as p', 'p.id', '=', 't.trade_plan_id')
            ->where('t.user_id', $user->getKey())->where('t.status', 'OPEN')->where('t.quantity_open', '>', 0)
            ->orderBy('t.opened_at')
            ->get(['t.id', 't.instrument_id', 'i.trading_symbol', 't.quantity_open', 't.avg_entry_price', 't.opened_at', 'p.stop_price', 'p.target_price']);

        $out = [];
        foreach ($rows as $r) {
            $bar = DB::table('candles')->where('data_source_id', $source)->where('instrument_id', $r->instrument_id)->where('timeframe', '5m')
                ->orderByDesc('bar_start')->first(['bar_start', 'close']);
            $price = $bar === null ? null : (string) $bar->close;
            $entry = (string) $r->avg_entry_price;
            $stop = $r->stop_price === null ? null : (string) $r->stop_price;
            $target = $r->target_price === null ? null : (string) $r->target_price;
            $out[] = [
                'position_id' => $r->id,
                'symbol' => $r->trading_symbol,
                'quantity' => (int) $r->quantity_open,
                'entry_price' => Decimals::money($entry),
                'entry_at' => ScannerRowMapper::time((string) $r->opened_at),
                'current_price' => Decimals::money($price),
                'price_at' => $bar === null ? null : ScannerRowMapper::time(CarbonImmutable::parse($bar->bar_start)->addMinutes(5)->toIso8601String()),
                'unrealised_pnl' => $price === null ? null : Decimals::money(bcmul(bcsub($price, $entry, 8), (string) $r->quantity_open, 8)),
                'stop' => Decimals::money($stop),
                'target' => Decimals::money($target),
                'distance_to_stop_pct' => $price === null || $stop === null ? null : Decimals::changePct($stop, $price),
                'distance_to_target_pct' => $price === null || $target === null ? null : Decimals::changePct($target, $price),
                'signal' => null,
            ];
        }

        return ApiResponse::ok($out, $meta);
    }
}
