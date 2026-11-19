<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\V1\TradePlanRequest;
use App\Models\User;
use App\Services\Analysis\AnalysisMapper;
use App\Services\DataSourceResolver;
use App\Services\Engine\EngineClient;
use App\Services\InstrumentCatalog;
use App\Services\PersonalTenant;
use App\Services\RiskCalculator;
use App\Services\RiskProfileResolver;
use App\Services\Scanner\ScannerRowMapper;
use App\Services\SessionClock;
use App\Support\ApiException;
use App\Support\ApiResponse;
use App\Support\Cursor;
use App\Support\Decimals;
use Carbon\CarbonImmutable;
use Illuminate\Database\Query\Builder;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * Trade plans (T1-T5), personal mode (ADR-017). A plan is made from the live analysis of one instrument (or by hand with all
 * three levels) and sized by the engine; the plan stores what it was made from. Nothing here places or changes a broker order
 * (ADR-010).
 */
class TradePlanController extends Controller
{
    private const OPEN = ['PENDING', 'TRIGGERED'];

    private const STATUSES = ['PENDING', 'TRIGGERED', 'FILLED', 'SKIPPED', 'INVALIDATED', 'EXPIRED', 'CANCELLED'];

    public function index(Request $request): JsonResponse
    {
        $user = $this->user($request);
        $request->validate(['status' => ['sometimes', 'string'], 'symbol' => ['sometimes', 'string', 'max:32'], 'sort' => ['sometimes', 'in:created_at,-created_at,plan_number,-plan_number']]);
        $statuses = array_filter(explode(',', (string) $request->query('status', '')));
        if (array_diff($statuses, self::STATUSES) !== []) {
            throw new ApiException('VALIDATION_FAILED', 'The status filter is not valid.', 422, ['field_errors' => ['status' => ['Unknown status.']]]);
        }
        $limit = max(1, min(100, (int) $request->query('limit', 25)));
        $offset = Cursor::decode((string) $request->query('cursor', ''));

        $query = $this->base($user);
        if ($statuses !== []) {
            $query->whereIn('p.status', $statuses);
        }
        if ($request->filled('symbol')) {
            $query->where('i.trading_symbol', strtoupper((string) $request->query('symbol')));
        }
        $sort = (string) $request->query('sort', '-created_at');
        $total = (clone $query)->count();
        $ids = $query->orderBy('p.'.ltrim($sort, '-'), str_starts_with($sort, '-') ? 'desc' : 'asc')->orderByDesc('p.id')
            ->offset($offset)->limit($limit)->pluck('p.id')->all();

        $open = $this->base($user)->whereIn('p.status', self::OPEN);
        $openCount = (clone $open)->count();

        return ApiResponse::ok($this->plans($ids), [
            'total' => $total, 'next_cursor' => $offset + $limit < $total ? Cursor::encode($offset + $limit) : null,
            'totals' => [
                'open_count' => $openCount,
                'pending_count' => $this->base($user)->where('p.status', 'PENDING')->count(),
                'planned_risk' => Decimals::money((string) ((clone $open)->sum('p.risk_amount') ?? '0')),
                'avg_rr_open' => $openCount === 0 ? null : Decimals::ratio((string) (clone $open)->avg('p.rr')),
            ],
        ]);
    }

    public function show(string $id, Request $request): JsonResponse
    {
        $this->find($this->user($request), $id);

        return ApiResponse::ok($this->plans([$id])[0] + ['events' => []]);
    }

