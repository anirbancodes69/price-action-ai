<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\V1\ScannerRequest;
use App\Services\DataSourceResolver;
use App\Services\Engine\EngineClient;
use App\Services\Scanner\ScannerRowMapper;
use App\Support\ApiException;
use App\Support\ApiResponse;
use Carbon\CarbonImmutable;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;

/**
 * `GET /api/v1/scanner`, served live from the engine (ADR-016): one scan of the universe per request.
 */
class ScannerController extends Controller
{
    public function index(ScannerRequest $request, EngineClient $engine, DataSourceResolver $sources): JsonResponse
    {
        $scan = $engine->scan([
            'data_source_id' => $sources->id(),
            'universe_code' => $request->input('universe', 'NIFTY50'),
            'account' => ['capital' => (string) config('trading.capital')],
            'include_no_trade' => true,
        ]);

        $rows = $scan['rows'] ?? [];
        $instruments = $this->instruments(array_column($rows, 'symbol'));
        $mapped = [];
        foreach ($rows as $row) {
            if (isset($instruments[$row['symbol']])) {
                $mapped[] = ScannerRowMapper::map($row, $instruments[$row['symbol']]);
            }
        }

        $filtered = array_values(array_filter($mapped, fn (array $r) => $this->matches($r, $request)));
        $sorted = $this->sort($filtered, (string) $request->input('sort', ''));

        $limit = (int) $request->input('limit', 25);
        $offset = $this->offset((string) $request->input('cursor', ''));
        $page = array_slice($sorted, $offset, $limit);
        $next = $offset + $limit < count($sorted) ? $this->cursor($offset + $limit) : null;

        $asOf = $this->latest(array_column($mapped, 'as_of'));

        return ApiResponse::ok($page, [
            'data_mode' => $scan['data_mode'] ?? null,
            'as_of' => $asOf,
            'next_bar_close' => $asOf === null ? null : CarbonImmutable::parse($asOf)->addMinutes(5)->format('Y-m-d\TH:i:sP'),
            'next_cursor' => $next,
            'total' => count($sorted),
            'ruleset' => $scan['ruleset_version'] ?? null,
            'notice' => $scan['notice'] ?? null,
        ]);
    }

    /**
     * @param  list<string>  $symbols
     * @return array<string, array<string, mixed>>
     */
    private function instruments(array $symbols): array
    {
        if ($symbols === []) {
            return [];
        }
        $rows = DB::table('instruments as i')
            ->leftJoin('instrument_snapshots as s', fn ($j) => $j->on('s.instrument_id', '=', 'i.id')->whereNull('s.effective_to'))
            ->where('i.exchange', 'NSE')->where('i.status', 'ACTIVE')->whereIn('i.trading_symbol', $symbols)
            ->get(['i.id', 'i.trading_symbol', 'i.name', 'i.exchange', 'i.segment', 'i.isin', 'i.status', 's.tick_size', 's.lot_size']);

        $out = [];
        foreach ($rows as $r) {
            $out[$r->trading_symbol] = [
                'id' => $r->id, 'symbol' => $r->trading_symbol, 'name' => $r->name, 'exchange' => $r->exchange,
                'segment' => $r->segment, 'sector' => null, 'isin' => $r->isin, 'status' => $r->status,
                'tick_size' => $r->tick_size === null ? '0.05' : (string) $r->tick_size,
                'lot_size' => (int) ($r->lot_size ?? 1),
            ];
        }

        return $out;
    }

    /** @param  array<string, mixed>  $r */
    private function matches(array $r, ScannerRequest $q): bool
    {
        $setup = $r['primary_setup'];
        $checks = [
            fn () => ! $q->filled('q') || str_contains(mb_strtolower($r['instrument']['symbol'].' '.$r['instrument']['name']), mb_strtolower((string) $q->input('q'))),
            fn () => ! $q->filled('htf_state') || $r['htf_state'] === $q->input('htf_state'),
            fn () => ! $q->filled('structure') || $r['structure_state'] === $q->input('structure'),
            fn () => ! $q->filled('signal') || $r['signal_state'] === $q->input('signal'),
            fn () => ! $q->filled('setup_type') || ($setup['type'] ?? null) === $q->input('setup_type'),
            fn () => ! $q->filled('setup_status') || ($setup['status'] ?? null) === $q->input('setup_status'),
            fn () => ! $q->filled('direction') || ($setup['direction'] ?? null) === $q->input('direction'),
            fn () => ! $q->filled('min_score') || ($setup !== null && $setup['quality_score'] >= (int) $q->input('min_score')),
            fn () => ! $q->filled('min_rr') || (($setup['levels'] ?? null) !== null && bccomp($setup['levels']['rr'], (string) $q->input('min_rr'), 4) >= 0),
        ];
        foreach ($checks as $check) {
            if (! $check()) {
                return false;
            }
        }

        return true;
    }

    /**
     * @param  list<array<string, mixed>>  $rows
     * @return list<array<string, mixed>>
     */
    private function sort(array $rows, string $sort): array
    {
        if ($sort === '') {
            return $rows; // the engine already orders: confirmed entries, watches, then the rest by score
        }
        $desc = str_starts_with($sort, '-');
        $field = ltrim($sort, '-');
        $key = fn (array $r) => match ($field) {
            'symbol' => $r['instrument']['symbol'],
            'quality_score' => $r['primary_setup']['quality_score'] ?? -1,
            'signal_at' => $r['signal_at'] ?? '',
            'change_pct' => (float) ($r['change_pct'] ?? '-1000000'),
            default => 0,
        };
        usort($rows, fn (array $a, array $b) => $desc ? $key($b) <=> $key($a) : $key($a) <=> $key($b));

        return $rows;
    }

    private function cursor(int $offset): string
    {
        return rtrim(strtr(base64_encode((string) json_encode(['o' => $offset])), '+/', '-_'), '=');
    }

    private function offset(string $cursor): int
    {
        if ($cursor === '') {
            return 0;
        }
        $decoded = json_decode((string) base64_decode(strtr($cursor, '-_', '+/'), true), true);
        if (! is_array($decoded) || ! isset($decoded['o']) || ! is_int($decoded['o']) || $decoded['o'] < 0) {
            throw new ApiException('INVALID_CURSOR', 'The cursor is not valid.', 400);
        }

        return $decoded['o'];
    }

    /** @param  list<string|null>  $times */
    private function latest(array $times): ?string
    {
        $times = array_filter($times);

        return $times === [] ? null : array_reduce($times, fn (?string $c, string $t) => $c === null || $t > $c ? $t : $c);
    }
}
