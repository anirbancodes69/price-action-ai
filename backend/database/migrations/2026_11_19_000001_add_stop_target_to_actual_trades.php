<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/*
 * Optional stop and target kept on an actual trade (ARC-03 §8). A trade logged without a trade plan had no stop, so the
 * account limits could not count its risk. The owner enters them and may move them; both are the owner's own levels.
 * The stop/entry relation is not a CHECK: a trailed stop may sit above the average entry.
 */
return new class extends Migration
{
    public function up(): void
    {
        DB::unprepared(<<<'SQL'
            ALTER TABLE actual_trades
                ADD COLUMN stop_price numeric(12,2) NULL,
                ADD COLUMN target_price numeric(12,2) NULL,
                ADD CONSTRAINT ck_actual_trades__stop_price CHECK (stop_price IS NULL OR stop_price > 0),
                ADD CONSTRAINT ck_actual_trades__target_price CHECK (target_price IS NULL OR target_price > 0);
        SQL);
    }

    public function down(): void
    {
        DB::unprepared(<<<'SQL'
            ALTER TABLE actual_trades
                DROP CONSTRAINT ck_actual_trades__stop_price,
                DROP CONSTRAINT ck_actual_trades__target_price,
                DROP COLUMN stop_price,
                DROP COLUMN target_price;
        SQL);
    }
};
