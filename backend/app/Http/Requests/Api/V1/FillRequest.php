<?php

namespace App\Http\Requests\Api\V1;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

/** `POST /actual-trades/{id}/fills` (X9). */
class FillRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /** @return array<string, array<int, mixed>> */
    public function rules(): array
    {
        return [
            'side' => ['required', Rule::in(['BUY', 'SELL'])],
            'broker_trade_id' => ['sometimes', 'nullable', 'string', 'max:64'],
            ...FillRules::rules(),
        ];
    }
}
