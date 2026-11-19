<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/*
 * ADR-017: a trade plan may exist without a stored analysis run (ADR-016 stores none in personal mode). The plan keeps its
 * own record of what it was made from: setup type, PAQS and the end of the 5m bar analysed.
 * Down restores NOT NULL, which fails while plans without a run exist (development data only).
 */
return new class extends Migration
{
    public function up(): void
    {
        DB::unprepared(<<<'SQL'
            ALTER TABLE trade_plans
                ALTER COLUMN analysis_run_id DROP NOT NULL,
                ADD COLUMN setup_type text NULL,
                ADD COLUMN paqs smallint NULL,
                ADD COLUMN as_of_ts timestamptz NULL,
                ADD CONSTRAINT ck_trade_plans__paqs CHECK (paqs IS NULL OR paqs BETWEEN 0 AND 100);
        SQL);
    }

    public function down(): void
    {
        DB::unprepared(<<<'SQL'
            DELETE FROM trade_plans WHERE analysis_run_id IS NULL;
            ALTER TABLE trade_plans
                DROP CONSTRAINT ck_trade_plans__paqs,
                DROP COLUMN setup_type,
                DROP COLUMN paqs,
                DROP COLUMN as_of_ts,
                ALTER COLUMN analysis_run_id SET NOT NULL;
        SQL);
    }
};
