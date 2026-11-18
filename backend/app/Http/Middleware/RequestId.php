<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Symfony\Component\HttpFoundation\Response;

/** Every API request has an id, echoed in `X-Request-Id`, response `meta` and error bodies (ARC-04 §2.4). */
class RequestId
{
    public function handle(Request $request, Closure $next): Response
    {
        $given = (string) $request->headers->get('X-Request-Id', '');
        $id = preg_match('/^[A-Za-z0-9._-]{8,64}$/', $given) === 1 ? $given : (string) Str::uuid();
        $request->attributes->set('request_id', $id);

        $response = $next($request);
        $response->headers->set('X-Request-Id', $id);

        return $response;
    }
}
