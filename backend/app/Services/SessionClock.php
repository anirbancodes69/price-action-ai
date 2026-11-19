<?php

namespace App\Services;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;

/**
 * The trading session of a day from `market_calendar`, and the entry cutoff derived from the ruleset
 * (TRD-01 §4.1). A day without a calendar row is treated as a normal weekday session (holidays are not loaded yet).
 */
class SessionClock
{
    public const TZ = 'Asia/Kolkata';

    public function __construct(private readonly RulesetParameters $ruleset) {}

    /** Start of the 5m bar that is currently closing or has just closed: the request's `as_of_ts`. */
    public function lastBarEnd(?CarbonImmutable $now = null): CarbonImmutable
    {
        $t = ($now ?? CarbonImmutable::now())->setTimezone(self::TZ);

        return $t->setTime((int) $t->format('H'), intdiv((int) $t->format('i'), 5) * 5, 0);
    }

    public function entryCutoff(?CarbonImmutable $now = null): CarbonImmutable
    {
        return $this->beforeClose('session.entry_cutoff_minutes_before_close', $now);
    }

    /** The forced session-end exit time (TRD-05 §8). */
    public function sessionEndExit(?CarbonImmutable $now = null): CarbonImmutable
    {
        return $this->beforeClose('session.exit_minutes_before_close', $now);
    }

    private function beforeClose(string $parameter, ?CarbonImmutable $now): CarbonImmutable
    {
        $day = ($now ?? CarbonImmutable::now())->setTimezone(self::TZ);
        $row = DB::table('market_calendar')->where('exchange', 'NSE')->where('calendar_date', $day->toDateString())->first();
        $close = $row !== null && $row->session_close !== null ? (string) $row->session_close : '15:30:00';

        return CarbonImmutable::parse($day->toDateString().' '.$close, self::TZ)
            ->subMinutes((int) $this->ruleset->get($parameter));
    }
}
