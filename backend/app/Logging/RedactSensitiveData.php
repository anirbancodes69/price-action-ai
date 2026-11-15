<?php

namespace App\Logging;

use Monolog\LogRecord;
use Monolog\Processor\ProcessorInterface;

/**
 * Redacts values whose keys look sensitive from log context and extra
 * (docs/engineering/06_ERROR_HANDLING_AND_LOGGING.md §5). Mirrors app/logging.py in the engine.
 */
class RedactSensitiveData implements ProcessorInterface
{
    public const REDACTED = '[REDACTED]';

    private const PATTERN = '/(pass(word)?|secret|token|authorization|cookie|api[_-]?key|request_token|access_token)/i';

    public function __invoke(LogRecord $record): LogRecord
    {
        return $record->with(
            context: $this->redact($record->context),
            extra: $this->redact($record->extra),
        );
    }

    /**
     * @param  array<array-key, mixed>  $data
     * @return array<array-key, mixed>
     */
    public function redact(array $data): array
    {
        foreach ($data as $key => $value) {
            if (is_string($key) && preg_match(self::PATTERN, $key)) {
                $data[$key] = self::REDACTED;
            } elseif (is_array($value)) {
                $data[$key] = $this->redact($value);
            }
        }

        return $data;
    }
}
