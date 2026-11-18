<?php

use App\Http\Middleware\RequestId;
use App\Support\ApiException;
use App\Support\ApiResponse;
use Illuminate\Auth\AuthenticationException;
use Illuminate\Database\Eloquent\ModelNotFoundException;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Exceptions\ThrottleRequestsException;
use Illuminate\Http\Request;
use Illuminate\Session\TokenMismatchException;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpKernel\Exception\HttpException;
use Symfony\Component\HttpKernel\Exception\NotFoundHttpException;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        api: __DIR__.'/../routes/api.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        // SPA cookie auth (Sanctum): requests from the frontend origin are stateful and CSRF-protected.
        $middleware->statefulApi();
        $middleware->api(prepend: [RequestId::class]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        $exceptions->shouldRenderJsonWhen(
            fn (Request $request) => $request->is('api/*') || $request->expectsJson(),
        );

        // API error envelope (docs/architecture/04_API_SPECIFICATION.md §2.5).
        $isApi = fn (Request $request): bool => $request->is('api/*');
        $exceptions->render(fn (ApiException $e, Request $r) => $isApi($r)
            ? ApiResponse::error($e->errorCode, $e->getMessage(), $e->status, $e->details) : null);
        $exceptions->render(fn (AuthenticationException $e, Request $r) => $isApi($r)
            ? ApiResponse::error('UNAUTHENTICATED', 'Authentication required.', 401) : null);
        $exceptions->render(fn (ValidationException $e, Request $r) => $isApi($r)
            ? ApiResponse::error('VALIDATION_FAILED', 'The request is invalid.', 422, ['field_errors' => $e->errors()]) : null);
        // 419: a missing or wrong CSRF token (TokenMismatchException) or a cross-site origin (HttpException 419).
        $exceptions->render(fn (TokenMismatchException $e, Request $r) => $isApi($r)
            ? ApiResponse::error('CSRF_TOKEN_MISMATCH', 'CSRF token mismatch.', 419) : null);
        $exceptions->render(fn (HttpException $e, Request $r) => $isApi($r) && $e->getStatusCode() === 419
            ? ApiResponse::error('CSRF_TOKEN_MISMATCH', 'CSRF token mismatch.', 419) : null);
        $exceptions->render(fn (ThrottleRequestsException $e, Request $r) => $isApi($r)
            ? ApiResponse::error('RATE_LIMITED', 'Too many requests.', 429, [], array_intersect_key(
                $e->getHeaders(), ['Retry-After' => 1, 'X-RateLimit-Limit' => 1, 'X-RateLimit-Remaining' => 1],
            )) : null);
        $exceptions->render(fn (NotFoundHttpException|ModelNotFoundException $e, Request $r) => $isApi($r)
            ? ApiResponse::error('NOT_FOUND', 'Resource not found.', 404) : null);
    })->create();
