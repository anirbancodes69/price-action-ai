<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\User;
use App\Services\InstrumentCatalog;
use App\Services\PersonalTenant;
use App\Services\Scanner\ScannerRowMapper;
use App\Support\ApiException;
use App\Support\ApiResponse;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * The owner's watchlists (W1-W6). At least one list always exists: the first read creates "My watchlist". A client may
 * supply the id of a list it creates, so a retried request cannot create it twice.
 */
class WatchlistController extends Controller
{
    private const MAX_ITEMS = 200;

    private const DEFAULT_NAME = 'My watchlist';

    public function index(Request $request, PersonalTenant $tenants): JsonResponse
    {
        $user = $this->user($request);
        if (! DB::table('watchlists')->where('user_id', $user->getKey())->exists()) {
            $this->insertList($user, $tenants->idFor($user), self::DEFAULT_NAME, null);
        }

        return ApiResponse::ok($this->lists($user));
    }

    public function store(Request $request, PersonalTenant $tenants): JsonResponse
    {
        $user = $this->user($request);
        $v = $request->validate(['name' => ['required', 'string', 'min:1', 'max:60'], 'id' => ['sometimes', 'uuid']]);
        $name = trim($v['name']);
        $this->assertNameFree($user, $name, null);
        if (isset($v['id']) && DB::table('watchlists')->where('id', $v['id'])->exists()) {
            throw new ApiException('VALIDATION_FAILED', 'This id is already used.', 422, ['field_errors' => ['id' => ['Already used.']]]);
        }
        $id = $this->insertList($user, $tenants->idFor($user), $name, $v['id'] ?? null);

        return ApiResponse::ok($this->list($user, $id), [], 201);
    }

    public function update(string $id, Request $request): JsonResponse
    {
        $user = $this->user($request);
        $this->own($user, $id);
        $v = $request->validate(['name' => ['sometimes', 'string', 'min:1', 'max:60'], 'sort_order' => ['sometimes', 'integer', 'min:0', 'max:32767']]);
        $set = [];
        if (isset($v['name'])) {
            $this->assertNameFree($user, trim($v['name']), $id);
            $set['name'] = trim($v['name']);
        }
        if (isset($v['sort_order'])) {
            $set['sort_order'] = $v['sort_order'];
        }
        if ($set !== []) {
            DB::table('watchlists')->where('id', $id)->update($set + ['updated_at' => now()]);
        }

        return ApiResponse::ok($this->list($user, $id));
    }

    public function destroy(string $id, Request $request): Response
    {
        $user = $this->user($request);
        $this->own($user, $id);
        if (DB::table('watchlists')->where('user_id', $user->getKey())->count() <= 1) {
            throw new ApiException('LAST_WATCHLIST', 'At least one watchlist must remain.', 409);
        }
        DB::table('watchlists')->where('id', $id)->delete();

        return response()->noContent();
    }

    public function addItem(string $id, string $symbol, Request $request, InstrumentCatalog $catalog): JsonResponse
    {
        $user = $this->user($request);
        $this->own($user, $id);
        $symbol = strtoupper($symbol);
        $instrument = $catalog->bySymbols([$symbol])[$symbol] ?? null;
        if ($instrument === null) {
            throw new ApiException('NOT_FOUND', 'Unknown instrument.', 404);
        }
        $items = DB::table('watchlist_items')->where('watchlist_id', $id);
        if (! (clone $items)->where('instrument_id', $instrument['id'])->exists()) {
            if ((clone $items)->count() >= self::MAX_ITEMS) {
                throw new ApiException('WATCHLIST_FULL', 'A watchlist holds at most '.self::MAX_ITEMS.' symbols.', 422);
            }
            DB::table('watchlist_items')->insert([
                'watchlist_id' => $id, 'instrument_id' => $instrument['id'], 'sort_order' => 1 + (int) (clone $items)->max('sort_order'),
            ]);
        }

        return ApiResponse::ok($this->list($user, $id));
    }

    public function removeItem(string $id, string $symbol, Request $request): Response
    {
        $user = $this->user($request);
        $this->own($user, $id);
        DB::table('watchlist_items')->where('watchlist_id', $id)
            ->whereIn('instrument_id', DB::table('instruments')->where('exchange', 'NSE')->where('trading_symbol', strtoupper($symbol))->select('id'))
            ->delete();

        return response()->noContent();
    }

    private function user(Request $request): User
    {
        /** @var User $user */
        $user = $request->user();

        return $user;
    }

    private function own(User $user, string $id): void
    {
        if (! DB::table('watchlists')->where('id', $id)->where('user_id', $user->getKey())->exists()) {
            throw new ApiException('NOT_FOUND', 'Unknown watchlist.', 404);
        }
    }

    private function assertNameFree(User $user, string $name, ?string $exceptId): void
    {
        $q = DB::table('watchlists')->where('user_id', $user->getKey())->whereRaw('lower(name) = ?', [mb_strtolower($name)]);
        if ($exceptId !== null) {
            $q->where('id', '!=', $exceptId);
        }
        if ($q->exists()) {
            throw new ApiException('NAME_TAKEN', 'A watchlist with this name already exists.', 422, ['field_errors' => ['name' => ['Already used.']]]);
        }
    }

    private function insertList(User $user, string $tenantId, string $name, ?string $id): string
    {
        $id ??= (string) Str::uuid7();
        DB::table('watchlists')->insert([
            'id' => $id, 'tenant_id' => $tenantId, 'user_id' => $user->getKey(), 'name' => $name,
            'sort_order' => 1 + (int) DB::table('watchlists')->where('user_id', $user->getKey())->max('sort_order'),
        ]);

        return $id;
    }

    /** @return list<array<string, mixed>> */
    private function lists(User $user): array
    {
        $lists = DB::table('watchlists')->where('user_id', $user->getKey())->orderBy('sort_order')->orderBy('created_at')->get(['id', 'name', 'sort_order']);
        $items = DB::table('watchlist_items as w')->join('instruments as i', 'i.id', '=', 'w.instrument_id')
            ->whereIn('w.watchlist_id', $lists->pluck('id')->all())->orderBy('w.sort_order')->orderBy('w.added_at')
            ->get(['w.watchlist_id', 'i.trading_symbol', 'w.added_at'])->groupBy('watchlist_id');

        return $lists->map(fn ($l) => [
            'id' => $l->id, 'name' => $l->name, 'sort_order' => (int) $l->sort_order,
            'items' => ($items[$l->id] ?? collect())->map(fn ($i) => ['symbol' => $i->trading_symbol, 'added_at' => ScannerRowMapper::time((string) $i->added_at)])->values()->all(),
        ])->values()->all();
    }

    /** @return array<string, mixed> */
    private function list(User $user, string $id): array
    {
        return collect($this->lists($user))->firstWhere('id', $id);
    }
}