    public function store(
        TradePlanRequest $request,
        InstrumentCatalog $catalog,
        EngineClient $engine,
        DataSourceResolver $sources,
        SessionClock $clock,
        RiskCalculator $calculator,
        RiskProfileResolver $profiles,
        PersonalTenant $tenants,
    ): JsonResponse {
        $user = $this->user($request);
        $key = ($h = trim((string) $request->header('Idempotency-Key'))) === '' ? null : 'idem:'.$user->getKey().':plan:'.hash('sha256', $h);
        if ($key !== null && ($existing = Cache::get($key)) !== null && $this->owns($user, (string) $existing)) {
            return ApiResponse::ok($this->plans([(string) $existing])[0], [], 201);
        }

        $symbol = (string) $request->input('instrument');
        $instrument = $catalog->bySymbols([$symbol])[$symbol] ?? null;
        if ($instrument === null) {
            throw new ApiException('NOT_FOUND', 'Unknown instrument.', 404);
        }

        $setup = null;
        $context = ['as_of' => null, 'session_date' => null];
        if ($request->filled('setup_type')) {
            [$setup, $context] = $this->actionableSetup($engine, $sources->id(), $symbol, (string) $request->input('setup_type'), $clock);
        } elseif (! ($request->filled('entry') && $request->filled('stop') && $request->filled('target'))) {
            throw new ApiException('VALIDATION_FAILED', 'A manual plan needs entry, stop and target.', 422, ['field_errors' => [
                'entry' => ['Required without a setup.'], 'stop' => ['Required without a setup.'], 'target' => ['Required without a setup.'],
            ]]);
        }

        $engineLevels = $setup === null ? null : ['entry' => $setup['entry'], 'stop' => $setup['stop'], 'target' => $setup['target']];
        $levels = [];
        foreach (['entry', 'stop', 'target'] as $k) {
            $levels[$k] = $request->filled($k) ? (string) $request->input($k) : (string) $engineLevels[$k];
        }

        $calc = $calculator->calculate($user, 'ACTUAL', $symbol, 'LONG', $levels['entry'], $levels['stop'], $levels['target'], $request->filled('risk_per_trade_pct') ? (string) $request->input('risk_per_trade_pct') : null);
        $rounded = $calc['rounding'];
        $overridden = $engineLevels !== null && array_filter(['entry', 'stop', 'target'], fn ($k) => bccomp($rounded[$k], (string) $engineLevels[$k], 2) !== 0) !== [];

        $id = DB::transaction(function () use ($user, $tenants, $profiles, $instrument, $setup, $context, $engineLevels, $rounded, $overridden, $calc, $request, $clock) {
            $tenant = $tenants->idFor($user);
            $id = (string) Str::uuid7();
            DB::table('trade_plans')->insert([
                'id' => $id, 'tenant_id' => $tenant, 'user_id' => $user->getKey(),
                'plan_number' => 1 + (int) DB::table('trade_plans')->where('tenant_id', $tenant)->max('plan_number'),
                'instrument_id' => $instrument['id'], 'analysis_run_id' => null,
                'setup_key' => $setup === null ? null : AnalysisMapper::setupKey($instrument['symbol'], $setup['type'], 'LONG', $context['session_date']),
                'source' => $setup === null ? 'MANUAL' : 'ENGINE', 'direction' => 'LONG', 'status' => 'PENDING',
                'entry_price' => $rounded['entry'], 'stop_price' => $rounded['stop'], 'target_price' => $rounded['target'],
                'engine_entry_price' => $engineLevels['entry'] ?? null, 'engine_stop_price' => $engineLevels['stop'] ?? null,
                'engine_target_price' => $engineLevels['target'] ?? null, 'levels_overridden' => $overridden,
                'quantity' => $calc['quantity'], 'risk_budget' => $calc['risk_budget'], 'risk_amount' => $calc['actual_risk'],
                'position_value' => $calc['position_value'], 'rr' => $calc['rr'], 'binding_constraint' => $calc['binding_constraint'],
                'risk_profile_id' => $profiles->ensureStored($user),
                'ruleset_version_id' => DB::table('ruleset_versions')->where('status', 'ACTIVE')->orderByDesc('activated_at')->value('id'),
                'paper_tracking' => $request->boolean('paper_tracking', true), 'note' => $request->input('note'),
                'valid_until' => $clock->entryCutoff()->toIso8601String(), 'setup_type' => $setup['type'] ?? null, 'paqs' => $setup['paqs'] ?? null,
                'as_of_ts' => $context['as_of'],
            ]);

            return $id;
        });
        if ($key !== null) {
            Cache::put($key, $id, now()->addDay());
        }

        return ApiResponse::ok($this->plans([$id])[0], [], 201);
    }

