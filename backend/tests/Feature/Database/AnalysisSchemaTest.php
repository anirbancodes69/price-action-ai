<?php

namespace Tests\Feature\Database;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Tests\TestCase;

/** ARC-03 §7 and §2.2 (ADR-015): immutability and integrity of analysis data, enforced by the database. */
class AnalysisSchemaTest extends TestCase
{
    use AssertsDatabaseRejects;
    use RefreshDatabase;

    private function id(): string
    {
        return (string) Str::uuid7();
    }

    private function hash(string $seed = ''): string
    {
        return hash('sha256', $seed.Str::random(8));
    }

    private function ruleset(array $o = []): string
    {
        $id = $this->id();
        DB::table('ruleset_versions')->insert(array_merge([
            'id' => $id, 'ruleset_code' => 'pa-core', 'version' => '0.1.0', 'parameters' => '{"swing.n":3}',
            'parameters_hash' => $this->hash(), 'score_version' => 'paqs-0.1.0',
        ], $o));

        return $id;
    }

    /** @return array{source: string, instrument: string, snapshot: string, ruleset: string} */
    private function inputs(): array
    {
        $source = $this->id();
        $instrument = $this->id();
        $snapshot = $this->id();
        DB::table('data_sources')->insert(['id' => $source, 'mode' => 'DEMO', 'provider' => 'DEMO', 'name' => 'Demo']);
        DB::table('instruments')->insert([
            'id' => $instrument, 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'T'.substr($instrument, -6),
            'name' => 'Test', 'status' => 'ACTIVE',
        ]);
        DB::table('candle_snapshots')->insert([
            'id' => $snapshot, 'data_source_id' => $source, 'instrument_id' => $instrument, 'timeframe' => '5m',
            'from_date' => '2025-12-29', 'to_date' => '2026-01-05', 'bar_count' => 390, 'price_basis' => 'UNADJUSTED',
            'from_bar_start' => '2025-12-29T09:15:00+05:30', 'to_bar_start' => '2026-01-05T10:25:00+05:30',
            'max_revision' => 1, 'content_hash' => $this->hash('snap'),
        ]);

        return ['source' => $source, 'instrument' => $instrument, 'snapshot' => $snapshot, 'ruleset' => $this->ruleset()];
    }

    private function analysisRun(array $in, array $o = []): string
    {
        $id = $this->id();
        DB::table('analysis_runs')->insert(array_merge([
            'id' => $id, 'data_source_id' => $in['source'], 'instrument_id' => $in['instrument'],
            'ruleset_version_id' => $in['ruleset'],
            'engine_version' => '0.1.0', 'as_of_date' => '2026-01-05', 'as_of_ts' => '2026-01-05T10:30:00+05:30', 'status' => 'COMPLETED',
            'signal_state' => 'NO_TRADE', 'result_hash' => $this->hash('run'),
        ], $o));

        return $id;
    }

    private function detectedSetup(string $run, string $instrument, array $o = []): string
    {
        $id = $this->id();
        DB::table('detected_setups')->insert(array_merge([
            'id' => $id, 'analysis_run_id' => $run, 'instrument_id' => $instrument, 'setup_key' => $this->hash('setup'),
            'setup_type' => 'BREAKOUT_RETEST', 'direction' => 'LONG', 'informational' => false, 'status' => 'FORMING',
            'detected_at_date' => '2026-01-05', 'detected_at_bar_start' => '2026-01-05T10:25:00+05:30',
            'status_changed_date' => '2026-01-05', 'entry_price' => 100, 'stop_price' => 95, 'target_price' => 115, 'paqs_score' => 72,
            'paqs_version' => 'paqs-0.1.0', 'paqs_components' => '{}',
        ], $o));

        return $id;
    }

