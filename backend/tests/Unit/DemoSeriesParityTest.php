<?php

namespace Tests\Unit;

use Database\Seeders\Demo\DemoRandom;
use Database\Seeders\Demo\DemoSeriesGenerator;
use Database\Seeders\Demo\DemoUniverse;
use PHPUnit\Framework\TestCase;

/**
 * The demo candle generator must reproduce frontend/src/mocks/demo-series.ts bar for bar, so the seeded DEMO data
 * matches what the Phase 1 UI shows. The fixture holds, per symbol, the bar count, first and last bar and a sha256
 * over all bars; it was exported by running that TypeScript generator (tests/Fixtures/demo-series-parity.json).
 * Regenerate it only if the TypeScript source changes.
 */
class DemoSeriesParityTest extends TestCase
{
    private static function fmt(float|int $v): string
    {
        $s = number_format((float) $v, 2, '.', '');

        return str_contains($s, '.') ? rtrim(rtrim($s, '0'), '.') : $s;
    }

    private static function line(array $c): string
    {
        return implode(',', [$c['date'], self::fmt($c['open']), self::fmt($c['high']), self::fmt($c['low']), self::fmt($c['close']), $c['volume']]);
    }

    private function fixture(): array
    {
        return json_decode((string) file_get_contents(__DIR__.'/../Fixtures/demo-series-parity.json'), true, flags: JSON_THROW_ON_ERROR);
    }

    public function test_imul_matches_javascript_math_imul(): void
    {
        // Expected values computed with Node: Math.imul(0xffffffff, 5) >>> 0 and Math.imul(2166136261 ^ 0x52, 16777619) >>> 0.
        $this->assertSame(0xFFFFFFFB, DemoRandom::imul(0xFFFFFFFF, 5));
        $this->assertSame(3607893173, DemoRandom::imul(2166136261 ^ 0x52, 16777619));
    }

    public function test_every_demo_symbol_matches_the_typescript_generator(): void
    {
        $fixture = $this->fixture();
        $this->assertSame(DemoUniverse::AS_OF, $fixture['as_of']);
        $this->assertSame(DemoUniverse::SERIES_LENGTH, $fixture['series_length']);
        $this->assertCount(count(DemoUniverse::EQUITIES), $fixture['symbols']);

        foreach (DemoUniverse::EQUITIES as [$symbol, , , $price, $avgVolume, $template]) {
            $expected = $fixture['symbols'][$symbol];
            $candles = DemoSeriesGenerator::generate($symbol, $price, $avgVolume, $template);
            $lines = array_map(self::line(...), $candles);

            $this->assertCount($expected['bars'], $candles, $symbol);
            $this->assertSame($expected['first'], $lines[0], "$symbol first bar");
            $this->assertSame($expected['last'], $lines[count($lines) - 1], "$symbol last bar");
            $this->assertSame($expected['sha256'], hash('sha256', implode("\n", $lines)), "$symbol series");
        }
    }

    public function test_series_is_deterministic_and_valid_ohlc(): void
    {
        $a = DemoSeriesGenerator::generate('RELIANCE', 1486.4, 9_800_000, 'breakout');
        $this->assertSame($a, DemoSeriesGenerator::generate('RELIANCE', 1486.4, 9_800_000, 'breakout'));

        foreach ($a as $c) {
            $this->assertGreaterThan(0, $c['low']);
            $this->assertLessThanOrEqual(min($c['open'], $c['close']), $c['low']);
            $this->assertGreaterThanOrEqual(max($c['open'], $c['close']), $c['high']);
            $this->assertGreaterThanOrEqual(0, $c['volume']);
        }
    }
}
