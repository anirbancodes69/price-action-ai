<?php

namespace Tests\Feature\Database;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Tests\TestCase;

/** ARC-03 §8: trading invariants (long-only, stop < entry < target, trade lifecycles) enforced by the database. */
class TradingSchemaTest extends TestCase
{
    use AssertsDatabaseRejects;
    use RefreshDatabase;

    private function id(): string
    {
        return (string) Str::uuid7();
    }

    private function hash(): string
    {
        return hash('sha256', Str::random(12));
    }

    /** @return array{tenant: string, user: string, instrument: string, run: string, ruleset: string, risk: string} */
    private function base(): array
    {
        $in = ['tenant' => $this->id(), 'user' => $this->id(), 'instrument' => $this->id(), 'run' => $this->id(),
            'ruleset' => $this->id(), 'risk' => $this->id(), 'source' => $this->id(), 'snapshot' => $this->id()];

        DB::table('tenants')->insert(['id' => $in['tenant'], 'name' => 't', 'slug' => 't'.substr($in['tenant'], -8), 'kind' => 'PERSONAL']);
        DB::table('users')->insert(['id' => $in['user'], 'email' => $in['user'].'@example.com', 'password' => 'x']);
        DB::table('risk_profiles')->insert([
            'id' => $in['risk'], 'tenant_id' => $in['tenant'], 'user_id' => $in['user'], 'version' => 1, 'is_current' => true,
            'trading_capital' => 500000, 'risk_per_trade_pct' => 1, 'max_open_positions' => 5,
            'max_portfolio_heat_pct' => 5, 'max_position_pct' => 25,
        ]);
        DB::table('data_sources')->insert(['id' => $in['source'], 'mode' => 'DEMO', 'provider' => 'DEMO', 'name' => 'Demo']);
        DB::table('instruments')->insert([
            'id' => $in['instrument'], 'exchange' => 'NSE', 'segment' => 'EQ', 'trading_symbol' => 'T'.substr($in['instrument'], -6),
            'name' => 'Test', 'status' => 'ACTIVE',
        ]);
        DB::table('ruleset_versions')->insert([
            'id' => $in['ruleset'], 'ruleset_code' => 'pa-core', 'version' => '0.1.0', 'parameters' => '{}',
            'parameters_hash' => $this->hash(), 'score_version' => 'paqs-0.1.0',
        ]);
        DB::table('candle_snapshots')->insert([
            'id' => $in['snapshot'], 'data_source_id' => $in['source'], 'instrument_id' => $in['instrument'], 'timeframe' => '1D',
            'from_date' => '2025-01-01', 'to_date' => '2026-01-05', 'bar_count' => 250, 'price_basis' => 'ADJUSTED',
            'content_hash' => $this->hash(), 'payload' => 'x',
        ]);
        DB::table('analysis_runs')->insert([
            'id' => $in['run'], 'data_source_id' => $in['source'], 'instrument_id' => $in['instrument'],
            'candle_snapshot_id' => $in['snapshot'], 'ruleset_version_id' => $in['ruleset'], 'engine_version' => '0.1.0',
            'as_of_date' => '2026-01-05', 'status' => 'COMPLETED', 'signal_state' => 'NO_TRADE', 'result_hash' => $this->hash(),
        ]);

        return $in;
    }

    private function plan(array $in, array $o = []): string
    {
        $id = $this->id();
        DB::table('trade_plans')->insert(array_merge([
            'id' => $id, 'tenant_id' => $in['tenant'], 'user_id' => $in['user'], 'plan_number' => random_int(1, 1_000_000),
            'instrument_id' => $in['instrument'], 'analysis_run_id' => $in['run'], 'source' => 'ENGINE', 'direction' => 'LONG',
            'status' => 'PENDING', 'entry_price' => 100, 'stop_price' => 95, 'target_price' => 115,
            'engine_entry_price' => 100, 'engine_stop_price' => 95, 'engine_target_price' => 115,
            'quantity' => 100, 'risk_budget' => 5000, 'risk_amount' => 500, 'position_value' => 10000, 'rr' => 3,
            'risk_profile_id' => $in['risk'], 'ruleset_version_id' => $in['ruleset'],
        ], $o));

        return $id;
    }