    public function test_ruleset_version_format_hash_and_uniqueness(): void
    {
        $this->ruleset();

        $this->assertRejected(fn () => $this->ruleset());                                   // same code + version
        $this->assertRejected(fn () => $this->ruleset(['version' => 'v1']));
        $this->assertRejected(fn () => $this->ruleset(['version' => '0.2.0', 'parameters_hash' => 'abc']));
        $this->assertRejected(fn () => $this->ruleset(['version' => '0.3.0', 'status' => 'ACTIVE']));  // ACTIVE needs activated_at
        $this->ruleset(['version' => '0.4.0', 'status' => 'ACTIVE', 'activated_at' => now()]);
    }

    public function test_ruleset_content_is_editable_in_draft_and_frozen_once_active(): void
    {
        $id = $this->ruleset();

        DB::table('ruleset_versions')->where('id', $id)->update(['parameters' => '{"swing.n":4}']);
        $this->assertSame(4, json_decode(DB::table('ruleset_versions')->where('id', $id)->value('parameters'), true)['swing.n']);

        DB::table('ruleset_versions')->where('id', $id)->update(['status' => 'ACTIVE', 'activated_at' => now()]);

        $this->assertRejected(fn () => DB::table('ruleset_versions')->where('id', $id)->update(['parameters' => '{"swing.n":5}']));
        $this->assertRejected(fn () => DB::table('ruleset_versions')->where('id', $id)->update(['parameters_hash' => $this->hash()]));
        $this->assertRejected(fn () => DB::table('ruleset_versions')->where('id', $id)->update(['version' => '9.9.9']));
        $this->assertRejected(fn () => DB::table('ruleset_versions')->where('id', $id)->update(['status' => 'DRAFT']));

        // Lifecycle fields may still change.
        DB::table('ruleset_versions')->where('id', $id)->update(['validation_status' => 'VALIDATED']);
        DB::table('ruleset_versions')->where('id', $id)->update(['status' => 'RETIRED', 'retired_at' => now()]);
        $this->assertSame('RETIRED', DB::table('ruleset_versions')->where('id', $id)->value('status'));
    }

    public function test_candle_snapshots_dedupe_validate_and_are_immutable(): void
    {
        $in = $this->inputs();
        $snapshot = fn (array $o = []) => array_merge([
            'id' => $this->id(), 'data_source_id' => $in['source'], 'instrument_id' => $in['instrument'], 'timeframe' => '15m',
            'from_date' => '2025-12-29', 'to_date' => '2026-01-05', 'bar_count' => 130, 'price_basis' => 'UNADJUSTED',
            'from_bar_start' => '2025-12-29T09:15:00+05:30', 'to_bar_start' => '2026-01-05T10:15:00+05:30',
            'max_revision' => 1, 'content_hash' => $this->hash(),
        ], $o);

        DB::table('candle_snapshots')->insert($snapshot());
        $existingHash = DB::table('candle_snapshots')->where('id', $in['snapshot'])->value('content_hash');

        $this->assertRejected(fn () => DB::table('candle_snapshots')->insert($snapshot(['content_hash' => $existingHash])));
        $this->assertRejected(fn () => DB::table('candle_snapshots')->insert($snapshot(['bar_count' => 0])));
        $this->assertRejected(fn () => DB::table('candle_snapshots')->insert($snapshot(['to_date' => '2024-01-01'])));
        $this->assertRejected(fn () => DB::table('candle_snapshots')->insert($snapshot(['price_basis' => 'RAW'])));
        $this->assertRejected(fn () => DB::table('candle_snapshots')->insert($snapshot(['content_hash' => 'not-a-hash'])));
        $this->assertRejected(fn () => DB::table('candle_snapshots')->insert($snapshot(['timeframe' => '2h'])));
        $this->assertRejected(fn () => DB::table('candle_snapshots')->insert($snapshot(['to_bar_start' => '2025-12-01T09:15:00+05:30'])));
        $this->assertRejected(fn () => DB::table('candle_snapshots')->insert($snapshot(['max_revision' => 0])));
        $this->assertRejected(fn () => DB::table('candle_snapshots')->insert($snapshot(['from_bar_start' => null])));
        DB::table('candle_snapshots')->insert($snapshot(['timeframe' => '1D', 'price_basis' => 'ADJUSTED']));   // daily context

        $this->assertRejected(fn () => DB::table('candle_snapshots')->where('id', $in['snapshot'])->update(['bar_count' => 251]));
    }

