<?php

namespace App\Services\Scanner;

use App\Support\Decimals;
use Carbon\CarbonImmutable;

/**
 * Engine scan row -> OpenAPI `ScannerRow` (docs/architecture/04_API_SPECIFICATION.md, ADR-016).
 * The engine's analysis is live, so `analysis_run_id` is null and `volume` is not supplied.
 */
class ScannerRowMapper
{
    public const TZ = 'Asia/Kolkata';

    /**
     * @param  array<string, mixed>  $row  one entry of the engine `ScanResponse.rows`
     * @param  array<string, mixed>  $instrument  `Instrument` schema
     * @return array<string, mixed>
     */
    public static function map(array $row, array $instrument): array
    {
        $lastClose = $row['last_close'] ?? null;
        $prev = $row['prev_day_close'] ?? null;
        $change = ($lastClose !== null && $prev !== null) ? bcsub((string) $lastClose, (string) $prev, 8) : null;

        return [
            'instrument' => $instrument,
            'last_close' => Decimals::money($lastClose),
            'change' => Decimals::money($change),
            'change_pct' => ($lastClose !== null && $prev !== null) ? Decimals::changePct((string) $lastClose, (string) $prev) : null,
            'volume' => null,
            'analysis_run_id' => null,
            'as_of' => self::time($row['last_bar_end']),
            'htf_state' => $row['htf_state'] ?? null,
            'structure_state' => $row['structure_state'] ?? null,
            'signal_state' => self::signal((string) $row['signal']),
            'signal_at' => self::time($row['signal_at'] ?? null),
            'valid_until' => self::time($row['valid_until'] ?? null),
            'primary_setup' => self::primary($row),
        ];
    }

    /** Snapshot statuses (INSUFFICIENT_HISTORY, INVALID_INPUT) are NO_TRADE for the signal vocabulary. */
    public static function signal(string $engineSignal): string
    {
        return in_array($engineSignal, ['BUY_WATCH', 'ENTRY_CONFIRMED'], true) ? $engineSignal : 'NO_TRADE';
    }

    /** ISO-8601 with the +05:30 offset (ARC-04 §2.9). */
    public static function time(?string $iso): ?string
    {
        return $iso === null ? null : CarbonImmutable::parse($iso)->setTimezone(self::TZ)->format('Y-m-d\TH:i:sP');
    }

    /**
     * @param  array<string, mixed>  $row
     * @return array<string, mixed>|null
     */
    private static function primary(array $row): ?array
    {
        if (($row['setup_type'] ?? null) === null) {
            return null;
        }
        $hasLevels = ($row['entry'] ?? null) !== null && ($row['stop'] ?? null) !== null
            && ($row['target'] ?? null) !== null && ($row['rr'] ?? null) !== null && ($row['target_source'] ?? null) !== null;

        return [
            'type' => $row['setup_type'],
            'direction' => $row['direction'] ?? 'LONG',
            'status' => $row['setup_status'],
            'levels' => $hasLevels ? [
                'trigger' => Decimals::money((string) ($row['trigger_price'] ?? $row['entry'])),
                'entry' => Decimals::money((string) $row['entry']),
                'stop' => Decimals::money((string) $row['stop']),
                'target' => Decimals::money((string) $row['target']),
                'rr' => Decimals::ratio((string) $row['rr']),
                'target_source' => $row['target_source'],
            ] : null,
            'quality_score' => (int) ($row['paqs'] ?? 0),
        ];
    }
}
