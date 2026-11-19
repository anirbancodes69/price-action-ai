<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\V1\RiskCalculateRequest;
use App\Models\User;
use App\Services\RiskCalculator;
use App\Support\ApiResponse;
use Illuminate\Http\JsonResponse;

/**
 * `POST /api/v1/risk/calculate`: persists nothing. The sizing is {@see RiskCalculator}'s (the engine's, RM-01).
 */
class RiskController extends Controller
{
    public function calculate(RiskCalculateRequest $request, RiskCalculator $calculator): JsonResponse
    {
        /** @var User $user */
        $user = $request->user();

        return ApiResponse::ok($calculator->calculate(
            $user,
            $request->string('book')->toString(),
            $request->string('instrument')->toString(),
            $request->string('direction')->toString(),
            $request->string('entry')->toString(),
            $request->string('stop')->toString(),
            $request->string('target')->toString(),
            $request->filled('risk_per_trade_pct') ? (string) $request->input('risk_per_trade_pct') : null,
        ));
    }
}
