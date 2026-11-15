<?php

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Redis;
use Throwable;

/**
 * Liveness and readiness probe (docs/operations/01_DEPLOYMENT_GUIDE.md §5).
 *
 * GET /api/health          → process is up (no dependency checks)
 * GET /api/health?deep=1   → also checks PostgreSQL, Redis and the engine (authenticated ping)
 *
 * Deep checks return booleans only; no hostnames, versions or error messages are exposed.
 */
class HealthController extends Controller
{
    public function __invoke(Request $request): JsonResponse
    {
        if (! $request->boolean('deep')) {
            return response()->json(['status' => 'ok', 'service' => 'backend']);
        }

        $checks = [
            'database' => $this->check(fn () => DB::select('select 1')),
            'redis' => $this->check(fn () => Redis::connection()->ping()),
            'engine' => $this->check(function () {
                Http::timeout(config('services.engine.timeout'))
                    ->withToken((string) config('services.engine.token'))
                    ->get(rtrim((string) config('services.engine.url'), '/').'/internal/v1/ping')
                    ->throw();
            }),
        ];
        $ok = ! in_array(false, $checks, true);

        return response()->json(
            ['status' => $ok ? 'ok' : 'degraded', 'service' => 'backend', 'checks' => $checks],
            $ok ? 200 : 503,
        );
    }

    private function check(callable $probe): bool
    {
        try {
            $probe();

            return true;
        } catch (Throwable $e) {
            report($e);

            return false;
        }
    }
}
