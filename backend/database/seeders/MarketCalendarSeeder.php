<?php

namespace Database\Seeders;

use DateInterval;
use DatePeriod;
use DateTimeImmutable;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use RuntimeException;

/**
 * Seeds `market_calendar` for NSE from `data/nse-market-calendar.json` (ARC-03 §6.9, TRD-01 §4.1).
 *
 * Weekends are closed; listed holidays are closed with their name; listed special sessions use their own times;
 * every other weekday is a normal session (09:15–15:30). While the file is not marked `verified`, those weekday
 * rows carry the note "Unverified weekday default" so nothing presents them as the official calendar.
 * Existing rows are never overwritten.
 *
 * File shapes: holidays `[{date, name}]`, special_sessions `[{date, open, close, name}]`.
 */
class MarketCalendarSeeder extends Seeder
{
    public const UNVERIFIED_NOTE = 'Unverified weekday default (NSE holidays not loaded)';

    /** @return array<string, mixed> */
    public static function config(): array
    {
        $path = __DIR__.'/data/nse-market-calendar.json';
        $config = json_decode((string) file_get_contents($path), true, flags: JSON_THROW_ON_ERROR);
        if (! is_array($config) || ! isset($config['range']['from'], $config['range']['to'], $config['normal_session'])) {
            throw new RuntimeException("Calendar file {$path} is missing range or normal_session.");
        }

        return $config;
    }

    public function run(): void
    {
        $config = self::config();
        $holidays = array_column($config['holidays'] ?? [], 'name', 'date');
        $special = [];
        foreach ($config['special_sessions'] ?? [] as $s) {
            $special[$s['date']] = $s;
        }
        $verified = (bool) ($config['verified'] ?? false);

        $period = new DatePeriod(
            new DateTimeImmutable($config['range']['from']),
            new DateInterval('P1D'),
            (new DateTimeImmutable($config['range']['to']))->modify('+1 day'),
        );

        $rows = [];
        foreach ($period as $day) {
            $date = $day->format('Y-m-d');
            $weekend = in_array((int) $day->format('N'), [6, 7], true);
            if (isset($special[$date])) {
                $rows[] = ['exchange' => 'NSE', 'calendar_date' => $date, 'is_trading_day' => true,
                    'session_open' => $special[$date]['open'], 'session_close' => $special[$date]['close'],
                    'note' => $special[$date]['name'] ?? 'Special session'];
            } elseif ($weekend || isset($holidays[$date])) {
                $rows[] = ['exchange' => 'NSE', 'calendar_date' => $date, 'is_trading_day' => false,
                    'session_open' => null, 'session_close' => null, 'note' => $holidays[$date] ?? 'Weekend'];
            } else {
                $rows[] = ['exchange' => 'NSE', 'calendar_date' => $date, 'is_trading_day' => true,
                    'session_open' => $config['normal_session']['open'], 'session_close' => $config['normal_session']['close'],
                    'note' => $verified ? null : self::UNVERIFIED_NOTE];
            }
        }

        foreach (array_chunk($rows, 500) as $chunk) {
            DB::table('market_calendar')->insertOrIgnore($chunk);
        }
    }
}
