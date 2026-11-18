<?php

namespace App\Support;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/** Builders for the API response envelopes: `{data, meta}` and `{error}`. */
final class ApiResponse
{
    public static function requestId(?Request $request = null): string
    {
        $request ??= request();

        return (string) ($request->attributes->get('request_id') ?? $request->headers->get('X-Request-Id', ''));
    }

    /**
     * @param  array<string, mixed>|list<mixed>  $data
     * @param  array<string, mixed>  $meta
     */
    public static function ok(array $data, array $meta = [], int $status = 200): JsonResponse
    {
        return response()->json(['data' => $data, 'meta' => ['request_id' => self::requestId()] + $meta], $status);
    }

    /**
     * @param  array<string, mixed>  $details
     * @param  array<string, string>  $headers
     */
    public static function error(string $code, string $message, int $status, array $details = [], array $headers = []): JsonResponse
    {
        $body = ['code' => $code, 'message' => $message];
        if ($details !== []) {
            $body['details'] = $details;
        }
        $body['request_id'] = self::requestId();

        return response()->json(['error' => $body], $status, $headers);
    }
}