    public function test_analysis_run_requires_ruleset_and_time_and_is_idempotent(): void
    {
        $in = $this->inputs();
        $this->analysisRun($in);

        $this->assertRejected(fn () => $this->analysisRun($in));                                             // same bar close + ruleset
        $this->assertRejected(fn () => $this->analysisRun($in, ['ruleset_version_id' => null]));             // C-08
        $this->assertRejected(fn () => $this->analysisRun($in, ['as_of_ts' => null]));
        // as_of_date is the IST session date of as_of_ts.
        $this->assertRejected(fn () => $this->analysisRun($in, ['as_of_ts' => '2026-01-06T10:30:00+05:30']));
        // 2026-01-05 20:00 UTC is already 2026-01-06 in IST: the session date follows IST, not UTC.
        $this->assertRejected(fn () => $this->analysisRun($in, ['as_of_ts' => '2026-01-05T20:00:00+00:00']));
        // A new ruleset version or a later bar close is a different, valid run.
        $this->analysisRun($in, ['ruleset_version_id' => $this->ruleset(['version' => '0.3.0'])]);
        $this->analysisRun($in, ['as_of_ts' => '2026-01-05T10:35:00+05:30']);
        $this->assertSame(3, DB::table('analysis_runs')->count());
    }

    public function test_analysis_run_inputs_link_snapshots_by_role_and_are_immutable(): void
    {
        $in = $this->inputs();
        $run = $this->analysisRun($in);
        $input = fn (array $o = []) => array_merge(['analysis_run_id' => $run, 'role' => 'PRIMARY_5M', 'candle_snapshot_id' => $in['snapshot']], $o);

        DB::table('analysis_run_inputs')->insert($input());
        DB::table('analysis_run_inputs')->insert($input(['role' => 'CONTEXT_15M']));

        $this->assertRejected(fn () => DB::table('analysis_run_inputs')->insert($input()));                           // one snapshot per role
        $this->assertRejected(fn () => DB::table('analysis_run_inputs')->insert($input(['role' => 'WEEKLY'])));
        $this->assertRejected(fn () => DB::table('analysis_run_inputs')->insert($input(['role' => 'DAILY_CONTEXT', 'candle_snapshot_id' => $this->id()])));
        $this->assertRejected(fn () => DB::table('analysis_run_inputs')->where('role', 'PRIMARY_5M')->update(['role' => 'DAILY_CONTEXT']));

        DB::table('analysis_runs')->where('id', $run)->delete();
        $this->assertSame(0, DB::table('analysis_run_inputs')->count());                                             // cascades with the run
    }

    public function test_analysis_run_enums_and_completed_run_needs_result_hash(): void
    {
        $in = $this->inputs();
        $with = fn (array $o) => fn () => $this->analysisRun(array_merge($in, ['ruleset' => $this->ruleset(['version' => '1.'.random_int(0, 99999).'.0'])]), $o);

        $this->assertRejected($with(['status' => 'DONE']));
        $this->assertRejected($with(['signal_state' => 'SELL']));
        $this->assertRejected($with(['structure_state' => 'UPTREND']));
        $this->assertRejected($with(['transition_direction' => 'SIDEWAYS']));
        $this->assertRejected($with(['result_hash' => null]));                                       // COMPLETED without hash
        $this->assertRejected($with(['duration_ms' => -1]));

        // A failed run legitimately has no hash and no structure.
        DB::transaction($with(['status' => 'FAILED', 'result_hash' => null, 'error_code' => 'ENGINE_ERROR']));
        $this->assertSame(1, DB::table('analysis_runs')->count());
    }