    private function paperAccount(array $in): string
    {
        $id = $this->id();
        DB::table('paper_accounts')->insert([
            'id' => $id, 'tenant_id' => $in['tenant'], 'user_id' => $in['user'], 'starting_capital' => 500000, 'is_current' => true,
        ]);

        return $id;
    }

    private function paperTrade(array $in, string $plan, string $account, array $o = []): string
    {
        $id = $this->id();
        DB::table('paper_trades')->insert(array_merge([
            'id' => $id, 'tenant_id' => $in['tenant'], 'user_id' => $in['user'], 'paper_account_id' => $account,
            'trade_plan_id' => $plan, 'instrument_id' => $in['instrument'], 'status' => 'OPEN', 'entry_date' => '2026-01-06',
            'entry_price' => 100.1, 'quantity' => 100, 'initial_stop' => 95, 'current_stop' => 95, 'target_price' => 115,
        ], $o));

        return $id;
    }

    public function test_trade_plans_are_long_only_with_stop_below_entry_below_target(): void
    {
        $in = $this->base();
        $this->plan($in);

        $this->assertRejected(fn () => $this->plan($in, ['direction' => 'SHORT']));
        $this->assertRejected(fn () => $this->plan($in, ['stop_price' => 100]));                     // stop == entry
        $this->assertRejected(fn () => $this->plan($in, ['stop_price' => 105]));                     // stop above entry
        $this->assertRejected(fn () => $this->plan($in, ['target_price' => 100]));                   // target == entry
        $this->assertRejected(fn () => $this->plan($in, ['target_price' => 90]));
        $this->assertRejected(fn () => $this->plan($in, ['engine_stop_price' => 101]));              // engine levels obey it too
    }

    public function test_trade_plan_fields_and_numbering(): void
    {
        $in = $this->base();
        $this->plan($in, ['plan_number' => 1]);

        $this->assertRejected(fn () => $this->plan($in, ['plan_number' => 1]));                      // per-tenant unique
        $this->assertRejected(fn () => $this->plan($in, ['plan_number' => 0]));
        $this->assertRejected(fn () => $this->plan($in, ['quantity' => 0]));
        $this->assertRejected(fn () => $this->plan($in, ['status' => 'DONE']));
        $this->assertRejected(fn () => $this->plan($in, ['source' => 'IMPORT']));
        $this->assertRejected(fn () => $this->plan($in, ['rr' => 0]));
        $this->assertRejected(fn () => $this->plan($in, ['note' => str_repeat('x', 2001)]));
        $this->assertRejected(fn () => $this->plan($in, ['setup_key' => 'nope']));
        $this->assertRejected(fn () => $this->plan($in, ['analysis_run_id' => $this->id()]));        // run must exist

        // A manual plan carries no engine levels.
        $this->assertRejected(fn () => $this->plan($in, ['source' => 'MANUAL']));
        $this->plan($in, ['source' => 'MANUAL', 'engine_entry_price' => null, 'engine_stop_price' => null,
            'engine_target_price' => null, 'levels_overridden' => true]);
    }

    public function test_one_paper_account_is_current_and_one_paper_trade_per_plan(): void
    {
        $in = $this->base();
        $account = $this->paperAccount($in);

        $this->assertRejected(fn () => $this->paperAccount($in));                                    // second current account
        DB::table('paper_accounts')->insert([
            'id' => $this->id(), 'tenant_id' => $in['tenant'], 'user_id' => $in['user'], 'starting_capital' => 100000,
            'reset_generation' => 1, 'is_current' => false,
        ]);
        $this->assertRejected(fn () => DB::table('paper_accounts')->insert([
            'id' => $this->id(), 'tenant_id' => $in['tenant'], 'user_id' => $in['user'], 'starting_capital' => 100000,
            'reset_generation' => 1, 'is_current' => false,
        ]));

        $plan = $this->plan($in);
        $this->paperTrade($in, $plan, $account);
        $this->assertRejected(fn () => $this->paperTrade($in, $plan, $account));
    }

