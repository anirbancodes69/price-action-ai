<?php

namespace Database\Seeders\Demo;

use DateTimeImmutable;
use DateTimeZone;

/**
 * SAMPLE DATA. Deterministic 5-minute bars for one session, consistent with that session's daily bar
 * (ADR-015, ENG-05 §12 "Demo data"): the first 5m open equals the daily open, the last 5m close equals the daily
 * close, the session high and low equal the daily high and low, and the 5m volumes sum to the daily volume.
 * 15-minute bars are aggregated from the 5m bars, exactly as the ingestion consistency check expects.
 *
 * The path is a seeded random bridge from open to close, clipped to [low, high]; the bars holding the extremes are
 * pinned to the daily high and low. Volume follows a U-shaped intraday profile. Never market data.
 */
final class DemoIntradayGenerator
{
    /** Bars in a normal NSE session (09:15–15:30). */
    public const BARS_5M = 75;

    private const SESSION_OPEN = '09:15';

    /**
     * @param  array{date: string, open: float, high: float, low: float, close: float, volume: int}  $daily
     * @return list<array{bar_start: string, open: float, high: float, low: float, close: float, volume: int}>
     */
    public static function fiveMinute(string $symbol, array $daily): array
    {
        $rnd = new DemoRandom(DemoRandom::hashString($symbol.'@'.$daily['date']));
        $o = $daily['open'];
        $h = $daily['high'];
        $l = $daily['low'];
        $c = $daily['close'];
        $n = self::BARS_5M;
        $amp = max($h - $l, 0.05) / 3;

        // Random walk, turned into a bridge that starts at 0 and ends at 0.
        $walk = [0.0];
        for ($k = 1; $k <= $n; $k++) {
            $walk[$k] = $walk[$k - 1] + ($rnd->next() - 0.5);
        }
        $scale = 0.0;
        $bridge = [];
        for ($k = 0; $k <= $n; $k++) {
            $bridge[$k] = $walk[$k] - ($k / $n) * $walk[$n];
            $scale = max($scale, abs($bridge[$k]));
        }
        $scale = $scale > 0 ? $scale : 1.0;

        $path = [];
        for ($k = 0; $k <= $n; $k++) {
            $base = $o + ($c - $o) * $k / $n;
            $path[$k] = min($h, max($l, $base + $amp * $bridge[$k] / $scale));
        }
        $path[0] = $o;
        $path[$n] = $c;

        $weights = [];
        for ($k = 1; $k <= $n; $k++) {
            $x = ($k - ($n + 1) / 2) / (($n - 1) / 2);
            $weights[$k] = (1 + 1.5 * $x * $x) * (0.7 + 0.6 * $rnd->next());
        }
        $weightSum = array_sum($weights);

        $start = new DateTimeImmutable($daily['date'].' '.self::SESSION_OPEN, new DateTimeZone('Asia/Kolkata'));
        $bars = [];
        $volumeLeft = $daily['volume'];
        for ($k = 1; $k <= $n; $k++) {
            $open = DemoRandom::toTick($path[$k - 1]);
            $close = DemoRandom::toTick($path[$k]);
            $wick = $amp * 0.15;
            $high = min($h, DemoRandom::toTick(max($open, $close) + $wick * $rnd->next()));
            $low = max($l, DemoRandom::toTick(min($open, $close) - $wick * $rnd->next()));
            $volume = $k === $n ? $volumeLeft : (int) floor($daily['volume'] * $weights[$k] / $weightSum);
            $volumeLeft -= $volume;
            $bars[] = [
                'bar_start' => $start->modify('+'.(5 * ($k - 1)).' minutes')->format(DATE_ATOM),
                'open' => $open,
                'high' => max($high, $open, $close),
                'low' => min($low, $open, $close),
                'close' => $close,
                'volume' => $volume,
            ];
        }
        $bars[0]['open'] = $o;
        $bars[$n - 1]['close'] = $c;

        // Pin the session extremes to the daily bar.
        $hi = 0;
        $lo = 0;
        foreach ($bars as $i => $b) {
            $hi = $b['high'] > $bars[$hi]['high'] ? $i : $hi;
            $lo = $b['low'] < $bars[$lo]['low'] ? $i : $lo;
        }
        $bars[$hi]['high'] = $h;
        $bars[$lo]['low'] = $l;
        foreach ($bars as $i => $b) {
            $bars[$i]['high'] = max($b['high'], $b['open'], $b['close']);
            $bars[$i]['low'] = min($b['low'], $b['open'], $b['close']);
        }

        return $bars;
    }

    /**
     * Aggregate consecutive groups of three 5m bars into 15m bars.
     *
     * @param  list<array{bar_start: string, open: float, high: float, low: float, close: float, volume: int}>  $bars
     * @return list<array{bar_start: string, open: float, high: float, low: float, close: float, volume: int}>
     */
    public static function fifteenMinute(array $bars): array
    {
        $out = [];
        foreach (array_chunk($bars, 3) as $group) {
            $out[] = [
                'bar_start' => $group[0]['bar_start'],
                'open' => $group[0]['open'],
                'high' => max(array_column($group, 'high')),
                'low' => min(array_column($group, 'low')),
                'close' => $group[count($group) - 1]['close'],
                'volume' => array_sum(array_column($group, 'volume')),
            ];
        }

        return $out;
    }

    /** Start of the session for a date, as an ISO-8601 timestamp with the IST offset (daily bars use it). */
    public static function sessionOpen(string $date): string
    {
        return (new DateTimeImmutable($date.' '.self::SESSION_OPEN, new DateTimeZone('Asia/Kolkata')))->format(DATE_ATOM);
    }
}
