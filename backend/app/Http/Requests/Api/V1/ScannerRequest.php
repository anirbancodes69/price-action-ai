<?php

namespace App\Http\Requests\Api\V1;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class ScannerRequest extends FormRequest
{
    public const STATES = ['BULLISH', 'BEARISH', 'SIDEWAYS', 'TRANSITION'];

    public const SORTS = ['symbol', 'quality_score', 'signal_at', 'change_pct'];

    public function authorize(): bool
    {
        return true;
    }

    /** @return array<string, array<int, mixed>> */
    public function rules(): array
    {
        return [
            'universe' => ['sometimes', Rule::in(['NIFTY500', 'NIFTY50', 'NIFTY100', 'NIFTY200', 'NIFTYMIDCAP150', 'DEMO'])],
            'q' => ['sometimes', 'string', 'max:32'],
            'htf_state' => ['sometimes', Rule::in(self::STATES)],
            'structure' => ['sometimes', Rule::in(self::STATES)],
            'signal' => ['sometimes', Rule::in(['NO_TRADE', 'BUY_WATCH', 'ENTRY_CONFIRMED'])],
            'setup_type' => ['sometimes', Rule::in([
                'OPENING_RANGE_BREAKOUT', 'PREV_DAY_HIGH_BREAK', 'PREV_DAY_LOW_BREAK', 'BREAKOUT_RETEST',
                'TREND_CONTINUATION', 'LIQUIDITY_SWEEP_REVERSAL',
            ])],
            'setup_status' => ['sometimes', Rule::in([
                'FORMING', 'AWAITING_CONFIRMATION', 'ENTRY_CONFIRMED', 'INVALIDATED', 'EXPIRED',
            ])],
            'direction' => ['sometimes', Rule::in(['LONG', 'SHORT'])],
            'min_rr' => ['sometimes', 'numeric', 'min:0', 'max:100'],
            'min_score' => ['sometimes', 'integer', 'min:0', 'max:100'],
            'sort' => ['sometimes', 'string', 'regex:/^-?('.implode('|', self::SORTS).')$/'],
            'limit' => ['sometimes', 'integer', 'min:1', 'max:100'],
            'cursor' => ['sometimes', 'string', 'max:200'],
            // Accepted by the contract but not available from the live engine (ADR-016): rejected explicitly.
            'near' => ['prohibited'],
            'watchlist' => ['prohibited'],
        ];
    }
}