    public function test_paper_trade_stop_only_moves_up_and_closing_requires_exit_facts(): void
    {
        $in = $this->base();
        $account = $this->paperAccount($in);
        $trade = $this->paperTrade($in, $this->plan($in), $account);

        DB::table('paper_trades')->where('id', $trade)->update(['current_stop' => 97]);
        $this->assertRejected(fn () => DB::table('paper_trades')->where('id', $trade)->update(['current_stop' => 94]));
        $this->assertRejected(fn () => DB::table('paper_trades')->where('id', $trade)->update(['quantity' => 0]));

        // CLOSED without exit facts, and exit facts on an OPEN trade, are both rejected.
        $this->assertRejected(fn () => DB::table('paper_trades')->where('id', $trade)->update(['status' => 'CLOSED']));
        $this->assertRejected(fn () => DB::table('paper_trades')->where('id', $trade)->update(['exit_price' => 110]));
        $this->assertRejected(fn () => DB::table('paper_trades')->where('id', $trade)->update([
            'status' => 'CLOSED', 'exit_date' => '2026-01-10', 'exit_price' => 110, 'exit_reason' => 'SOMETHING',
            'gross_pnl' => 10, 'net_pnl' => 9,
        ]));
        $this->assertRejected(fn () => DB::table('paper_trades')->where('id', $trade)->update([
            'status' => 'CLOSED', 'exit_date' => '2026-01-01', 'exit_price' => 110, 'exit_reason' => 'TARGET',   // before entry
            'gross_pnl' => 10, 'net_pnl' => 9,
        ]));

        DB::table('paper_trades')->where('id', $trade)->update([
            'status' => 'CLOSED', 'exit_date' => '2026-01-10', 'exit_price' => 115, 'exit_reason' => 'TARGET',
            'gross_pnl' => 1490, 'charges' => 40, 'net_pnl' => 1450, 'r_multiple' => 2.9,
        ]);
        $this->assertSame('CLOSED', DB::table('paper_trades')->where('id', $trade)->value('status'));
    }

    public function test_paper_trade_events_validate_type_and_cascade(): void
    {
        $in = $this->base();
        $trade = $this->paperTrade($in, $this->plan($in), $this->paperAccount($in));
        $event = fn (string $type) => DB::table('paper_trade_events')->insert([
            'id' => $this->id(), 'paper_trade_id' => $trade, 'event_type' => $type, 'event_date' => '2026-01-06',
        ]);

        $event('FILLED');
        $this->assertRejected(fn () => $event('REOPENED'));

        DB::table('paper_trades')->where('id', $trade)->delete();
        $this->assertSame(0, DB::table('paper_trade_events')->where('paper_trade_id', $trade)->count());
    }

    public function test_actual_trades_are_long_only_and_closed_means_flat(): void
    {
        $in = $this->base();
        $trade = fn (array $o = []) => DB::table('actual_trades')->insert(array_merge([
            'id' => $this->id(), 'tenant_id' => $in['tenant'], 'user_id' => $in['user'], 'instrument_id' => $in['instrument'],
            'direction' => 'LONG', 'status' => 'OPEN', 'quantity_open' => 10,
        ], $o));

        $trade();
        $this->assertRejected(fn () => $trade(['direction' => 'SHORT']));
        $this->assertRejected(fn () => $trade(['quantity_open' => -1]));
        $this->assertRejected(fn () => $trade(['source' => 'SCREENSHOT']));
        $this->assertRejected(fn () => $trade(['status' => 'CLOSED', 'quantity_open' => 10, 'closed_at' => now()]));  // not flat
        $this->assertRejected(fn () => $trade(['status' => 'CLOSED', 'quantity_open' => 0]));                          // no closed_at
        $this->assertRejected(fn () => $trade(['status' => 'OPEN', 'closed_at' => now()]));
        $trade(['status' => 'CLOSED', 'quantity_open' => 0, 'closed_at' => now()]);
    }

