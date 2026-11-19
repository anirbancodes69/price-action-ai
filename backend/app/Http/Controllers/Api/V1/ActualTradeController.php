<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\V1\ActualTradeRequest;
use App\Http\Requests\Api\V1\FillRequest;
use App\Models\User;
use App\Services\InstrumentCatalog;
use App\Services\Scanner\ScannerRowMapper;
use App\Services\Trades\ActualTradeService;
use App\Support\ApiException;
use App\Support\ApiResponse;
use App\Support\Cursor;
use App\Support\Decimals;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;

/**
 * Actual trades: what the owner did at the broker, entered by hand (ADR-010). Nothing here places an order.
 * A repeated `Idempotency-Key` returns the trade the first request created.
 */
class ActualTradeController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $user = $this->user($request);
        $limit = max(1, min(100, (int) $request->query('limit', 25)));
        $offset = Cursor::decode((string) $request->query('cursor', ''));
        $status = $request->query('status');
        if ($status !== null && ! in_array($status, ['OPEN', 'CLOSED'], true)) {
            throw new ApiException('VALIDATION_FAILED', 'The status filter is not valid.', 422, ['field_errors' => ['status' => ['Use OPEN or CLOSED.']]]);
        }

        $query = DB::table('actual_trades')->where('user_id', $user->getKey())
            ->when($status !== null, fn ($q) => $q->where('status', $status));
        $total = (clone $query)->count();
        $ids = $query->orderByRaw('opened_at DESC NULLS LAST')->orderByDesc('id')->offset($offset)->limit($limit)->pluck('id')->all();

        return ApiResponse::ok($this->trades($ids), [
            'total' => $total,
            'next_cursor' => $offset + $limit < $total ? Cursor::encode($offset + $limit) : null,
        ]);
    }

    public function store(ActualTradeRequest $request, InstrumentCatalog $catalog, ActualTradeService $service): JsonResponse
    {
        $user = $this->user($request);
        $key = $this->idempotencyKey($request, $user, 'actual-trade');
        if ($key !== null && ($existing = Cache::get($key)) !== null && $this->owns($user, (string) $existing)) {
            return ApiResponse::ok($this->trades([(string) $existing])[0], [], 201);
        }

        $symbol = (string) $request->input('instrument');
        $instrument = $catalog->bySymbols([$symbol])[$symbol] ?? null;
        if ($instrument === null) {
            throw new ApiException('NOT_FOUND', 'Unknown instrument.', 404);
        }
        $planId = $request->input('trade_plan_id');
        $plan = $planId === null ? null : DB::table('trade_plans')->where('id', $planId)->where('user_id', $user->getKey())->first(['instrument_id', 'stop_price', 'target_price']);
        if ($planId !== null && $plan === null) {
            throw new ApiException('NOT_FOUND', 'Unknown trade plan.', 404);
        }
        if ($plan !== null && $plan->instrument_id !== $instrument['id']) {
            throw new ApiException('VALIDATION_FAILED', 'The plan is for another instrument.', 422, ['field_errors' => ['trade_plan_id' => ['Plan is for another symbol.']]]);
        }

        $fill = $this->normaliseFill((array) $request->input('fill'), 'BUY');
        $stop = $this->level($request->input('stop'));
        $target = $this->level($request->input('target'));
        // A trade logged against a plan takes the plan's levels unless the owner gave their own (when still on the right side).
        if ($plan !== null && $stop === null && bccomp((string) $plan->stop_price, $fill['price'], 2) < 0) {
            $stop = $this->level($plan->stop_price);
        }
        if ($plan !== null && $target === null && bccomp((string) $plan->target_price, $fill['price'], 2) > 0) {
            $target = $this->level($plan->target_price);
        }

        $id = $service->open($user, $instrument['id'], $planId, $fill, $stop, $target);
        if ($key !== null) {
            Cache::put($key, $id, now()->addDay());
        }

        return ApiResponse::ok($this->trades([$id])[0], [], 201);
    }

    /** `PATCH /actual-trades/{id}` (X12): move the stop and/or target of an open trade; `null` clears one. */
    public function levels(string $id, Request $request): JsonResponse
    {
        $user = $this->user($request);
        if (! $this->owns($user, $id)) {
            throw new ApiException('NOT_FOUND', 'Unknown trade.', 404);
        }
        $v = $request->validate([
            'stop' => ['sometimes', 'nullable', 'numeric', 'gt:0', 'max:10000000', 'decimal:0,2'],
            'target' => ['sometimes', 'nullable', 'numeric', 'gt:0', 'max:10000000', 'decimal:0,2'],
        ]);
        $set = [];
        foreach (['stop' => 'stop_price', 'target' => 'target_price'] as $field => $column) {
            if (array_key_exists($field, $v)) {
                $set[$column] = $this->level($v[$field]);
            }
        }
        if ($set !== []) {
            DB::table('actual_trades')->where('id', $id)->update($set + ['updated_at' => now()]);
        }

        return ApiResponse::ok($this->trades([$id])[0]);
    }

    private function level(mixed $value): ?string
    {
        return $value === null ? null : bcadd((string) $value, '0', 2);
    }

    public function fill(string $id, FillRequest $request, ActualTradeService $service): JsonResponse
    {
        $user = $this->user($request);
        if (! $this->owns($user, $id)) {
            throw new ApiException('NOT_FOUND', 'Unknown trade.', 404);
        }
        $key = $this->idempotencyKey($request, $user, 'fill:'.$id);
        if ($key !== null && ! Cache::add($key, 1, now()->addDay())) {
            return ApiResponse::ok($this->trades([$id])[0], [], 201); // the same request was already applied
        }

        try {
            $service->addFill($id, $this->normaliseFill($request->validated(), (string) $request->input('side')));
        } catch (\Throwable $e) {
            if ($key !== null) {
                Cache::forget($key); // a failed fill may be retried with the same key
            }
            throw $e;
        }

        return ApiResponse::ok($this->trades([$id])[0], [], 201);
    }

    private function user(Request $request): User
    {
        /** @var User $user */
        $user = $request->user();

        return $user;
    }

    private function owns(User $user, string $tradeId): bool
    {
        return DB::table('actual_trades')->where('id', $tradeId)->where('user_id', $user->getKey())->exists();
    }

    private function idempotencyKey(Request $request, User $user, string $scope): ?string
    {
        $key = trim((string) $request->header('Idempotency-Key'));

        return $key === '' ? null : 'idem:'.$user->getKey().':'.$scope.':'.hash('sha256', $key);
    }

    /**
     * @param  array<string, mixed>  $fill
     * @return array{side: string, quantity: int, price: string, executed_at: string, broker_order_id: string|null, broker_trade_id: string|null, fees: string|null}
     */
    private function normaliseFill(array $fill, string $side): array
    {
        return [
            'side' => $side, 'quantity' => (int) $fill['quantity'], 'price' => bcadd((string) $fill['price'], '0', 2),
            'executed_at' => (string) $fill['executed_at'], 'broker_order_id' => $fill['broker_order_id'] ?? null,
            'broker_trade_id' => $fill['broker_trade_id'] ?? null,
            'fees' => isset($fill['fees']) ? bcadd((string) $fill['fees'], '0', 2) : null,
        ];
    }

    /**
     * @param  list<string>  $ids  in the order to return
     * @return list<array<string, mixed>>
     */
    private function trades(array $ids): array
    {
        if ($ids === []) {
            return [];
        }
        $trades = DB::table('actual_trades')->whereIn('id', $ids)->get()->keyBy('id');
        $fills = DB::table('actual_trade_fills')->whereIn('actual_trade_id', $ids)->orderBy('executed_at')->orderBy('created_at')->get()->groupBy('actual_trade_id');
        $symbols = DB::table('instruments')->whereIn('id', $trades->pluck('instrument_id')->all())->pluck('trading_symbol', 'id');
        $instruments = app(InstrumentCatalog::class)->bySymbols($symbols->values()->all());

        $out = [];
        foreach ($ids as $id) {
            $t = $trades[$id];
            $out[] = [
                'id' => $t->id,
                'instrument' => $instruments[$symbols[$t->instrument_id]] ?? null,
                'trade_plan_id' => $t->trade_plan_id,
                'status' => $t->status,
                'quantity_open' => (int) $t->quantity_open,
                'stop' => Decimals::money($t->stop_price === null ? null : (string) $t->stop_price),
                'target' => Decimals::money($t->target_price === null ? null : (string) $t->target_price),
                'avg_entry_price' => Decimals::money($t->avg_entry_price === null ? null : (string) $t->avg_entry_price),
                'avg_exit_price' => Decimals::money($t->avg_exit_price === null ? null : (string) $t->avg_exit_price),
                'realized_pnl' => Decimals::money($t->realized_pnl === null ? null : (string) $t->realized_pnl),
                'charges' => Decimals::money($t->charges === null ? null : (string) $t->charges),
                'fills' => ($fills[$id] ?? collect())->map(fn ($f) => [
                    'id' => $f->id, 'side' => $f->side, 'quantity' => (int) $f->quantity, 'price' => Decimals::money((string) $f->price),
                    'executed_at' => ScannerRowMapper::time((string) $f->executed_at),
                    'broker_order_id' => $f->broker_order_id, 'broker_trade_id' => $f->broker_trade_id,
                    'fees' => Decimals::money($f->fees === null ? null : (string) $f->fees),
                ])->values()->all(),
            ];
        }

        return $out;
    }
}
