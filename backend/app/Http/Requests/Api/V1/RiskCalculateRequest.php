<?php

namespace App\Http\Requests\Api\V1;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class RiskCalculateRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /** @return array<string, array<int, mixed>> */
    public function rules(): array
    {
        $price = ['required', 'string', 'regex:/^\d{1,9}(\.\d{1,2})?$/'];

        return [
            'instrument' => ['required', 'string', 'regex:/^[A-Z0-9&_-]{1,32}$/'],
            'direction' => ['required', Rule::in(['LONG', 'SHORT'])],
            'book' => ['required', Rule::in(['PAPER', 'ACTUAL'])],
            'entry' => $price,
            'stop' => $price,
            'target' => $price,
            // 2% is the technical ceiling (DEC-024), not a recommended risk; the default is 0.5%.
            'risk_per_trade_pct' => ['sometimes', 'nullable', 'numeric', 'gt:0', 'lte:2'],
        ];
    }
}
