<?php

namespace App\Http\Requests\Api\V1;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

/** `POST /trade-plans` (T2). A client-supplied quantity is not accepted: the engine sizes the plan. */
class TradePlanRequest extends FormRequest
{
    /** Long, actionable types the engine can emit (contracts/strategy-registry.json; `check_strategy_registry.py` keeps them equal). */
    public const SETUP_TYPES = ['OPENING_RANGE_BREAKOUT', 'PREV_DAY_HIGH_BREAK', 'BREAKOUT_RETEST', 'LIQUIDITY_SWEEP_REVERSAL', 'FAILED_BREAKDOWN_RECLAIM'];

    public function authorize(): bool
    {
        return true;
    }

    /** @return array<string, array<int, mixed>> */
    public function rules(): array
    {
        $price = ['sometimes', 'string', 'regex:/^\d{1,9}(\.\d{1,2})?$/'];

        return [
            'instrument' => ['required', 'string', 'regex:/^[A-Z0-9&_-]{1,32}$/'],
            'setup_type' => ['sometimes', Rule::in(self::SETUP_TYPES)],
            'entry' => $price, 'stop' => $price, 'target' => $price,
            // 2% is the technical ceiling (DEC-024), not a recommended risk; the default is 0.5%.
            'risk_per_trade_pct' => ['sometimes', 'nullable', 'numeric', 'gt:0', 'lte:2'],
            'paper_tracking' => ['sometimes', 'boolean'],
            'note' => ['sometimes', 'nullable', 'string', 'max:2000'],
            'quantity' => ['prohibited'],
            'analysis_run_id' => ['prohibited'], // no stored runs in personal mode (ADR-017)
            'setup_id' => ['prohibited'],
        ];
    }
}
