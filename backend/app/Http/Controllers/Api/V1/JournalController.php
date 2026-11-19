<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\User;
use App\Services\Scanner\ScannerRowMapper;
use App\Support\ApiException;
use App\Support\ApiResponse;
use App\Support\Cursor;
use App\Support\Decimals;
use Illuminate\Database\Query\Builder;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\Rule;

/**
 * Journal of the owner's closed actual trades (J1-J3). Entries are created as drafts when a trade closes; the owner adds
 * notes, tags and lessons. Trade figures are read from the trade rows, never edited here. The paper book is not built,
 * so its journal is empty. The setup type is the linked plan's (null without a plan); the R-multiple needs a stop (the trade's own, else its plan's).
 */
class JournalController extends Controller
{
    public function index(Request $request): JsonResponse
    {
        $user = $this->user($request);
        $limit = max(1, min(100, (int) $request->query('limit', 25)));
        $offset = Cursor::decode((string) $request->query('cursor', ''));
        $this->validateFilters($request);
        if ($request->query('kind', 'PAPER') === 'PAPER') {
            return ApiResponse::ok([], ['total' => 0, 'next_cursor' => null]);
        }

        $query = $this->base($user);
        if ($request->filled('q')) {
            $like = '%'.str_replace(['\\', '%', '_'], ['\\\\', '\\%', '\\_'], mb_strtolower((string) $request->query('q'))).'%';
            $query->where(fn ($w) => $w->whereRaw('lower(i.trading_symbol) like ?', [$like])->orWhereRaw("lower(coalesce(j.notes, '')) like ?", [$like]));
        }
        if ($request->filled('outcome')) {
            $net = 'coalesce(t.realized_pnl, 0) - coalesce(t.charges, 0)';
            $query->whereRaw(match ($request->query('outcome')) {
                'WIN' => "$net > 0", 'LOSS' => "$net < 0", default => "$net = 0",
            });
        }
        if ($request->filled('followed_plan')) {
            $query->where('j.followed_plan', filter_var($request->query('followed_plan'), FILTER_VALIDATE_BOOLEAN));
        }
        if ($request->filled('from')) {
            $query->where('t.closed_at', '>=', (string) $request->query('from'));
        }
        if ($request->filled('to')) {
            $query->where('t.closed_at', '<=', (string) $request->query('to'));
        }

        $total = (clone $query)->count();
        $rows = $query->orderByDesc('t.closed_at')->orderByDesc('j.id')->offset($offset)->limit($limit)->get($this->columns());

        return ApiResponse::ok($rows->map(fn ($r) => $this->entry($r))->all(), [
            'total' => $total, 'next_cursor' => $offset + $limit < $total ? Cursor::encode($offset + $limit) : null,
        ]);
    }

    public function show(string $id, Request $request): JsonResponse
    {
        return ApiResponse::ok($this->entry($this->find($this->user($request), $id)));
    }

    public function update(string $id, Request $request): JsonResponse
    {
        $user = $this->user($request);
        $this->find($user, $id);
        $v = $request->validate([
            'notes' => ['sometimes', 'nullable', 'string', 'max:10000'],
            'tags' => ['sometimes', 'array', 'max:20'], 'tags.*' => ['string', 'max:40'],
            'emotions' => ['sometimes', 'array', 'max:20'], 'emotions.*' => ['string', 'max:40'],
            'mistakes' => ['sometimes', 'array', 'max:20'], 'mistakes.*' => ['string', 'max:40'],
            'lessons' => ['sometimes', 'nullable', 'string', 'max:10000'],
            'rating' => ['sometimes', 'nullable', 'integer', 'between:1,5'],
            'followed_plan' => ['sometimes', 'nullable', 'boolean'],
            'status' => ['sometimes', Rule::in(['DRAFT', 'COMPLETE'])],
        ]);

        $set = [];
        foreach (['notes', 'lessons', 'rating', 'followed_plan', 'status'] as $f) {
            if (array_key_exists($f, $v)) {
                $set[$f] = $v[$f];
            }
        }
        foreach (['tags', 'emotions', 'mistakes'] as $f) {
            if (array_key_exists($f, $v)) {
                $set[$f] = DB::raw("'".str_replace("'", "''", $this->pgArray($v[$f]))."'::text[]");
            }
        }
        if ($set !== []) {
            DB::table('journal_entries')->where('id', $id)->update($set + ['updated_at' => now()]);
        }

        return ApiResponse::ok($this->entry($this->find($user, $id)));
    }

