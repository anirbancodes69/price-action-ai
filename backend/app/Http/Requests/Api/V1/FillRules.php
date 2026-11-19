<?php

namespace App\Http\Requests\Api\V1;

/** Shared validation of one fill (X8 `fill`, X9 body). Prices and fees are decimal strings or numbers with at most two decimals. */
final class FillRules
{
    /** @return array<string, array<int, mixed>> */
    public static function rules(string $prefix = ''): array
    {
        return [
            $prefix.'quantity' => ['required', 'integer', 'min:1', 'max:10000000'],
            $prefix.'price' => ['required', 'numeric', 'gt:0', 'max:10000000', 'decimal:0,2'],
            $prefix.'executed_at' => ['required', 'date', 'before_or_equal:+1 minute'],
            $prefix.'broker_order_id' => ['sometimes', 'nullable', 'string', 'max:64'],
            $prefix.'fees' => ['sometimes', 'nullable', 'numeric', 'min:0', 'max:10000000', 'decimal:0,2'],
        ];
    }
}
