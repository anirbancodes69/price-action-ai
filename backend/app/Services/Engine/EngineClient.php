<?php

namespace App\Services\Engine;

use App\Support\ApiException;
use App\Support\ApiResponse;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Facades\Http;

/**
 * The only way Laravel calls the Python engine (docs/architecture/08_INTEGRATION_ARCHITECTURE.md §5).
 * Bearer service token, request id propagation, timeouts, and a fixed mapping of engine failures to API errors:
 *
 * - network failure, timeout, 5xx, or the engine rejecting our token  → 503 ENGINE_UNAVAILABLE
 * - the engine answering 4xx to a request we built                     → 502 ENGINE_CONTRACT_ERROR
 * - engine `NO_BARS_FOR_SYMBOL` / `DATA_SOURCE_NOT_FOUND`              → 404 with the same code
 * - engine `UNKNOWN_RULESET_VERSION`                                   → 409 (configuration)
 */
class EngineClient
{
    /** @param  array<string, mixed>  $payload @return array<string, mixed> */
    public function scan(array $payload): array
    {
        return $this->post('/internal/v1/scan', $payload, (float) config('services.engine.scan_timeout'));
    }

    /** @param  array<string, mixed>  $payload @return array<string, mixed> */
    public function analysis(array $payload): array
    {
        return $this->post('/internal/v1/analysis', $payload, (float) config('services.engine.scan_timeout'));
    }

    /** @param  array<string, mixed>  $payload @return array<string, mixed> */
    public function positionSize(array $payload): array
    {
        return $this->post('/internal/v1/risk/position-size', $payload, (float) config('services.engine.timeout'));
    }

    /** @param  array<string, mixed>  $payload @return array<string, mixed> */
    public function accountState(array $payload): array
    {
        return $this->post('/internal/v1/risk/account-state', $payload, (float) config('services.engine.timeout'));
    }

    /** @param  array<string, mixed>  $payload @return array<string, mixed> */
    private function post(string $path, array $payload, float $timeout): array
    {
        try {
            $response = Http::timeout($timeout)
                ->withToken((string) config('services.engine.token'))
                ->withHeaders(['X-Request-Id' => ApiResponse::requestId()])
                ->acceptJson()
                ->asJson()
                ->post(rtrim((string) config('services.engine.url'), '/').$path, $payload);
        } catch (ConnectionException $e) {
            report($e);
            throw new ApiException('ENGINE_UNAVAILABLE', 'The analysis engine is not reachable.', 503);
        }

        return $this->decode($response, $path);
    }

    /** @return array<string, mixed> */
    private function decode(Response $response, string $path): array
    {
        if ($response->successful()) {
            $json = $response->json();
            if (! is_array($json)) {
                throw new ApiException('ENGINE_CONTRACT_ERROR', 'The engine returned an unreadable response.', 502);
            }

            return $json;
        }

        $detail = $response->json('detail');
        $code = is_string($detail) ? $detail : null;
        $status = $response->status();
        logger()->warning('engine_request_failed', ['path' => $path, 'status' => $status, 'code' => $code]);

        if ($status === 404 && in_array($code, ['NO_BARS_FOR_SYMBOL', 'DATA_SOURCE_NOT_FOUND'], true)) {
            throw new ApiException($code, $code === 'NO_BARS_FOR_SYMBOL'
                ? 'No stored bars for this symbol yet.' : 'The configured data source does not exist.', 404);
        }
        if ($status === 422 && $code === 'UNKNOWN_RULESET_VERSION') {
            throw new ApiException('RULESET_UNAVAILABLE', 'The configured ruleset version is not available.', 409);
        }
        if ($status >= 500 || $status === 401 || $status === 403 || $status === 503) {
            throw new ApiException('ENGINE_UNAVAILABLE', 'The analysis engine is not available.', 503);
        }

        throw new ApiException('ENGINE_CONTRACT_ERROR', 'The engine rejected the request.', 502);
    }
}