    private function user(Request $request): User
    {
        /** @var User $user */
        $user = $request->user();

        return $user;
    }

    private function validateFilters(Request $request): void
    {
        $request->validate([
            'kind' => ['sometimes', Rule::in(['PAPER', 'ACTUAL'])], 'outcome' => ['sometimes', Rule::in(['WIN', 'LOSS', 'BREAKEVEN'])],
            'q' => ['sometimes', 'string', 'max:64'], 'followed_plan' => ['sometimes', 'boolean'],
            'from' => ['sometimes', 'date'], 'to' => ['sometimes', 'date'],
        ]);
    }

    private function base(User $user): Builder
    {
        return DB::table('journal_entries as j')
            ->join('actual_trades as t', 't.id', '=', 'j.actual_trade_id')
            ->join('instruments as i', 'i.id', '=', 't.instrument_id')
            ->leftJoin('trade_plans as p', 'p.id', '=', 't.trade_plan_id')
            ->where('j.user_id', $user->getKey())->where('j.trade_kind', 'ACTUAL');
    }

    /** @return list<mixed> */
    private function columns(): array
    {
        return [
            'j.id', 'j.status', 'j.followed_plan', 'j.followed_plan_system', 'j.notes', 'j.lessons', 'j.rating',
            DB::raw('to_json(j.tags) as tags'), DB::raw('to_json(j.emotions) as emotions'), DB::raw('to_json(j.mistakes) as mistakes'),
            'i.trading_symbol', 't.avg_entry_price', 't.avg_exit_price', 't.realized_pnl', 't.charges', 't.opened_at', 't.closed_at',
            't.stop_price as own_stop', 'p.stop_price', 'p.setup_type',
            DB::raw("(select coalesce(sum(f.quantity), 0) from actual_trade_fills f where f.actual_trade_id = t.id and f.side = 'BUY') as bought"),
        ];
    }

    private function find(User $user, string $id): object
    {
        $row = $this->base($user)->where('j.id', $id)->first($this->columns());
        if ($row === null) {
            throw new ApiException('NOT_FOUND', 'Unknown journal entry.', 404);
        }

        return $row;
    }

    /** @return array<string, mixed> */
    private function entry(object $r): array
    {
        $net = bcsub((string) ($r->realized_pnl ?? '0'), (string) ($r->charges ?? '0'), 8);
        $qty = (int) $r->bought;
        $stop = $r->own_stop ?? $r->stop_price;
        $risk = $stop === null || $r->avg_entry_price === null ? null : bcmul(bcsub((string) $r->avg_entry_price, (string) $stop, 8), (string) $qty, 8);
        $closed = $r->closed_at !== null;

        return [
            'id' => $r->id, 'kind' => 'ACTUAL', 'status' => $r->status,
            'trade' => [
                'symbol' => $r->trading_symbol, 'setup_type' => $r->setup_type, 'direction' => 'LONG',
                'entry_at' => ScannerRowMapper::time((string) $r->opened_at),
                'exit_at' => $closed ? ScannerRowMapper::time((string) $r->closed_at) : null,
                'entry_price' => Decimals::money((string) $r->avg_entry_price),
                'exit_price' => Decimals::money($r->avg_exit_price === null ? null : (string) $r->avg_exit_price),
                'quantity' => $qty,
                'net_pnl' => $closed ? Decimals::money($net) : null,
                'r_multiple' => $closed && $risk !== null && bccomp($risk, '0', 8) > 0 ? Decimals::ratio(bcdiv($net, $risk, 8)) : null,
                'outcome' => ! $closed ? null : (bccomp($net, '0', 8) > 0 ? 'WIN' : (bccomp($net, '0', 8) < 0 ? 'LOSS' : 'BREAKEVEN')),
            ],
            'followed_plan' => $r->followed_plan, 'followed_plan_system' => $r->followed_plan_system, 'notes' => $r->notes,
            'tags' => json_decode((string) $r->tags, true) ?? [], 'emotions' => json_decode((string) $r->emotions, true) ?? [],
            'mistakes' => json_decode((string) $r->mistakes, true) ?? [], 'lessons' => $r->lessons, 'rating' => $r->rating,
        ];
    }

    /** @param  list<string>  $values */
    private function pgArray(array $values): string
    {
        return '{'.implode(',', array_map(fn (string $v) => '"'.str_replace(['\\', '"'], ['\\\\', '\\"'], $v).'"', $values)).'}';
    }
}
