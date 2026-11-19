<?php

use App\Http\Controllers\Api\V1\ActualTradeController;
use App\Http\Controllers\Api\V1\AnalysisController;
use App\Http\Controllers\Api\V1\AuthController;
use App\Http\Controllers\Api\V1\JournalController;
use App\Http\Controllers\Api\V1\MeController;
use App\Http\Controllers\Api\V1\PositionController;
use App\Http\Controllers\Api\V1\RiskController;
use App\Http\Controllers\Api\V1\RiskProfileController;
use App\Http\Controllers\Api\V1\RiskTodayController;
use App\Http\Controllers\Api\V1\ScannerController;
use App\Http\Controllers\Api\V1\WatchlistController;
use App\Http\Controllers\HealthController;
use Illuminate\Support\Facades\Route;

// Public REST API (docs/architecture/04_API_SPECIFICATION.md). Personal-mode subset (ADR-014, ADR-016).
Route::get('/health', HealthController::class)->name('health');

Route::prefix('v1')->name('v1.')->group(function () {
    Route::post('/auth/login', [AuthController::class, 'login'])->middleware('throttle:auth')->name('auth.login');

    Route::middleware('auth:sanctum')->group(function () {
        Route::post('/auth/logout', [AuthController::class, 'logout'])->name('auth.logout');
        Route::get('/me', [MeController::class, 'show'])->name('me');
        Route::get('/scanner', [ScannerController::class, 'index'])->middleware('throttle:read')->name('scanner');
        Route::get('/analysis/{symbol}', [AnalysisController::class, 'show'])->middleware('throttle:read')->name('analysis.show');
        Route::get('/actual-trades', [ActualTradeController::class, 'index'])->middleware('throttle:read')->name('actual-trades.index');
        Route::post('/actual-trades', [ActualTradeController::class, 'store'])->middleware('throttle:calc')->name('actual-trades.store');
        Route::patch('/actual-trades/{id}', [ActualTradeController::class, 'levels'])->whereUuid('id')->middleware('throttle:calc')->name('actual-trades.levels');
        Route::post('/actual-trades/{id}/fills', [ActualTradeController::class, 'fill'])->whereUuid('id')->middleware('throttle:calc')->name('actual-trades.fill');
        Route::get('/positions/live', [PositionController::class, 'live'])->middleware('throttle:read')->name('positions.live');
        Route::get('/risk/today', [RiskTodayController::class, 'show'])->middleware('throttle:read')->name('risk.today');
        Route::get('/journal', [JournalController::class, 'index'])->middleware('throttle:read')->name('journal.index');
        Route::get('/journal/{id}', [JournalController::class, 'show'])->whereUuid('id')->middleware('throttle:read')->name('journal.show');
        Route::patch('/journal/{id}', [JournalController::class, 'update'])->whereUuid('id')->middleware('throttle:calc')->name('journal.update');
        Route::get('/risk-profile', [RiskProfileController::class, 'show'])->middleware('throttle:read')->name('risk-profile.show');
        Route::put('/risk-profile', [RiskProfileController::class, 'update'])->middleware('throttle:calc')->name('risk-profile.update');
        Route::get('/watchlists', [WatchlistController::class, 'index'])->middleware('throttle:read')->name('watchlists.index');
        Route::post('/watchlists', [WatchlistController::class, 'store'])->middleware('throttle:calc')->name('watchlists.store');
        Route::patch('/watchlists/{id}', [WatchlistController::class, 'update'])->whereUuid('id')->middleware('throttle:calc')->name('watchlists.update');
        Route::delete('/watchlists/{id}', [WatchlistController::class, 'destroy'])->whereUuid('id')->middleware('throttle:calc')->name('watchlists.destroy');
        Route::put('/watchlists/{id}/items/{symbol}', [WatchlistController::class, 'addItem'])->whereUuid('id')->middleware('throttle:calc')->name('watchlists.items.add');
        Route::delete('/watchlists/{id}/items/{symbol}', [WatchlistController::class, 'removeItem'])->whereUuid('id')->middleware('throttle:calc')->name('watchlists.items.remove');
        Route::post('/risk/calculate', [RiskController::class, 'calculate'])->middleware('throttle:calc')->name('risk.calculate');
    });
});
