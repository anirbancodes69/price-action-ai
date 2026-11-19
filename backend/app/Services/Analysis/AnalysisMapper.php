<?php

namespace App\Services\Analysis;

use App\Services\Scanner\ScannerRowMapper;
use App\Support\Decimals;
use Ramsey\Uuid\Uuid;

/**
 * Engine `AnalysisDetail` -> OpenAPI `AnalysisRun` (ADR-016). Live analysis has no stored run, so `id`, setup, swing, event
 * and zone ids are deterministic UUIDv5 values of their content: the same analysis yields the same ids.
 * Only renaming and formatting happens here; no trading value is computed.
 */
class AnalysisMapper
{
    private const NS = '6f1d1c0e-52a4-4d4e-9d0a-7a3b1d2c9e11';

    private const STATUS_RANK = ['ENTRY_CONFIRMED' => 0, 'AWAITING_CONFIRMATION' => 1, 'FORMING' => 2];

    /**
     * @param  array<string, mixed>  $d  engine `AnalysisDetail`
     * @param  array<string, mixed>  $instrument  `Instrument` schema
     * @param  array{code: string, version: string, validation_status: string}  $ruleset
     * @param  array<string, list<array<string, mixed>>>  $series  requested candle series: `candles` (5m), `candles_15m`, `candles_1d`
     * @return array<string, mixed>
     */
    public static function map(array $d, array $instrument, array $ruleset, string $entryCutoffAt, string $sessionEndExitAt, array $series = []): array
    {
        $symbol = (string) $d['symbol'];
        $asOf = ScannerRowMapper::time($d['as_of_ts']);
        $id = fn (string $kind, string ...$parts) => Uuid::uuid5(self::NS, implode('|', [$symbol, $asOf, $kind, ...$parts]))->toString();
        $sig = $d['signal'] ?? null;
        $state = ScannerRowMapper::signal((string) ($sig['signal'] ?? 'NO_TRADE'));
        $signalAt = ScannerRowMapper::time($sig['signal_at'] ?? null);
        $validUntil = ScannerRowMapper::time($sig['valid_until'] ?? null);

        $setups = [];
        foreach ($d['setups'] as $s) {
            $setups[] = self::setup($s, $symbol, $d['session_date'], $asOf, $entryCutoffAt, $id);
        }
        $primary = self::primary($setups);
        foreach ($setups as $i => $s) {
            if ($primary !== null && $s['id'] === $primary) {
                $setups[$i]['signal_at'] = $signalAt;
                $setups[$i]['valid_until'] = $validUntil;
            }
        }

        $htf = $d['state_15m'] ?? null;
        $out = [
            'id' => $id('run'),
            'instrument' => $instrument,
            'as_of' => $asOf,
            'status' => self::status((string) $d['status']),
            'timeframe' => '5m',
            'ruleset' => $ruleset,
            'engine_version' => (string) config('trading.engine_version', 'live'),
            'inputs' => [],
            'context' => [
                'htf_state' => $htf,
                'htf_transition_direction' => null,
                'session' => self::session($d['levels'] ?? null, $entryCutoffAt, $sessionEndExitAt),
            ],
            'structure' => [
                'state' => $d['state_5m'] ?? 'SIDEWAYS',
                'transition_direction' => $d['transition_direction_5m'] ?? null,
                'protected_low' => Decimals::money($d['protected_low_5m'] ?? null),
                'protected_high' => Decimals::money($d['protected_high_5m'] ?? null),
                'summary_text' => sprintf('5m structure %s; 15m structure %s.', $d['state_5m'] ?? 'unknown', $htf ?? 'unknown'),
            ],
            'signal' => [
                'state' => $state,
                'reason_codes' => array_values($sig['reasons'] ?? $d['no_setup_reasons'] ?? []),
                'signal_at' => $signalAt,
                'valid_until' => $validUntil,
            ],
            'primary_setup_id' => $primary,
            'setups' => $setups,
            'swings' => array_map(fn (array $p) => [
                'id' => $id('swing', $p['bar_start'], $p['kind']),
                'timeframe' => '5m',
                'kind' => $p['kind'],
                'bar_start' => ScannerRowMapper::time($p['bar_start']),
                'price' => Decimals::money($p['price']),
                'label' => $p['label'],
                'confirmed_at' => ScannerRowMapper::time($p['confirmed_at']),
            ], $d['pivots']),
            'events' => array_map(fn (array $e) => [
                'id' => $id('event', $e['break_bar_start'], $e['type']),
                'timeframe' => '5m',
                'type' => $e['type'],
                'direction' => $e['direction'],
                'level' => Decimals::money($e['level']),
                'level_bar_start' => ScannerRowMapper::time($e['level_bar_start']),
                'break_bar_start' => ScannerRowMapper::time($e['break_bar_start']),
                'break_close' => Decimals::money($e['close']),
                'close_inside_buffer' => (bool) $e['close_inside_buffer'],
            ], $d['events']),
            'zones' => self::zones($d['zones'], $d['levels'] ?? null, $id),
            // Equal-level pools carry no first/last bar in live mode, so none are listed (ADR-016).
            'liquidity' => [],
        ];
        $out += $series;

        return $out;
    }

