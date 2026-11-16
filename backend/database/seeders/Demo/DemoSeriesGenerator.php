<?php

namespace Database\Seeders\Demo;

use DateTimeImmutable;
use DateTimeZone;

/**
 * Port of the candle generator in frontend/src/mocks/demo-series.ts (ENG-05 §3, ARC-03 §12).
 *
 * Builds deterministic daily OHLCV from scripted price-action templates (breakout, pullback, range, breakdown).
 * The output is SAMPLE DATA for demonstrating the product, never market data. The order of every random draw
 * matches the TypeScript source so the series is identical; a parity test compares against a fixture exported from it.
 * Zones, marks and refs from the TypeScript templates are overlay concerns and are not ported.
 */
final class DemoSeriesGenerator
{
    private const NOISE_AMP = 0.0055;

    private const WICK_AMP = 0.0065;

    /**
     * @return array{segments: list<array{0: int, 1: float, 2?: float}>}
     */
    private static function template(string $name, DemoRandom $rnd): array
    {
        return match ($name) {
            'breakout' => self::breakout($rnd),
            'pullback' => self::pullback($rnd),
            'range' => self::range($rnd),
            'breakdown' => self::breakdown($rnd),
        };
    }

    /** Segments are [bars, end ratio, volume multiplier?]. */
    private static function breakout(DemoRandom $rnd): array
    {
        $finish = 1.058 + $rnd->next() * 0.035;

        return ['segments' => [
            [25, 0.92], [12, 0.96], [15, 0.88], [14, 0.97, 1.2], [10, 0.93, 0.8], [16, 1.04, 1.1], [12, 0.99, 0.8],
            [14, 1.045], [12, 1.0, 0.75], [10, 1.04], [8, 1.1, 2.1], [8, 1.052, 0.7], [6, $finish, 1.1],
        ]];
    }

    private static function pullback(DemoRandom $rnd): array
    {
        $finish = 1.093 + $rnd->next() * 0.022;

        return ['segments' => [
            [20, 0.93], [16, 1.03, 1.2], [10, 0.99, 0.8], [16, 1.09, 1.3], [12, 1.045, 0.8], [16, 1.155, 1.2],
            [12, $finish, 0.7],
        ]];
    }

    private static function range(DemoRandom $rnd): array
    {
        $finish = 0.985 + $rnd->next() * 0.04;

        return ['segments' => [
            [24, 1.05, 1.2], [12, 0.955], [12, 1.045], [11, 0.96], [12, 1.05], [12, 0.952], [13, 1.043], [11, 0.962],
            [12, 1.048], [10, $finish, 0.8],
        ]];
    }

    /** Mirror image of the breakout template. */
    private static function breakdown(DemoRandom $rnd): array
    {
        $base = self::breakout($rnd);
        $segments = [];
        foreach ($base['segments'] as $s) {
            $s[1] = 2 - $s[1];
            $segments[] = $s;
        }

        return ['segments' => $segments];
    }

    /** Trading days (Mon–Fri) ending at $end, oldest first. Holidays are ignored in sample data. */
    public static function tradingDays(int $count, string $end = DemoUniverse::AS_OF): array
    {
        $out = [];
        $d = new DateTimeImmutable($end, new DateTimeZone('UTC'));
        while (count($out) < $count) {
            if ((int) $d->format('w') !== 0 && (int) $d->format('w') !== 6) {
                $out[] = $d->format('Y-m-d');
            }
            $d = $d->modify('-1 day');
        }

        return array_reverse($out);
    }

    private static function ease(float $t): float
    {
        return 0.5 * $t + 0.5 * $t * $t * (3 - 2 * $t);
    }

    /**
     * @return list<array{date: string, open: float, high: float, low: float, close: float, volume: int}>
     */
    public static function generate(string $symbol, float $price, int $avgVolume, string $template): array
    {
        $rnd = new DemoRandom(DemoRandom::hashString($symbol));
        $spec = self::template($template, $rnd);

        // Lead-in drift so every series has SERIES_LENGTH bars.
        $templBars = array_sum(array_column($spec['segments'], 0));
        $leadBars = max(0, DemoUniverse::SERIES_LENGTH - $templBars);
        $leadStart = 1 + ($rnd->next() - 0.4) * 0.12;
        $leadSegs = [];
        $remaining = $leadBars;
        $lvl = $leadStart;
        while ($remaining > 0) {
            $bars = min($remaining, 14 + (int) floor($rnd->next() * 10));
            $next = $remaining - $bars <= 0 ? 1.0 : $lvl * (1 + ($rnd->next() - 0.5) * 0.09);
            $leadSegs[] = [$bars, $next, 0.9];
            $lvl = $next;
            $remaining -= $bars;
        }
        $allSegs = array_merge($leadSegs, $spec['segments']);

        $raw = [];
        $from = $leadStart;
        $prevClose = $leadStart;
        foreach ($allSegs as $seg) {
            [$segBars, $to] = $seg;
            $volMult = $seg[2] ?? 1;
            for ($i = 1; $i <= $segBars; $i++) {
                $t = $i / $segBars;
                $target = $from + ($to - $from) * self::ease($t);
                $close = $target * (1 + ($rnd->next() - 0.5) * 2 * self::NOISE_AMP);
                $open = $prevClose * (1 + ($rnd->next() - 0.5) * 0.006);
                $high = max($open, $close) * (1 + $rnd->next() * self::WICK_AMP);
                $low = min($open, $close) * (1 - $rnd->next() * self::WICK_AMP);
                $volume = $avgVolume * (0.65 + $rnd->next() * 0.7) * $volMult;
                $raw[] = [$open, $high, $low, $close, $volume];
                $prevClose = $close;
            }
            $from = $to;
        }

        $scale = $price / $raw[count($raw) - 1][3];
        $days = self::tradingDays(count($raw));
        $candles = [];
        foreach ($raw as $i => [$open, $high, $low, $close, $volume]) {
            $candles[] = [
                'date' => $days[$i],
                'open' => DemoRandom::toTick($open * $scale),
                'high' => DemoRandom::toTick($high * $scale),
                'low' => DemoRandom::toTick($low * $scale),
                'close' => DemoRandom::toTick($close * $scale),
                'volume' => (int) floor($volume + 0.5),
            ];
        }
        // Pin the final close exactly to the universe price.
        $last = count($candles) - 1;
        $candles[$last]['close'] = $price;
        $candles[$last]['high'] = max($candles[$last]['high'], $price);
        $candles[$last]['low'] = min($candles[$last]['low'], $price);

        return $candles;
    }
}