    public function test_fills_validate_and_broker_trade_ids_are_unique_per_trade(): void
    {
        $in = $this->base();
        $trade = $this->id();
        DB::table('actual_trades')->insert([
            'id' => $trade, 'tenant_id' => $in['tenant'], 'user_id' => $in['user'], 'instrument_id' => $in['instrument'],
            'direction' => 'LONG', 'status' => 'OPEN', 'quantity_open' => 10,
        ]);
        $fill = fn (array $o = []) => DB::table('actual_trade_fills')->insert(array_merge([
            'id' => $this->id(), 'actual_trade_id' => $trade, 'side' => 'BUY', 'quantity' => 10, 'price' => 100,
            'executed_at' => now(),
        ], $o));

        $fill(['broker_trade_id' => 'T1']);
        $fill();
        $fill();                                                                                     // NULL broker ids may repeat
        $this->assertRejected(fn () => $fill(['broker_trade_id' => 'T1']));
        $this->assertRejected(fn () => $fill(['side' => 'SHORT']));
        $this->assertRejected(fn () => $fill(['quantity' => 0]));
        $this->assertRejected(fn () => $fill(['price' => 0]));
        $this->assertRejected(fn () => $fill(['fees' => -1]));
    }

    public function test_journal_entry_points_at_exactly_one_matching_trade_once(): void
    {
        $in = $this->base();
        $paper = $this->paperTrade($in, $this->plan($in), $this->paperAccount($in));
        $actual = $this->id();
        DB::table('actual_trades')->insert([
            'id' => $actual, 'tenant_id' => $in['tenant'], 'user_id' => $in['user'], 'instrument_id' => $in['instrument'],
            'direction' => 'LONG', 'status' => 'OPEN', 'quantity_open' => 10,
        ]);
        $entry = fn (array $o) => DB::table('journal_entries')->insert(array_merge([
            'id' => $this->id(), 'tenant_id' => $in['tenant'], 'user_id' => $in['user'],
        ], $o));

        $entry(['trade_kind' => 'PAPER', 'paper_trade_id' => $paper]);
        $entry(['trade_kind' => 'ACTUAL', 'actual_trade_id' => $actual]);

        $this->assertRejected(fn () => $entry(['trade_kind' => 'PAPER', 'paper_trade_id' => $paper]));            // one per trade
        $this->assertRejected(fn () => $entry(['trade_kind' => 'ACTUAL', 'actual_trade_id' => $actual]));
        $this->assertRejected(fn () => $entry(['trade_kind' => 'PAPER']));                                         // no trade
        $this->assertRejected(fn () => $entry(['trade_kind' => 'PAPER', 'actual_trade_id' => $actual]));          // wrong kind
        $this->assertRejected(fn () => $entry(['trade_kind' => 'ACTUAL', 'paper_trade_id' => $paper, 'actual_trade_id' => $actual]));
        $this->assertRejected(fn () => $entry(['trade_kind' => 'PAPER', 'paper_trade_id' => $this->id()]));      // dangling
    }

    public function test_journal_entry_limits(): void
    {
        $in = $this->base();
        $make = function (array $o) use ($in) {
            $plan = $this->plan($in);
            $trade = $this->paperTrade($in, $plan, DB::table('paper_accounts')->where('tenant_id', $in['tenant'])->value('id') ?? $this->paperAccount($in));

            DB::table('journal_entries')->insert(array_merge([
                'id' => $this->id(), 'tenant_id' => $in['tenant'], 'user_id' => $in['user'],
                'trade_kind' => 'PAPER', 'paper_trade_id' => $trade,
            ], $o));
        };

        $make(['rating' => 5, 'tags' => '{breakout,patience}']);
        $this->assertRejected(fn () => $make(['rating' => 0]));
        $this->assertRejected(fn () => $make(['rating' => 6]));
        $this->assertRejected(fn () => $make(['status' => 'ARCHIVED']));
        $this->assertRejected(fn () => $make(['notes' => str_repeat('x', 10001)]));
    }

