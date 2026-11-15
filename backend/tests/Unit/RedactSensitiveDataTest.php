<?php

namespace Tests\Unit;

use App\Logging\RedactSensitiveData;
use DateTimeImmutable;
use Monolog\Level;
use Monolog\LogRecord;
use PHPUnit\Framework\TestCase;

class RedactSensitiveDataTest extends TestCase
{
    public function test_redacts_nested_sensitive_keys_and_keeps_others(): void
    {
        $record = new LogRecord(
            datetime: new DateTimeImmutable,
            channel: 'test',
            level: Level::Info,
            message: 'provider_connected',
            context: [
                'access_token' => 'secret-value',
                'connection' => ['api_key' => 'k', 'Authorization' => 'Bearer x', 'provider' => 'ZERODHA_KITE'],
                'request_id' => 'req-1',
            ],
        );

        $out = (new RedactSensitiveData)($record);

        $this->assertSame(RedactSensitiveData::REDACTED, $out->context['access_token']);
        $this->assertSame(
            ['api_key' => RedactSensitiveData::REDACTED, 'Authorization' => RedactSensitiveData::REDACTED, 'provider' => 'ZERODHA_KITE'],
            $out->context['connection'],
        );
        $this->assertSame('req-1', $out->context['request_id']);
    }
}
