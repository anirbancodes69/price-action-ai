<?php

namespace Database\Seeders;

use Database\Seeders\Demo\DemoSeriesGenerator;
use Database\Seeders\Demo\DemoUniverse;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use Ramsey\Uuid\Uuid;

/**
 * Seeds the DEMO data mode (ADR-011, ARC-03 §12): the DEMO data source, demo instruments with provider refs and
 * snapshots, the DEMO universe, one completed ingestion run and generated daily candles. Everything is SAMPLE DATA,
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

    public static function id(string $key): string
    {
        return Uuid::uuid5(self::NAMESPACE_UUID, $key)->toString();
    }

    public function run(): void
    {
        $this->call([RulesetSeeder::class, UniverseSeeder::class]);

        DB::transaction(function (): void {
            $sourceId = self::id('data-source:DEMO');
            $runId = self::id('ingestion-run:DEMO:backfill');
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
                foreach (DemoSeriesGenerator::generate($symbol, $price, $avgVolume, $template) as $c) {
                    $candles[] = [
                        'data_source_id' => $sourceId, 'instrument_id' => $instrumentId, 'timeframe' => '1D',
                        'trade_date' => $c['date'], 'open' => $c['open'], 'high' => $c['high'], 'low' => $c['low'],
                        'close' => $c['close'], 'volume' => $c['volume'], 'ingestion_run_id' => $runId,
                    ];
                }
            }
            foreach (DemoUniverse::INDICES as [$symbol, $name]) {
                $this->instrument($symbol, $name, 'INDEX', '0.0100');
            }

            $days = DemoSeriesGenerator::tradingDays(DemoUniverse::SERIES_LENGTH);
            DB::table('ingestion_runs')->insertOrIgnore([
                'id' => $runId, 'data_source_id' => $sourceId, 'kind' => 'BACKFILL', 'status' => 'COMPLETED',
                'range_from' => $days[0], 'range_to' => $days[count($days) - 1],
                'instruments_total' => count(DemoUniverse::EQUITIES), 'instruments_succeeded' => count(DemoUniverse::EQUITIES),
                'rows_inserted' => count($candles), 'started_at' => now(), 'finished_at' => now(),
            ]);

            foreach (array_chunk($candles, self::CHUNK) as $chunk) {
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
