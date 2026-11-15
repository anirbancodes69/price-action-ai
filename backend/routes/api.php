<?php

use App\Http\Controllers\HealthController;
use Illuminate\Support\Facades\Route;

// Public REST API (docs/architecture/04_API_SPECIFICATION.md). Versioned endpoints arrive in M6.
Route::get('/health', HealthController::class)->name('health');

Route::prefix('v1')->name('v1.')->group(function () {
    // M6: auth, onboarding, preferences, scanner, analysis, plans, ...
});