    public function test_analysis_runs_are_immutable(): void
    {
        $run = $this->analysisRun($this->inputs());

        $this->assertRejected(fn () => DB::table('analysis_runs')->where('id', $run)->update(['signal_state' => 'BUY_WATCH']));
        $this->assertRejected(fn () => DB::table('analysis_runs')->where('id', $run)->update(['summary' => '{"x":1}']));
    }

    public function test_analysis_batch_scope_is_unique_and_counters_are_consistent(): void
    {
        $in = $this->inputs();
        $universe = $this->id();
        DB::table('universes')->insert(['id' => $universe, 'code' => 'NIFTY500', 'name' => 'NIFTY 500']);
        $batch = fn (array $o = []) => array_merge([
            'id' => $this->id(), 'data_source_id' => $in['source'], 'universe_id' => $universe, 'as_of_date' => '2026-01-05',
            'as_of_ts' => '2026-01-05T10:30:00+05:30', 'ruleset_version_id' => $in['ruleset'], 'trigger' => 'BAR_CLOSE', 'status' => 'QUEUED',
        ], $o);

        DB::table('analysis_batches')->insert($batch());
        DB::table('analysis_batches')->insert($batch(['as_of_ts' => '2026-01-05T10:35:00+05:30']));               // next 5m close

        $this->assertRejected(fn () => DB::table('analysis_batches')->insert($batch()));
        $this->assertRejected(fn () => DB::table('analysis_batches')->insert($batch(['as_of_ts' => '2026-01-05T10:40:00+05:30', 'trigger' => 'CRON'])));
        $this->assertRejected(fn () => DB::table('analysis_batches')->insert($batch(['as_of_ts' => '2026-01-06T10:40:00+05:30'])));  // date mismatch
        $this->assertRejected(fn () => DB::table('analysis_batches')->insert($batch([
            'as_of_ts' => '2026-01-05T10:45:00+05:30', 'instruments_total' => 10, 'instruments_completed' => 8, 'instruments_failed' => 3,
        ])));
    }

    public function test_swing_points_validate_labels_and_forbid_look_ahead(): void
    {
        $in = $this->inputs();
        $run = $this->analysisRun($in);
        $swing = fn (array $o = []) => array_merge([
            'id' => $this->id(), 'analysis_run_id' => $run, 'kind' => 'HIGH', 'timeframe' => '5m', 'bar_index' => 100,
            'bar_date' => '2026-01-05', 'bar_start' => '2026-01-05T09:50:00+05:30', 'price' => 150.5, 'label' => 'HH',
            'confirmed_at_index' => 102, 'confirmed_at_date' => '2026-01-05', 'confirmed_at_bar_start' => '2026-01-05T10:00:00+05:30',
        ], $o);

        DB::table('swing_points')->insert($swing());
        DB::table('swing_points')->insert($swing(['kind' => 'LOW', 'label' => 'HL']));
        DB::table('swing_points')->insert($swing(['kind' => 'LOW', 'label' => 'NONE']));

        $this->assertRejected(fn () => DB::table('swing_points')->insert($swing(['label' => 'HL'])));                 // low label on a high
        $this->assertRejected(fn () => DB::table('swing_points')->insert($swing(['confirmed_at_index' => 99])));      // confirmed before it formed
        $this->assertRejected(fn () => DB::table('swing_points')->insert($swing(['confirmed_at_date' => '2026-01-02'])));
        $this->assertRejected(fn () => DB::table('swing_points')->insert($swing(['confirmed_at_bar_start' => '2026-01-05T09:45:00+05:30'])));  // known before its bar
        $this->assertRejected(fn () => DB::table('swing_points')->insert($swing(['timeframe' => '2h'])));
        $this->assertRejected(fn () => DB::table('swing_points')->insert($swing(['timeframe' => null])));
        $this->assertRejected(fn () => DB::table('swing_points')->insert($swing(['price' => 0])));
        $this->assertRejected(fn () => DB::table('swing_points')->insert($swing(['kind' => 'MID'])));
    }