    public function update(string $id, Request $request, RiskCalculator $calculator): JsonResponse
    {
        $user = $this->user($request);
        $plan = $this->find($user, $id);
        $v = $request->validate([
            'lock_version' => ['required', 'integer', 'min:0'],
            'entry' => ['sometimes', 'string', 'regex:/^\d{1,9}(\.\d{1,2})?$/'], 'stop' => ['sometimes', 'string', 'regex:/^\d{1,9}(\.\d{1,2})?$/'],
            'target' => ['sometimes', 'string', 'regex:/^\d{1,9}(\.\d{1,2})?$/'], 'note' => ['sometimes', 'nullable', 'string', 'max:2000'],
            'paper_tracking' => ['sometimes', 'boolean'],
        ]);
        if ($plan->status !== 'PENDING') {
            throw new ApiException('PLAN_NOT_EDITABLE', 'Only a pending plan can be edited.', 409);
        }
        if ((int) $v['lock_version'] !== (int) $plan->lock_version) {
            throw new ApiException('STALE_VERSION', 'The plan changed since you loaded it. Reload and try again.', 409);
        }

        $set = [];
        foreach (['note', 'paper_tracking'] as $f) {
            if (array_key_exists($f, $v)) {
                $set[$f] = $v[$f];
            }
        }
        if (isset($v['entry']) || isset($v['stop']) || isset($v['target'])) {
            $new = ['entry' => $v['entry'] ?? (string) $plan->entry_price, 'stop' => $v['stop'] ?? (string) $plan->stop_price, 'target' => $v['target'] ?? (string) $plan->target_price];
            $calc = $calculator->calculate($user, 'ACTUAL', $plan->trading_symbol, 'LONG', $new['entry'], $new['stop'], $new['target']);
            $r = $calc['rounding'];
            $overridden = $plan->engine_entry_price !== null && (bccomp($r['entry'], (string) $plan->engine_entry_price, 2) !== 0
                || bccomp($r['stop'], (string) $plan->engine_stop_price, 2) !== 0 || bccomp($r['target'], (string) $plan->engine_target_price, 2) !== 0);
            $set += [
                'entry_price' => $r['entry'], 'stop_price' => $r['stop'], 'target_price' => $r['target'], 'levels_overridden' => $overridden,
                'quantity' => $calc['quantity'], 'risk_budget' => $calc['risk_budget'], 'risk_amount' => $calc['actual_risk'],
                'position_value' => $calc['position_value'], 'rr' => $calc['rr'], 'binding_constraint' => $calc['binding_constraint'],
            ];
        }
        if ($set !== []) {
            $done = DB::table('trade_plans')->where('id', $id)->where('lock_version', $plan->lock_version)->update($set + ['lock_version' => $plan->lock_version + 1, 'updated_at' => now()]);
            if ($done === 0) {
                throw new ApiException('STALE_VERSION', 'The plan changed since you loaded it. Reload and try again.', 409);
            }
        }

        return ApiResponse::ok($this->plans([$id])[0]);
    }

    public function cancel(string $id, Request $request): JsonResponse
    {
        $user = $this->user($request);
        $plan = $this->find($user, $id);
        $v = $request->validate(['reason' => ['sometimes', 'nullable', 'string', 'max:200']]);
        if (! in_array($plan->status, self::OPEN, true)) {
            throw new ApiException('PLAN_NOT_CANCELLABLE', 'Only a pending or triggered plan can be cancelled.', 409);
        }
        DB::table('trade_plans')->where('id', $id)->update([
            'status' => 'CANCELLED', 'status_reason' => ($v['reason'] ?? null) ?: 'CANCELLED_BY_USER', 'lock_version' => $plan->lock_version + 1, 'updated_at' => now(),
        ]);

        return ApiResponse::ok($this->plans([$id])[0]);
    }

    /**
     * The long setup of `$type` from the live analysis, if it can still be planned (TRD-04: a watch or confirmed entry whose
     * entry window is open and that has levels with the minimum R:R).
     *
     * @return array{0: array<string, mixed>, 1: array{as_of: string, session_date: string}}
     */
    private function actionableSetup(EngineClient $engine, string $source, string $symbol, string $type, SessionClock $clock): array
    {
        $detail = $engine->analysis(['data_source_id' => $source, 'symbol' => $symbol]);
        $found = collect($detail['setups'] ?? [])->first(fn (array $s) => $s['type'] === $type && $s['direction'] === 'LONG' && ! $s['informational']);
        if ($found === null) {
            throw new ApiException('SETUP_NOT_ACTIONABLE', 'There is no long setup of that type right now.', 422);
        }
        if (in_array($found['status'], ['INVALIDATED', 'EXPIRED'], true)) {
            throw new ApiException('SETUP_TERMINAL', 'That setup has ended.', 422);
        }
        if (! in_array($found['status'], ['AWAITING_CONFIRMATION', 'ENTRY_CONFIRMED'], true)
            || $found['entry'] === null || $found['stop'] === null || $found['target'] === null || ($found['rr_below_min'] ?? false)) {
            throw new ApiException('SETUP_NOT_ACTIONABLE', 'That setup is not actionable yet.', 422);
        }
        $asOf = CarbonImmutable::parse($detail['as_of_ts']);
        if ($asOf >= $clock->entryCutoff($asOf)) {
            throw new ApiException('ENTRY_WINDOW_ELAPSED', 'The entry window has closed for today.', 422);
        }

        return [$found, ['as_of' => $asOf->utc()->format('Y-m-d\TH:i:s\Z'), 'session_date' => (string) $detail['session_date']]];
    }

