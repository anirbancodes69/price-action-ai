<?php

namespace App\Support;

/** Opaque offset cursor for list endpoints (ARC-04 §2.4). */
final class Cursor
{
    public static function encode(int $offset): string
    {
        return rtrim(strtr(base64_encode((string) json_encode(['o' => $offset])), '+/', '-_'), '=');
    }

    public static function decode(string $cursor): int
    {
        if ($cursor === '') {
            return 0;
        }
        $decoded = json_decode((string) base64_decode(strtr($cursor, '-_', '+/'), true), true);
        if (! is_array($decoded) || ! isset($decoded['o']) || ! is_int($decoded['o']) || $decoded['o'] < 0) {
            throw new ApiException('INVALID_CURSOR', 'The cursor is not valid.', 400);
        }

        return $decoded['o'];
    }
}