    public function test_zones_events_and_liquidity_rules(): void
    {
        $run = $this->analysisRun($this->inputs());
        $zone = fn (array $o = []) => array_merge([
            'id' => $this->id(), 'analysis_run_id' => $run, 'role' => 'SUPPORT', 'low' => 98, 'high' => 101,
            'strength_score' => 60, 'strength_bucket' => 'MODERATE', 'status' => 'ACTIVE', 'formed_at_date' => '2025-10-01',
            'formed_at_bar_start' => '2025-10-01T11:00:00+05:30',
        ], $o);

        DB::table('price_zones')->insert($zone());
        $this->assertRejected(fn () => DB::table('price_zones')->insert($zone(['low' => 102])));                      // inverted
        $this->assertRejected(fn () => DB::table('price_zones')->insert($zone(['strength_score' => 101])));
        $this->assertRejected(fn () => DB::table('price_zones')->insert($zone(['strength_bucket' => 'HUGE'])));
        $this->assertRejected(fn () => DB::table('price_zones')->insert($zone(['broken_at_date' => '2025-09-01'])));
        $this->assertRejected(fn () => DB::table('price_zones')->insert($zone(['broken_at_bar_start' => '2025-10-01T10:55:00+05:30'])));

        $this->assertRejected(fn () => DB::table('structure_events')->insert([
            'id' => $this->id(), 'analysis_run_id' => $run, 'event_type' => 'BREAKDOWN', 'direction' => 'UP', 'timeframe' => '5m',
            'level_price' => 100, 'break_date' => '2026-01-02', 'break_bar_start' => '2026-01-02T10:00:00+05:30', 'break_close' => 101,
        ]));
        DB::table('structure_events')->insert([
            'id' => $this->id(), 'analysis_run_id' => $run, 'event_type' => 'BOS', 'direction' => 'UP', 'timeframe' => '15m',
            'level_price' => 100, 'break_date' => '2026-01-02', 'break_bar_start' => '2026-01-02T10:00:00+05:30', 'break_close' => 101,
        ]);

        $this->assertRejected(fn () => DB::table('liquidity_events')->insert([
            'id' => $this->id(), 'analysis_run_id' => $run, 'event_type' => 'EQUAL_HIGHS',
            'level_price' => 120, 'first_date' => '2026-01-05', 'last_date' => '2026-01-01',
            'first_bar_start' => '2026-01-05T10:00:00+05:30', 'last_bar_start' => '2026-01-01T10:00:00+05:30',
        ]));
        $this->assertRejected(fn () => DB::table('liquidity_events')->insert([
            'id' => $this->id(), 'analysis_run_id' => $run, 'event_type' => 'EQUAL_HIGHS', 'level_price' => 120,
            'first_date' => '2026-01-05', 'last_date' => '2026-01-05',
            'first_bar_start' => '2026-01-05T10:00:00+05:30', 'last_bar_start' => '2026-01-05T09:55:00+05:30',
        ]));
    }

    public function test_run_children_are_immutable_and_cascade_with_the_run(): void
    {
        $in = $this->inputs();
        $run = $this->analysisRun($in);
        $swing = $this->id();
        DB::table('swing_points')->insert([
            'id' => $swing, 'analysis_run_id' => $run, 'kind' => 'HIGH', 'timeframe' => '5m', 'bar_index' => 1,
            'bar_date' => '2026-01-05', 'bar_start' => '2026-01-05T09:20:00+05:30', 'price' => 100, 'label' => 'HH',
            'confirmed_at_index' => 3, 'confirmed_at_date' => '2026-01-05', 'confirmed_at_bar_start' => '2026-01-05T09:30:00+05:30',
        ]);
        DB::table('structure_events')->insert([
            'id' => $this->id(), 'analysis_run_id' => $run, 'event_type' => 'BOS', 'direction' => 'UP', 'timeframe' => '5m',
            'level_price' => 100, 'level_swing_point_id' => $swing, 'break_date' => '2026-01-05',
            'break_bar_start' => '2026-01-05T10:05:00+05:30', 'break_close' => 102,
        ]);
        $setup = $this->detectedSetup($run, $in['instrument'], ['anchor_swing_point_id' => $swing]);

        $this->assertRejected(fn () => DB::table('swing_points')->where('id', $swing)->update(['price' => 101]));
        $this->assertRejected(fn () => DB::table('detected_setups')->where('id', $setup)->update(['status' => 'EXPIRED']));

        // Retention may delete a run; everything that hangs off it goes too, despite cross-references.
        DB::table('analysis_runs')->where('id', $run)->delete();
        foreach (['swing_points', 'structure_events', 'detected_setups'] as $table) {
            $this->assertSame(0, DB::table($table)->count(), $table);
        }
    }