    public function test_backtest_run_parameters_are_bounded(): void
    {
        $in = $this->base();
        $run = fn (array $o = []) => DB::table('backtest_runs')->insert(array_merge([
            'id' => $this->id(), 'tenant_id' => $in['tenant'], 'user_id' => $in['user'], 'ruleset_version_id' => $in['ruleset'],
            'data_source_id' => $in['source'], 'instrument_ids' => '{'.$in['instrument'].'}', 'date_from' => '2024-01-01',
            'date_to' => '2025-01-01', 'starting_capital' => 500000, 'risk_per_trade_pct' => 1, 'sizing_mode' => 'FIXED',
        ], $o));

        $run();
        $run(['risk_per_trade_pct' => 5, 'purpose' => 'OOS']);
        $this->assertRejected(fn () => $run(['date_to' => '2024-01-01']));                           // from < to
        $this->assertRejected(fn () => $run(['starting_capital' => 9999]));
        $this->assertRejected(fn () => $run(['risk_per_trade_pct' => 0.05]));
        $this->assertRejected(fn () => $run(['risk_per_trade_pct' => 5.5]));
        $this->assertRejected(fn () => $run(['sizing_mode' => 'MARTINGALE']));
        $this->assertRejected(fn () => $run(['purpose' => 'LIVE']));
        $this->assertRejected(fn () => $run(['status' => 'PAUSED']));
        $this->assertRejected(fn () => $run(['progress_pct' => 101]));
        $this->assertRejected(fn () => $run(['input_hash' => 'abc']));
        $this->assertRejected(fn () => $run(['instrument_ids' => null]));                           // needs a universe or instruments
        $this->assertRejected(fn () => $run(['data_source_id' => $this->id()]));
    }

    public function test_backtest_trades_never_fill_on_or_before_the_signal_bar(): void
    {
        $in = $this->base();
        $runId = $this->id();
        DB::table('backtest_runs')->insert([
            'id' => $runId, 'tenant_id' => $in['tenant'], 'user_id' => $in['user'], 'ruleset_version_id' => $in['ruleset'],
            'data_source_id' => $in['source'], 'instrument_ids' => '{'.$in['instrument'].'}', 'date_from' => '2024-01-01',
            'date_to' => '2025-01-01', 'starting_capital' => 500000, 'risk_per_trade_pct' => 1, 'sizing_mode' => 'FIXED',
        ]);
        $trade = fn (array $o = []) => DB::table('backtest_trades')->insert(array_merge([
            'id' => $this->id(), 'backtest_run_id' => $runId, 'instrument_id' => $in['instrument'],
            'setup_type' => 'TREND_PULLBACK', 'setup_key' => $this->hash(), 'signal_date' => '2024-03-01', 'outcome' => 'FILLED',
            'entry_date' => '2024-03-04', 'entry_price' => 100, 'quantity' => 50, 'stop_price' => 95, 'target_price' => 115,
        ], $o));

        $trade();
        $trade(['outcome' => 'SKIPPED', 'skip_reason' => 'GAP_TOO_LARGE', 'entry_date' => null, 'entry_price' => null,
            'quantity' => null, 'stop_price' => null, 'target_price' => null]);

        $this->assertRejected(fn () => $trade(['entry_date' => '2024-03-01']));                      // same bar as the signal
        $this->assertRejected(fn () => $trade(['entry_date' => '2024-02-28']));
        $this->assertRejected(fn () => $trade(['entry_date' => null]));                              // FILLED needs entry facts
        $this->assertRejected(fn () => $trade(['stop_price' => 101]));                               // long-only level order
        $this->assertRejected(fn () => $trade(['target_price' => 99]));
        $this->assertRejected(fn () => $trade(['outcome' => 'SKIPPED']));                            // SKIPPED needs a reason, no entry
        $this->assertRejected(fn () => $trade(['exit_date' => '2024-03-01']));                       // exit before entry
        $this->assertRejected(fn () => $trade(['paqs_score' => 101]));
        $this->assertRejected(fn () => $trade(['setup_type' => 'FOMO']));

        DB::table('backtest_runs')->where('id', $runId)->delete();
        $this->assertSame(0, DB::table('backtest_trades')->where('backtest_run_id', $runId)->count());
    }