    /** Engine snapshot status (`VALID`, `INSUFFICIENT_HISTORY`, `INVALID_INPUT`) to the API `RunStatus`. */
    private static function status(string $engine): string
    {
        return match ($engine) {
            'VALID' => 'COMPLETED',
            'INSUFFICIENT_HISTORY', 'INVALID_INPUT' => $engine,
            default => 'FAILED',
        };
    }

    /**
     * @param  array<string, mixed>|null  $levels
     * @return array<string, mixed>|null
     */
    private static function session(?array $levels, string $entryCutoffAt, string $sessionEndExitAt): ?array
    {
        if ($levels === null) {
            return null;
        }
        $p = fn (string $k) => Decimals::money($levels[$k] ?? null);

        return [
            'pdh' => $p('pdh'), 'pdl' => $p('pdl'), 'pdc' => $p('pdc'), 'or_high' => $p('or_high'), 'or_low' => $p('or_low'),
            'session_high' => $p('session_high'), 'session_low' => $p('session_low'),
            'entry_cutoff_at' => $entryCutoffAt, 'session_end_exit_at' => $sessionEndExitAt,
        ];
    }

    /**
     * @param  array<string, mixed>  $s
     * @return array<string, mixed>
     */
    private static function setup(array $s, string $symbol, string $sessionDate, ?string $asOf, string $entryCutoffAt, callable $id): array
    {
        $hasLevels = $s['entry'] !== null && $s['stop'] !== null && $s['target'] !== null && $s['rr'] !== null && $s['target_source'] !== null;
        $detected = ScannerRowMapper::time($s['detected_at']);
        $open = in_array($s['status'], ['AWAITING_CONFIRMATION', 'ENTRY_CONFIRMED'], true) && $asOf !== null && $asOf < $entryCutoffAt;

        return [
            'id' => $id('setup', $s['type'], $s['direction'], $detected ?? ''),
            'setup_key' => self::setupKey($symbol, $s['type'], $s['direction'], $sessionDate),
            'type' => $s['type'],
            'direction' => $s['direction'],
            'informational' => (bool) $s['informational'],
            'status' => $s['status'],
            'detected_at' => $detected,
            'signal_at' => null,
            'valid_until' => null,
            'levels' => $hasLevels ? [
                'trigger' => Decimals::money($s['trigger_price']),
                'entry' => Decimals::money($s['entry']),
                'stop' => Decimals::money($s['stop']),
                'target' => Decimals::money($s['target']),
                'rr' => Decimals::ratio($s['rr']),
                'target_source' => $s['target_source'],
            ] : null,
            'rr_below_min' => (bool) ($s['rr_below_min'] ?? false),
            'entry_window_open' => $open,
            'quality' => [
                'score' => (int) ($s['paqs'] ?? 0),
                'version' => (string) ($s['paqs_version'] ?? ''),
                'components' => array_map(fn (array $c) => [
                    'key' => $c['name'], 'label' => $c['name'], 'points' => (int) $c['points'], 'max' => (int) $c['maximum'],
                    'missing' => (bool) $c['missing'], 'reason' => '',
                ], $s['paqs_components']),
            ],
            'evidence' => [],
            'reason_codes' => $s['end_reason'] === null ? [] : [(string) $s['end_reason']],
        ];
    }

    /** Identifies the same setup across runs and in the plans made from it. */
    public static function setupKey(string $symbol, string $type, string $direction, string $sessionDate): string
    {
        return hash('sha256', implode('|', [$symbol, $type, $direction, $sessionDate]));
    }

    /**
     * The setup shown first: confirmed entries, then watches, then forming; LONG before informational SHORT.
     *
     * @param  list<array<string, mixed>>  $setups
     */
    private static function primary(array $setups): ?string
    {
        $live = array_filter($setups, fn (array $s) => isset(self::STATUS_RANK[$s['status']]));
        if ($live === []) {
            return null;
        }
        usort($live, fn (array $a, array $b) => [self::STATUS_RANK[$a['status']], (int) $a['informational']] <=> [self::STATUS_RANK[$b['status']], (int) $b['informational']]);

        return $live[0]['id'];
    }

    /**
     * @param  list<array<string, mixed>>  $zones
     * @param  array<string, mixed>|null  $levels
     * @return list<array<string, mixed>>
     */
    private static function zones(array $zones, ?array $levels, callable $id): array
    {
        $out = [];
        foreach ($zones as $z) {
            if (! in_array($z['role'], ['SUPPORT', 'RESISTANCE'], true)) {
                continue; // INSIDE zones (price within the zone) have no side in the contract
            }
            $out[] = [
                'id' => $id('zone', $z['low'], $z['high']),
                'role' => $z['role'],
                'low' => Decimals::money($z['low']),
                'high' => Decimals::money($z['high']),
                'touches' => (int) $z['touches'],
                'strength_score' => (int) $z['strength'],
                'strength_bucket' => $z['strength_bucket'],
                'status' => $z['status'],
                'role_reversed' => (bool) $z['role_reversed'],
                'formed_at' => ScannerRowMapper::time($z['formed_at']),
                'distance_pct' => null,
            ];
        }

        return $out;
    }
}
