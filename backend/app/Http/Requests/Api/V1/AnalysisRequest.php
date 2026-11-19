<?php

namespace App\Http\Requests\Api\V1;

use Illuminate\Foundation\Http\FormRequest;

class AnalysisRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /** @return list<string> the requested `include` parts */
    public function includes(): array
    {
        return array_filter(explode(',', (string) $this->input('include', '')));
    }

    /** @return array<string, array<int, mixed>> */
    public function rules(): array
    {
        return [
            'as_of' => ['sometimes', 'date'],
            'include' => ['sometimes', 'string', 'regex:/^(candles|candles_15m|candles_1d)(,(candles|candles_15m|candles_1d))*$/'],
        ];
    }
}
