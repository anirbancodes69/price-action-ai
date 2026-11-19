<?php

namespace App\Http\Requests\Api\V1;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

/** `POST /actual-trades` (X8): the first BUY fill of a trade. */
class ActualTradeRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /** @return array<string, array<int, mixed>> */
    public function rules(): array
    {
        return [
            'instrument' => ['required', 'string', 'regex:/^[A-Z0-9&_-]{1,32}$/'],
            'trade_plan_id' => ['sometimes', 'uuid'],
            'notes' => ['sometimes', 'string', 'max:2000'],
            'stop' => ['sometimes', 'nullable', 'numeric', 'gt:0', 'max:10000000', 'decimal:0,2', 'lt:fill.price'],
            'target' => ['sometimes', 'nullable', 'numeric', 'gt:0', 'max:10000000', 'decimal:0,2', 'gt:fill.price'],
            'fill' => ['required', 'array:side,quantity,price,executed_at,broker_order_id,fees'],
            'fill.side' => ['required', Rule::in(['BUY'])],
            ...FillRules::rules('fill.'),
        ];
    }
}