    public function test_watchlists_and_items(): void
    {
        $in = $this->base();
        $list = fn (string $name) => DB::table('watchlists')->insert([
            'id' => $this->id(), 'tenant_id' => $in['tenant'], 'user_id' => $in['user'], 'name' => $name,
        ]);

        $list('Swing');
        $this->assertRejected(fn () => $list('Swing'));
        $this->assertRejected(fn () => $list(''));
        $this->assertRejected(fn () => $list(str_repeat('x', 61)));
        $list(str_repeat('x', 60));

        $watchlist = DB::table('watchlists')->where('name', 'Swing')->value('id');
        $item = fn () => DB::table('watchlist_items')->insert(['watchlist_id' => $watchlist, 'instrument_id' => $in['instrument']]);
        $item();
        $this->assertRejected($item);

        DB::table('watchlists')->where('id', $watchlist)->delete();
        $this->assertSame(0, DB::table('watchlist_items')->where('watchlist_id', $watchlist)->count());
    }

    public function test_notifications_need_a_type_and_title(): void
    {
        $in = $this->base();
        $note = fn (array $o) => DB::table('notifications')->insert(array_merge([
            'id' => $this->id(), 'tenant_id' => $in['tenant'], 'user_id' => $in['user'],
            'type' => 'PLAN_TRIGGERED', 'title' => 'TP-1 triggered',
        ], $o));

        $note([]);
        $this->assertRejected(fn () => $note(['type' => 'plan triggered']));
        $this->assertRejected(fn () => $note(['title' => '']));
    }

    // ---- Single-writer grants (ARC-01 §6). Skipped where the runtime roles do not exist (plain CI Postgres). ----

    private function requireRoles(): void
    {
        $roles = DB::table('pg_roles')->whereIn('rolname', ['app_backend', 'app_engine'])->count();
        if ($roles < 2) {
            $this->markTestSkipped('Roles app_backend and app_engine are not present in this database cluster.');
        }
    }

    private function can(string $role, string $table, string $privilege): bool
    {
        return (bool) DB::selectOne('SELECT has_table_privilege(?, ?, ?) AS ok', [$role, $table, $privilege])->ok;
    }

    private function canColumn(string $role, string $table, string $column): bool
    {
        return (bool) DB::selectOne('SELECT has_column_privilege(?, ?, ?, ?) AS ok', [$role, $table, $column, 'UPDATE'])->ok;
    }

    public function test_engine_cannot_write_laravel_owned_tables_and_laravel_cannot_write_engine_owned_tables(): void
    {
        $this->requireRoles();

        foreach (['users', 'tenants', 'risk_profiles', 'watchlists', 'actual_trades', 'actual_trade_fills', 'notifications',
            'data_sources', 'ruleset_versions', 'universes', 'market_calendar'] as $table) {
            foreach (['INSERT', 'UPDATE', 'DELETE'] as $privilege) {
                $this->assertFalse($this->can('app_engine', $table, $privilege), "app_engine must not $privilege $table");
            }
            $this->assertTrue($this->can('app_backend', $table, 'INSERT'), "app_backend writes $table");
        }

        foreach (['instruments', 'candles', 'ingestion_runs', 'analysis_batches', 'analysis_runs', 'detected_setups',
            'ai_explanations', 'backtest_trades', 'candle_snapshots', 'universe_memberships'] as $table) {
            foreach (['INSERT', 'UPDATE', 'DELETE'] as $privilege) {
                $this->assertFalse($this->can('app_backend', $table, $privilege), "app_backend must not $privilege $table");
            }
            $this->assertTrue($this->can('app_backend', $table, 'SELECT'), "app_backend reads $table");
            $this->assertTrue($this->can('app_engine', $table, 'INSERT'), "app_engine writes $table");
        }
    }

    public function test_provider_tokens_are_not_readable_by_the_engine(): void
    {
        $this->requireRoles();

        $this->assertFalse($this->can('app_engine', 'provider_connections', 'SELECT'));
        $this->assertTrue($this->can('app_backend', 'provider_connections', 'SELECT'));
    }

