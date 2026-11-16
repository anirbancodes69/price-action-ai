<?php

namespace Database\Seeders;

use Database\Seeders\Demo\DemoIntradayGenerator;
use Database\Seeders\Demo\DemoSeriesGenerator;
use Database\Seeders\Demo\DemoUniverse;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use Ramsey\Uuid\Uuid;

/**
 * Seeds the DEMO data mode (ADR-011, ARC-03 §12): the DEMO data source, demo instruments with provider refs and
 * snapshots, the DEMO universe, completed ingestion runs, generated daily candles and, for the last
 * INTRADAY_SESSIONS sessions, 5m and 15m bars consistent with those daily bars (ADR-015). Everything is SAMPLE DATA,
 * flagged `is_demo`, and is never presented as live. Ids are deterministic (UUIDv5) and inserts ignore conflicts,
 * so the seeder can be re-run safely.
 *
 * Needs the schema-owner role (`make seed`): the runtime roles do not own these tables (ARC-01 §6).
 */
class DemoSeeder extends Seeder
{
    private const NAMESPACE_UUID = '9a7e4c52-0d1b-4b38-a6f5-2c8d3e1b7a90';

    private const EFFECTIVE_FROM = '2000-01-01';

    private const CHUNK = 1000;

    /** Sessions (most recent first) that also get 5m and 15m bars. */
    public const INTRADAY_SESSIONS = 10;

    public static function id(string $key): string
    {
        return Uuid::uuid5(self::NAMESPACE_UUID, $key)->toString();
    }

    public function run(): void
    {
        $this->call([RulesetSeeder::class, UniverseSeeder::class, MarketCalendarSeeder::class]);

        DB::transaction(function (): void {
            $sourceId = self::id('data-source:DEMO');
            $runId = self::id('ingestion-run:DEMO:backfill');
            $runIds = ['5m' => self::id('ingestion-run:DEMO:backfill:5m'), '15m' => self::id('ingestion-run:DEMO:backfill:15m')];
            $intraday = ['5m' => [], '15m' => []];
            $universeId = UniverseSeeder::id('DEMO');

            DB::table('data_sources')->insertOrIgnore([
                'id' => $sourceId, 'mode' => 'DEMO', 'provider' => 'DEMO', 'name' => 'Demo data (sample)', 'status' => 'ACTIVE',
            ]);

            $candles = [];
            foreach (DemoUniverse::EQUITIES as [$symbol, $name, , $price, $avgVolume, $template]) {
                $instrumentId = $this->instrument($symbol, $name, 'EQ', '0.05');
                DB::table('universe_memberships')->insertOrIgnore([
                    'id' => self::id("membership:DEMO:$symbol"), 'universe_id' => $universeId,
                    'instrument_id' => $instrumentId, 'effective_from' => self::EFFECTIVE_FROM,
                    'source_ref' => 'demo-seed',
                ]);
                $daily = DemoSeriesGenerator::generate($symbol, $price, $avgVolume, $template);
                foreach ($daily as $c) {
                    $candles[] = [
                        'data_source_id' => $sourceId, 'instrument_id' => $instrumentId, 'timeframe' => '1D',
                        'bar_start' => DemoIntradayGenerator::sessionOpen($c['date']), 'trade_date' => $c['date'],
                        'open' => $c['open'], 'high' => $c['high'], 'low' => $c['low'],
                        'close' => $c['close'], 'volume' => $c['volume'], 'ingestion_run_id' => $runId,
                    ];
                }
                foreach (array_slice($daily, -self::INTRADAY_SESSIONS) as $day) {
                    $five = DemoIntradayGenerator::fiveMinute($symbol, $day);
                    foreach (['5m' => $five, '15m' => DemoIntradayGenerator::fifteenMinute($five)] as $tf => $bars) {
                        foreach ($bars as $b) {
                            $intraday[$tf][] = [
                                'data_source_id' => $sourceId, 'instrument_id' => $instrumentId, 'timeframe' => $tf,
                                'bar_start' => $b['bar_start'], 'trade_date' => $day['date'],
                                'open' => $b['open'], 'high' => $b['high'], 'low' => $b['low'],
                                'close' => $b['close'], 'volume' => $b['volume'], 'ingestion_run_id' => $runIds[$tf],
                            ];
                        }
                    }
                }
            }
            foreach (DemoUniverse::INDICES as [$symbol, $name]) {
                $this->instrument($symbol, $name, 'INDEX', '0.0100');
            }

            $days = DemoSeriesGenerator::tradingDays(DemoUniverse::SERIES_LENGTH);
            DB::table('ingestion_runs')->insertOrIgnore([
                'id' => $runId, 'data_source_id' => $sourceId, 'kind' => 'BACKFILL', 'timeframe' => '1D', 'status' => 'COMPLETED',
                'range_from' => $days[0], 'range_to' => $days[count($days) - 1],
                'instruments_total' => count(DemoUniverse::EQUITIES), 'instruments_succeeded' => count(DemoUniverse::EQUITIES),
                'rows_inserted' => count($candles), 'started_at' => now(), 'finished_at' => now(),
            ]);

            $intradayDays = array_slice($days, -self::INTRADAY_SESSIONS);
            foreach ($runIds as $tf => $id) {
                DB::table('ingestion_runs')->insertOrIgnore([
                    'id' => $id, 'data_source_id' => $sourceId, 'kind' => 'BACKFILL', 'timeframe' => $tf, 'status' => 'COMPLETED',
                    'range_from' => $intradayDays[0], 'range_to' => $intradayDays[count($intradayDays) - 1],
                    'instruments_total' => count(DemoUniverse::EQUITIES), 'instruments_succeeded' => count(DemoUniverse::EQUITIES),
                    'rows_inserted' => count($intraday[$tf]), 'started_at' => now(), 'finished_at' => now(),
                ]);
            }

            foreach (array_chunk(array_merge($candles, $intraday['5m'], $intraday['15m']), self::CHUNK) as $chunk) {
                DB::table('candles')->insertOrIgnore($chunk);
            }
        });
    }

    private function instrument(string $symbol, string $name, string $segment, string $tickSize): string
    {
        $id = self::id("instrument:$symbol");
        DB::table('instruments')->insertOrIgnore([
            'id' => $id, 'exchange' => 'NSE', 'segment' => $segment, 'trading_symbol' => $symbol, 'name' => $name,
            'status' => 'ACTIVE', 'is_demo' => true,
        ]);
        DB::table('instrument_provider_refs')->insertOrIgnore([
            'id' => self::id("provider-ref:DEMO:$symbol"), 'instrument_id' => $id, 'provider' => 'DEMO',
            'provider_token' => $symbol, 'valid_from' => self::EFFECTIVE_FROM,
        ]);
        DB::table('instrument_snapshots')->insertOrIgnore([
            'instrument_id' => $id, 'effective_from' => self::EFFECTIVE_FROM, 'name' => $name,
            'tick_size' => $tickSize, 'lot_size' => 1, 'status' => 'ACTIVE',
        ]);

        return $id;
    }
}
