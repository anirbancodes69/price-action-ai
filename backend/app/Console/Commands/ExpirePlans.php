<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

/**
 * Plans never survive the session (TRD-07 §3): once a plan's `valid_until` (the entry cutoff of its day) has passed,
 * a `PENDING` plan becomes `EXPIRED` and an unfilled `TRIGGERED` plan `SKIPPED`. A pure time rule: no trading
 * calculation. Bar-close transitions (triggered, invalidated) are the engine's and are not built (ADR-017).
 */
class ExpirePlans extends Command
{
    protected $signature = 'plans:expire';

    protected $description = 'Expire pending plans and skip unfilled triggered plans whose entry cutoff has passed';

    public function handle(): int
    {
        $count = 0;
        foreach (['PENDING' => ['EXPIRED', 'SESSION_CUTOFF'], 'TRIGGERED' => ['SKIPPED', 'SKIPPED_SESSION_CUTOFF']] as $from => [$to, $reason]) {
            $count += DB::table('trade_plans')
                ->where('status', $from)
                ->whereNotNull('valid_until')
                ->where('valid_until', '<=', now())
                ->update(['status' => $to, 'status_reason' => $reason, 'lock_version' => DB::raw('lock_version + 1'), 'updated_at' => now()]);
        }
        $this->info("Closed {$count} plan(s) past the entry cutoff.");

        return self::SUCCESS;
    }
}