    public function test_setup_rules_short_is_informational_and_long_levels_are_ordered(): void
    {
        $in = $this->inputs();
        $run = $this->analysisRun($in);
        $make = fn (array $o) => fn () => $this->detectedSetup($run, $in['instrument'], $o);

        DB::transaction($make([]));
        DB::transaction($make(['direction' => 'SHORT', 'informational' => true, 'stop_price' => 105, 'target_price' => 90]));
        DB::transaction($make(['entry_price' => null, 'stop_price' => null, 'target_price' => null, 'trigger_price' => 101]));

        $this->assertRejected($make(['direction' => 'SHORT', 'informational' => false]));            // C-12
        $this->assertRejected($make(['stop_price' => 100]));                                         // stop == entry
        $this->assertRejected($make(['stop_price' => 101]));                                         // stop above entry
        $this->assertRejected($make(['target_price' => 99]));                                        // target below entry
        $this->assertRejected($make(['paqs_score' => 101]));
        $this->assertRejected($make(['setup_type' => 'RANGE_BREAKOUT']));
        $this->assertRejected($make(['status' => 'OPEN']));
        $this->assertRejected($make(['target_source' => 'GUESS']));
        $this->assertRejected($make(['status_changed_date' => '2026-01-01']));
        $this->assertRejected($make(['setup_key' => 'abc']));
        $this->assertRejected($make(['rr' => 0]));
        $this->assertRejected($make(['detected_at_bar_start' => null]));
        // Validity: valid_until needs signal_at and cannot precede it (TRD-04 §12).
        $this->assertRejected($make(['valid_until' => '2026-01-05T10:40:00+05:30']));
        $this->assertRejected($make(['signal_at' => '2026-01-05T10:30:00+05:30', 'valid_until' => '2026-01-05T10:25:00+05:30']));
        DB::transaction($make(['setup_type' => 'OPENING_RANGE_BREAKOUT', 'signal_at' => '2026-01-05T10:30:00+05:30', 'valid_until' => '2026-01-05T10:35:00+05:30']));
        DB::transaction($make(['setup_type' => 'PREV_DAY_LOW_BREAK', 'direction' => 'SHORT', 'informational' => true, 'stop_price' => 105, 'target_price' => 90]));
    }

    public function test_primary_setup_fk_is_deferred_so_run_and_setup_can_insert_together(): void
    {
        $in = $this->inputs();
        $setupId = $this->id();

        // Run first (pointing at a setup that does not exist yet), then the setup; valid at commit time.
        DB::transaction(function () use ($in, $setupId) {
            $run = $this->analysisRun($in, ['primary_setup_id' => $setupId]);
            DB::table('detected_setups')->insert([
                'id' => $setupId, 'analysis_run_id' => $run, 'instrument_id' => $in['instrument'], 'setup_key' => $this->hash(),
                'setup_type' => 'TREND_PULLBACK', 'direction' => 'LONG', 'informational' => false, 'status' => 'FORMING',
                'detected_at_date' => '2026-01-05', 'detected_at_bar_start' => '2026-01-05T10:25:00+05:30',
                'status_changed_date' => '2026-01-05', 'paqs_score' => 50,
                'paqs_version' => 'paqs-0.1.0', 'paqs_components' => '{}',
            ]);
            DB::statement('SET CONSTRAINTS ALL IMMEDIATE');
        });
        $this->assertSame($setupId, DB::table('analysis_runs')->value('primary_setup_id'));

        // A dangling primary_setup_id is caught when constraints are checked.
        $this->assertRejected(function () use ($in) {
            $this->analysisRun(array_merge($in, ['ruleset' => $this->ruleset(['version' => '0.9.0'])]), ['primary_setup_id' => $this->id()]);
            DB::statement('SET CONSTRAINTS ALL IMMEDIATE');
        });
    }

