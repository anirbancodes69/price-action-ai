<?php

use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Schedule;

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');

// Plans past their entry cutoff (TRD-07 §3); idempotent, so a missed run is caught by the next.
Schedule::command('plans:expire')->everyFiveMinutes()->withoutOverlapping();
