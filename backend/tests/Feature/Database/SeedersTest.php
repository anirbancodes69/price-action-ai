<?php

namespace Tests\Feature\Database;

use Database\Seeders\DatabaseSeeder;
use Database\Seeders\Demo\DemoUniverse;
use Database\Seeders\RulesetSeeder;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Tests\TestCase;

/** T-102: reference and DEMO seed data load into the real schema, satisfy its constraints, and are idempotent. */
class SeedersTest extends TestCase
{
    use RefreshDatabase;

    private function counts(): array
    {
        return array_combine($t = [
            'ruleset_versions', 'universes', 'universe_memberships', 'data_sources', 'instruments',
            'instrument_provider_refs', 'instrument_snapshots', 'ingestion_runs', 'candles',
        ], array_map(fn ($table) => DB::table($table)->count(), $t));
    }

    public function test_seeds_ruleset_pa_core_0_1_0_as_active_hypothesis(): void
    {
        $this->seed(DatabaseSeeder::class);

        $row = DB::table('ruleset_versions')->where(['ruleset_code' => 'pa-core', 'version' => '0.1.0'])->sole();
        $parameters = RulesetSeeder::parameters();

        $this->assertSame('ACTIVE', $row->status);
        $this->assertSame('HYPOTHESIS', $row->validation_status);
        $this->assertSame('paqs-0.1.0', $row->score_version);
        $this->assertNotNull($row->activated_at);
        $this->assertSame(hash('sha256', RulesetSeeder::canonicalJson($parameters)), $row->parameters_hash);
        $this->assertEqualsCanonicalizing($parameters, json_decode($row->parameters, true));
        $this->assertCount(29, $parameters, 'TRD-01 §6 registry has 29 keys');
        $this->assertSame(5, $parameters['risk.default_max_open_positions']);
        $this->assertSame(2.0, $parameters['risk.min_rr']);
    }

    public function test_seeds_universes_and_demo_membership(): void
    {
        $this->seed(DatabaseSeeder::class);

        $this->assertEqualsCanonicalizing(
            ['NIFTY500', 'NIFTY50', 'NIFTY100', 'NIFTY200', 'NIFTYMIDCAP150', 'DEMO'],
            DB::table('universes')->pluck('code')->all(),
        );
        $demo = DB::table('universes')->where('code', 'DEMO')->sole();
        $this->assertTrue($demo->is_demo);
        $this->assertSame(count(DemoUniverse::EQUITIES), DB::table('universe_memberships')->where('universe_id', $demo->id)->count());
        $this->assertSame(count(DemoUniverse::EQUITIES), DB::table('universe_memberships')->count(), 'only DEMO has members');
    }

    public function test_seeds_demo_data_source_instruments_and_candles(): void
    {
        $this->seed(DatabaseSeeder::class);

        $source = DB::table('data_sources')->sole();
        $this->assertSame(['DEMO', 'DEMO', null], [$source->mode, $source->provider, $source->tenant_id]);

        $equities = count(DemoUniverse::EQUITIES);
        $this->assertSame($equities, DB::table('instruments')->where(['segment' => 'EQ', 'is_demo' => true])->count());
        $this->assertSame(count(DemoUniverse::INDICES), DB::table('instruments')->where('segment', 'INDEX')->count());
        $this->assertSame(0, DB::table('instruments')->where('is_demo', false)->count());
        $this->assertSame(0, DB::table('instruments')->whereNotNull('isin')->count());

        $this->assertSame($equities * DemoUniverse::SERIES_LENGTH, DB::table('candles')->count());
        $this->assertSame(0, DB::table('candles')->where('data_source_id', '<>', $source->id)->count());
        $this->assertSame(DemoUniverse::AS_OF, DB::table('candles')->max('trade_date'));

        $run = DB::table('ingestion_runs')->sole();
        $this->assertSame(['BACKFILL', 'COMPLETED'], [$run->kind, $run->status]);
        $this->assertSame($equities * DemoUniverse::SERIES_LENGTH, $run->rows_inserted);
        $this->assertSame(0, DB::table('candles')->where('ingestion_run_id', '<>', $run->id)->count());

        // Final close of each series is pinned to the universe price.
        foreach (DemoUniverse::EQUITIES as [$symbol, , , $price]) {
            $close = DB::table('candles')
                ->join('instruments', 'instruments.id', '=', 'candles.instrument_id')
                ->where('trading_symbol', $symbol)->where('trade_date', DemoUniverse::AS_OF)->value('close');
            $this->assertEquals($price, $close, $symbol);
        }
    }

    public function test_seeding_twice_changes_nothing(): void
    {
        $this->seed(DatabaseSeeder::class);
        $first = $this->counts();
        $ruleset = DB::table('ruleset_versions')->first();

        $this->seed(DatabaseSeeder::class);

        $this->assertSame($first, $this->counts());
        $this->assertEquals($ruleset, DB::table('ruleset_versions')->first());
    }
}
