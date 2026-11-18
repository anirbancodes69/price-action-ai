<?php

namespace App\Support;

use RuntimeException;

/**
 * A domain error that renders as the API error envelope (docs/architecture/04_API_SPECIFICATION.md §2.5):
 * `{error: {code, message, details?, request_id}}`.
 */
class ApiException extends RuntimeException
{
    /** @param  array<string, mixed>  $details */
    public function __construct(
        public readonly string $errorCode,
        string $message,
        public readonly int $status,
        public readonly array $details = [],
    ) {
        parent::__construct($message);
    }
}
