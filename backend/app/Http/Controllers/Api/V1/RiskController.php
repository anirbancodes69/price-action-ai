<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Http\Requests\Api\V1\RiskCalculateRequest;
use App\Models\User;
use App\Services\AccountStateService;
use App\Services\Engine\EngineClient;
use App\Services\RiskProfileResolver;
use App\Services\RulesetParameters;
use App\Services\SessionClock;
use App\Support\ApiException;
use App\Support\ApiResponse;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\DB;

/**
 * `POST /api/v1/risk/calculate`: persists nothing. Laravel gathers the inputs (risk profile, the book's account
 * state, tick and lot size, the session clock); the engine sizes the position (RM-01: all risk maths is the engine's).
 */
class RiskController extends Controller
{
    public function calculate(
        RiskCalculateRequest $request,
        EngineClient $engine,
        RiskProfileResolver $profiles,
        AccountStateService $accounts,
        RulesetParameters $ruleset,
        SessionClock $clock,
    ): JsonResponse {
        /** @var User $user */
        $user = $request->user();

        $inst = DB::table('instruments as i')
            ->leftJoin('instrument_snapshots as s', fn ($j) => $j->on('s.instrument_id', '=', 'i.id')->whereNull('s.effective_to'))
            ->where('i.exchange', 'NSE')->where('i.status', 'ACTIVE')->where('i.trading_symbol', $request->string('instrument')->toString())
            ->first(['s.tick_size', 's.lot_size']);
        if ($inst === null) {
            throw new ApiException('NOT_FOUND', 'Unknown instrument.', 404);
        }

        $profile = $profiles->for($user);
        $result = $engine->positionSize([
            'book' => $request->string('book')->toString(),
            'direction' => $request->string('direction')->toString(),
            'capital' => $profile['capital'],
            'risk_pct' => $request->filled('risk_per_trade_pct') ? (string) $request->input('risk_per_trade_pct') : $profile['risk_pct'],
            'entry' => $request->string('entry')->toString(),
            'stop' => $request->string('stop')->toString(),
            'target' => $request->string('target')->toString(),
            'tick_size' => $inst->tick_size === null ? '0.05' : (string) $inst->tick_size,
            'lot_size' => (int) ($inst->lot_size ?? 1),
            'max_position_value' => $profile['max_position_value'],
            'max_open_positions' => $profile['max_open_positions'],
            'max_open_risk_pct' => $profile['max_open_risk_pct'],
            'daily_loss_limit_pct' => $profile['daily_loss_limit_pct'],
            'max_consecutive_losses' => $profile['max_consecutive_losses'],
            'min_rr' => $profile['min_rr'],
            'account_state' => $accounts->forBook($user, $request->string('book')->toString()),
            'as_of_ts' => $clock->lastBarEnd()->format('Y-m-d\TH:i:sP'),
            'entry_cutoff_at' => $clock->entryCutoff()->format('Y-m-d\TH:i:sP'),
            'ruleset_version' => $ruleset->version(),
        ]);

        // Rule violations are 422s carrying the full calculation, so the UI can explain the limits (OpenAPI R1).
        $errors = $result['errors'] ?? [];
        if ($errors !== []) {
            throw new ApiException((string) $errors[0], 'The plan does not pass the risk rules.', 422, [
                'errors' => $errors, 'calculation' => $result,
            ]);
        }

        return ApiResponse::ok($result);
    }
}
