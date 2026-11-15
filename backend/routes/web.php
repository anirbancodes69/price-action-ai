<?php

use Illuminate\Support\Facades\Route;

// API-only backend: the browser UI is the Next.js frontend. See docs/architecture/04_API_SPECIFICATION.md.
Route::get('/', fn () => response()->json([
    'service' => 'priceaction-backend',
    'api' => '/api/v1',
]));