    public function test_ai_explanation_rules_and_summary_cache(): void
    {
        $in = $this->inputs();
        $run = $this->analysisRun($in);
        $setup = $this->detectedSetup($run, $in['instrument']);
        $tenant = $this->id();
        $user = $this->id();
        DB::table('tenants')->insert(['id' => $tenant, 'name' => 't', 'slug' => 't', 'kind' => 'PERSONAL']);
        DB::table('users')->insert(['id' => $user, 'email' => 'u@example.com', 'password' => 'x']);
        $explain = fn (array $o = []) => array_merge([
            'id' => $this->id(), 'analysis_run_id' => $run, 'detected_setup_id' => $setup, 'kind' => 'SETUP_SUMMARY',
            'prompt_version' => 'v1', 'model_provider' => 'p', 'model_id' => 'm', 'context_hash' => $this->hash(), 'status' => 'COMPLETED',
        ], $o);

        DB::table('ai_explanations')->insert($explain());                                             // shared summary: no tenant/user
        DB::table('ai_explanations')->insert($explain(['status' => 'FAILED']));                       // failures are not cached
        DB::table('ai_explanations')->insert($explain(['status' => 'FALLBACK', 'model_provider' => null, 'model_id' => null]));
        DB::table('ai_explanations')->insert($explain(['model_id' => 'm2']));                         // other model: separate cache entry
        DB::table('ai_explanations')->insert($explain([
            'kind' => 'CHART_QA', 'question' => 'Why is this a retest?', 'tenant_id' => $tenant, 'user_id' => $user,
        ]));

        $this->assertRejected(fn () => DB::table('ai_explanations')->insert($explain()));             // duplicate cache entry
        $this->assertRejected(fn () => DB::table('ai_explanations')->insert($explain(['kind' => 'CHART_QA', 'tenant_id' => $tenant, 'user_id' => $user])));   // Q&A without question
        $this->assertRejected(fn () => DB::table('ai_explanations')->insert($explain(['question' => 'stray', 'model_id' => 'm3'])));                         // question on a summary
        $this->assertRejected(fn () => DB::table('ai_explanations')->insert($explain(['kind' => 'CHART_QA', 'question' => 'q'])));                           // Q&A without owner
        $this->assertRejected(fn () => DB::table('ai_explanations')->insert($explain(['tenant_id' => $tenant, 'model_id' => 'm4'])));                       // tenant without user
        $this->assertRejected(fn () => DB::table('ai_explanations')->insert($explain(['model_id' => null, 'status' => 'FAILED'])));                          // model required unless FALLBACK
        $this->assertRejected(fn () => DB::table('ai_explanations')->insert($explain(['status' => 'MAYBE', 'model_id' => 'm5'])));
        $this->assertRejected(fn () => DB::table('ai_explanations')->insert($explain(['cost_usd' => -1, 'model_id' => 'm6'])));
    }

    public function test_run_referenced_by_an_explanation_cannot_be_deleted(): void
    {
        $in = $this->inputs();
        $run = $this->analysisRun($in);
        DB::table('ai_explanations')->insert([
            'id' => $this->id(), 'analysis_run_id' => $run, 'kind' => 'SETUP_SUMMARY', 'prompt_version' => 'v1',
            'model_provider' => 'p', 'model_id' => 'm', 'context_hash' => $this->hash(), 'status' => 'COMPLETED',
        ]);

        $this->assertRejected(fn () => DB::table('analysis_runs')->where('id', $run)->delete());     // retention keeps referenced runs
    }
}