    public function test_candle_snapshots_are_write_once_for_application_roles(): void
    {
        $this->requireRoles();

        foreach (['app_backend', 'app_engine'] as $role) {
            $this->assertFalse($this->can($role, 'candle_snapshots', 'UPDATE'), "$role updates snapshots");
            $this->assertFalse($this->can($role, 'candle_snapshots', 'DELETE'), "$role deletes snapshots");
        }
        $this->assertTrue($this->can('app_engine', 'candle_snapshots', 'INSERT'));

        foreach (['analysis_runs', 'swing_points', 'structure_events', 'price_zones', 'liquidity_events', 'detected_setups'] as $table) {
            $this->assertFalse($this->can('app_engine', $table, 'UPDATE'), "app_engine updates $table");
        }
    }

    public function test_audit_log_is_append_only_for_both_roles(): void
    {
        $this->requireRoles();

        foreach (['app_backend', 'app_engine'] as $role) {
            $this->assertTrue($this->can($role, 'audit_logs', 'INSERT'));
            foreach (['UPDATE', 'DELETE', 'TRUNCATE'] as $privilege) {
                $this->assertFalse($this->can($role, 'audit_logs', $privilege), "$role must not $privilege audit_logs");
            }
        }
    }

    public function test_shared_write_exceptions_are_limited_to_the_documented_columns(): void
    {
        $this->requireRoles();

        // trade_plans: engine updates status transitions only.
        $this->assertFalse($this->can('app_engine', 'trade_plans', 'INSERT'));
        $this->assertFalse($this->can('app_engine', 'trade_plans', 'DELETE'));
        foreach (['status', 'status_reason', 'triggered_on', 'lock_version'] as $column) {
            $this->assertTrue($this->canColumn('app_engine', 'trade_plans', $column), "engine updates trade_plans.$column");
        }
        foreach (['entry_price', 'stop_price', 'target_price', 'quantity', 'note'] as $column) {
            $this->assertFalse($this->canColumn('app_engine', 'trade_plans', $column), "engine must not update trade_plans.$column");
        }
        $this->assertTrue($this->can('app_backend', 'trade_plans', 'INSERT'));

        // paper_trades: Laravel moves the stop up and requests a close; it never records fills or P&L.
        $this->assertFalse($this->can('app_backend', 'paper_trades', 'INSERT'));
        $this->assertFalse($this->can('app_backend', 'paper_trades', 'DELETE'));
        foreach (['current_stop', 'exit_requested_on'] as $column) {
            $this->assertTrue($this->canColumn('app_backend', 'paper_trades', $column), "Laravel updates paper_trades.$column");
        }
        foreach (['status', 'exit_price', 'net_pnl', 'entry_price', 'initial_stop'] as $column) {
            $this->assertFalse($this->canColumn('app_backend', 'paper_trades', $column), "Laravel must not update paper_trades.$column");
        }
        $this->assertTrue($this->can('app_engine', 'paper_trades', 'INSERT'));

        // backtest_runs: Laravel creates and cancels; the engine reports progress and results.
        $this->assertFalse($this->can('app_engine', 'backtest_runs', 'INSERT'));
        $this->assertTrue($this->canColumn('app_engine', 'backtest_runs', 'metrics'));
        $this->assertFalse($this->canColumn('app_engine', 'backtest_runs', 'risk_per_trade_pct'));
        $this->assertTrue($this->canColumn('app_backend', 'backtest_runs', 'status'));
        $this->assertFalse($this->canColumn('app_backend', 'backtest_runs', 'metrics'));

        // journal_entries: the engine creates drafts but never edits them.
        $this->assertTrue($this->can('app_engine', 'journal_entries', 'INSERT'));
        $this->assertFalse($this->can('app_engine', 'journal_entries', 'UPDATE'));
        $this->assertTrue($this->can('app_backend', 'journal_entries', 'UPDATE'));
    }

    public function test_tables_created_later_are_closed_to_runtime_roles_by_default(): void
    {
        $this->requireRoles();

        DB::statement('CREATE TABLE zz_future_table (id uuid PRIMARY KEY)');

        foreach (['app_backend', 'app_engine'] as $role) {
            $this->assertFalse($this->can($role, 'zz_future_table', 'SELECT'), "$role reads an unlisted table");
        }
    }
}
