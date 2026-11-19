<?php

use App\Http\Controllers\Api\V1\ActualTradeController;
use App\Http\Controllers\Api\V1\AnalysisController;
use App\Http\Controllers\Api\V1\AuthController;
use App\Http\Controllers\Api\V1\MeController;
use App\Http\Controllers\Api\V1\PositionController;
use App\Http\Controllers\Api\V1\RiskController;
use App\Http\Controllers\Api\V1\RiskTodayController;
use App\Http\Controllers\Api\V1\ScannerController;
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
        Route::post('/actual-trades/{id}/fills', [ActualTradeController::class, 'fill'])->whereUuid('id')->middleware('throttle:calc')->name('actual-trades.fill');
        Route::get('/positions/live', [PositionController::class, 'live'])->middleware('throttle:read')->name('positions.live');
        Route::get('/risk/today', [RiskTodayController::class, 'show'])->middleware('throttle:read')->name('risk.today');
        Route::post('/risk/calculate', [RiskController::class, 'calculate'])->middleware('throttle:calc')->name('risk.calculate');
    });
});
