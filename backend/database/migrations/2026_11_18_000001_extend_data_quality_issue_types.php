<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/*
 * Intraday data-quality issue types (ENG-05 §12). The daily list in ARC-03 §6.8 did not include the bar-level checks
 * the bar-close fetcher records, so the engine could not persist them.
 *
 * Added: MISSING_BAR, LATE_BAR, MISALIGNED_BAR, OUTSIDE_SESSION, AGGREGATE_MISMATCH.
 * Down removes rows of the new types first (they would violate the restored constraint); development data only.
 */
return new class extends Migration
{
    public function up(): void
    {
        DB::unprepared(<<<'SQL'
            ALTER TABLE data_quality_issues DROP CONSTRAINT ck_data_quality_issues__issue_type;
            ALTER TABLE data_quality_issues ADD CONSTRAINT ck_data_quality_issues__issue_type CHECK (issue_type IN (
                'MISSING_SESSION', 'OHLC_INVALID', 'DUPLICATE', 'PRICE_SPIKE', 'ZERO_VOLUME', 'STALE_DATA', 'PROVIDER_GAP',
                'MISSING_BAR', 'LATE_BAR', 'MISALIGNED_BAR', 'OUTSIDE_SESSION', 'AGGREGATE_MISMATCH'
            ));
        SQL);
    }

    public function down(): void
    {
        DB::unprepared(<<<'SQL'
            DELETE FROM data_quality_issues WHERE issue_type IN (
                'MISSING_BAR', 'LATE_BAR', 'MISALIGNED_BAR', 'OUTSIDE_SESSION', 'AGGREGATE_MISMATCH'
            );
            ALTER TABLE data_quality_issues DROP CONSTRAINT ck_data_quality_issues__issue_type;
            ALTER TABLE data_quality_issues ADD CONSTRAINT ck_data_quality_issues__issue_type CHECK (issue_type IN (
                'MISSING_SESSION', 'OHLC_INVALID', 'DUPLICATE', 'PRICE_SPIKE', 'ZERO_VOLUME', 'STALE_DATA', 'PROVIDER_GAP'
            ));
        SQL);
    }
};
