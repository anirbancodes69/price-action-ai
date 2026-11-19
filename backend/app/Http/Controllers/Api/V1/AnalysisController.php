<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\V1\AnalysisRequest;
use App\Services\Analysis\AnalysisMapper;
use App\Services\DataSourceResolver;
use App\Services\Engine\EngineClient;
use App\Services\InstrumentCatalog;
use App\Services\Scanner\ScannerRowMapper;
use App\Services\SessionClock;
use App\Support\ApiException;
use App\Support\ApiResponse;
use Carbon\CarbonImmutable;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;

/**
 * `GET /api/v1/analysis/{symbol}`, served live from the engine (ADR-016): the analysis at the latest closed 5m bar,
 * or at `as_of`.
 */
class AnalysisController extends Controller
{
    public function show(
        string $symbol,
        AnalysisRequest $request,
        EngineClient $engine,
        DataSourceResolver $sources,
        InstrumentCatalog $catalog,
        SessionClock $clock,
    ): JsonResponse {
        $symbol = strtoupper($symbol);
        $instrument = preg_match('/^[A-Z0-9&_-]{1,32}$/', $symbol) === 1 ? ($catalog->bySymbols([$symbol])[$symbol] ?? null) : null;
        if ($instrument === null) {
            throw new ApiException('NOT_FOUND', 'Unknown instrument.', 404);
        }

        $source = $sources->id();
        $payload = ['data_source_id' => $source, 'symbol' => $symbol];
        if ($request->filled('as_of')) {
            $payload['as_of_ts'] = CarbonImmutable::parse((string) $request->input('as_of'))->utc()->format('Y-m-d\TH:i:s\Z');
        }
        $detail = $engine->analysis($payload);

        $asOf = CarbonImmutable::parse($detail['as_of_ts']);
        $candles = $request->input('include') === 'candles' ? $this->candles($source, $instrument['id'], $detail['session_date'], $asOf) : null;
        $rulesetParts = explode(' ', (string) $detail['ruleset_version'], 2);
        $ruleset = [
            'code' => $rulesetParts[0],
            'version' => $rulesetParts[1] ?? '',
            'validation_status' => (string) (DB::table('ruleset_versions')
                ->where('ruleset_code', $rulesetParts[0])->where('version', $rulesetParts[1] ?? '')->value('validation_status') ?? 'HYPOTHESIS'),
        ];

        $run = AnalysisMapper::map(
            $detail, $instrument, $ruleset,
            ScannerRowMapper::time($clock->entryCutoff($asOf)->toIso8601String()) ?? '',
            ScannerRowMapper::time($clock->sessionEndExit($asOf)->toIso8601String()) ?? '',
            $candles,
        );
        $mapped = $run['as_of'];

        return ApiResponse::ok($run, [
            'data_mode' => $this->dataMode($source),
            'as_of' => $mapped,
            'next_bar_close' => CarbonImmutable::parse($mapped)->addMinutes(5)->format('Y-m-d\TH:i:sP'),
        ]);
    }

    private function dataMode(string $sourceId): ?string
    {
        return DB::table('data_sources')->where('id', $sourceId)->value('mode');
    }

    /** @return list<array<string, mixed>> */
    private function candles(string $source, string $instrumentId, string $sessionDate, CarbonImmutable $asOf): array
    {
        $rows = DB::table('candles')
            ->where('data_source_id', $source)->where('instrument_id', $instrumentId)->where('timeframe', '5m')
            ->where('trade_date', $sessionDate)->where('bar_start', '<', $asOf->utc()->format('Y-m-d H:i:sP'))
            ->orderBy('bar_start')->get(['bar_start', 'open', 'high', 'low', 'close', 'volume']);

        return $rows->map(function ($r) {
            $start = CarbonImmutable::parse($r->bar_start);

            return [
                'start' => ScannerRowMapper::time($start->toIso8601String()),
                'end' => ScannerRowMapper::time($start->addMinutes(5)->toIso8601String()),
                'open' => (string) $r->open, 'high' => (string) $r->high, 'low' => (string) $r->low, 'close' => (string) $r->close,
                'volume' => (int) $r->volume,
            ];
        })->all();
    }
}
