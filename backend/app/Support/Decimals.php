<?php

namespace App\Support;

/**
 * Decimal strings for the API (ARC-04 §2.6): money and prices as strings with 2 decimals, ratios with up to 4.
 * Strings in, strings out: no floats are involved.
 */
final class Decimals
{
    /** `Price` / `Money`: exactly two decimals (truncated; engine values are tick-aligned). */
    public static function money(?string $value): ?string
    {
        return $value === null ? null : bcadd($value, '0', 2);
    }

    /** `Ratio`: up to four decimals, trailing zeros trimmed. */
    public static function ratio(?string $value): ?string
    {
        if ($value === null) {
            return null;
        }
        $out = bcadd($value, '0', 4);

        return str_contains($out, '.') ? rtrim(rtrim($out, '0'), '.') : $out;
    }

    /** `(a - b) / b x 100` as a `Ratio`, or null when `b` is zero. */
    public static function changePct(string $a, string $b): ?string
    {
        if (bccomp($b, '0', 8) === 0) {
            return null;
        }

        return self::ratio(bcmul(bcdiv(bcsub($a, $b, 8), $b, 8), '100', 8));
    }
}