    private function user(Request $request): User
    {
        /** @var User $user */
        $user = $request->user();

        return $user;
    }

    private function owns(User $user, string $id): bool
    {
        return DB::table('trade_plans')->where('id', $id)->where('user_id', $user->getKey())->exists();
    }

    private function base(User $user): Builder
    {
        return DB::table('trade_plans as p')->join('instruments as i', 'i.id', '=', 'p.instrument_id')->where('p.user_id', $user->getKey());
    }

    private function find(User $user, string $id): object
    {
        $row = $this->base($user)->where('p.id', $id)->first(['p.*', 'i.trading_symbol']);
        if ($row === null) {
            throw new ApiException('NOT_FOUND', 'Unknown trade plan.', 404);
        }

        return $row;
    }

    /**
     * @param  list<string>  $ids  in the order to return
     * @return list<array<string, mixed>>
     */
    private function plans(array $ids): array
    {
        if ($ids === []) {
            return [];
        }
        $rows = DB::table('trade_plans as p')->join('instruments as i', 'i.id', '=', 'p.instrument_id')
            ->leftJoin('ruleset_versions as r', 'r.id', '=', 'p.ruleset_version_id')
            ->whereIn('p.id', $ids)->get(['p.*', 'i.trading_symbol', 'r.ruleset_code', 'r.version as ruleset_version'])->keyBy('id');
        $instruments = app(InstrumentCatalog::class)->bySymbols($rows->pluck('trading_symbol')->unique()->values()->all());
        $trades = DB::table('actual_trades')->whereIn('trade_plan_id', $ids)->orderBy('created_at')->get(['id', 'trade_plan_id'])->groupBy('trade_plan_id');
        $time = fn ($t) => $t === null ? null : ScannerRowMapper::time((string) $t);

        return array_map(function (string $id) use ($rows, $instruments, $trades, $time) {
            $p = $rows[$id];

            return [
                'id' => $p->id, 'plan_number' => 'TP-'.str_pad((string) $p->plan_number, 4, '0', STR_PAD_LEFT),
                'instrument' => $instruments[$p->trading_symbol] ?? null, 'status' => $p->status, 'status_reason' => $p->status_reason,
                'source' => $p->source, 'direction' => $p->direction,
                'entry' => Decimals::money((string) $p->entry_price), 'stop' => Decimals::money((string) $p->stop_price), 'target' => Decimals::money((string) $p->target_price),
                'engine_levels' => $p->engine_entry_price === null ? null : [
                    'entry' => Decimals::money((string) $p->engine_entry_price), 'stop' => Decimals::money((string) $p->engine_stop_price), 'target' => Decimals::money((string) $p->engine_target_price),
                ],
                'levels_overridden' => (bool) $p->levels_overridden, 'quantity' => (int) $p->quantity,
                'risk_budget' => Decimals::money((string) $p->risk_budget), 'risk_amount' => Decimals::money((string) $p->risk_amount),
                'position_value' => Decimals::money((string) $p->position_value), 'rr' => Decimals::ratio((string) $p->rr),
                'binding_constraint' => $p->binding_constraint, 'paper_tracking' => (bool) $p->paper_tracking, 'note' => $p->note,
                'analysis_run_id' => $p->analysis_run_id, 'setup_id' => null, 'setup_type' => $p->setup_type, 'paqs' => $p->paqs === null ? null : (int) $p->paqs,
                'as_of' => $time($p->as_of_ts), 'ruleset_version' => trim(($p->ruleset_code ?? '').' '.($p->ruleset_version ?? '')),
                'triggered_at' => $time($p->triggered_at), 'valid_until' => $time($p->valid_until),
                'created_at' => $time($p->created_at), 'updated_at' => $time($p->updated_at), 'lock_version' => (int) $p->lock_version,
                'linked' => ['paper_trade_id' => null, 'actual_trade_ids' => ($trades[$id] ?? collect())->pluck('id')->values()->all()],
            ];
        }, $ids);
    }
}
