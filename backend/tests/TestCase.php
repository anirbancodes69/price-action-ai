<?php

namespace Tests;

use Illuminate\Foundation\Application;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;

abstract class TestCase extends BaseTestCase
{
    /**
     * phpunit.xml asks for array cache and session, but a real environment variable wins over it, and the
     * Compose service sets `CACHE_STORE=redis` and `SESSION_DRIVER=redis`. Setting them before the application
     * boots keeps tests (and the rate limiter, which binds its store at boot) off the dev Redis.
     */
    public function createApplication(): Application
    {
        foreach (['CACHE_STORE' => 'array', 'SESSION_DRIVER' => 'array', 'QUEUE_CONNECTION' => 'sync'] as $key => $value) {
            putenv("{$key}={$value}");
            $_ENV[$key] = $_SERVER[$key] = $value;
        }

        return parent::createApplication();
    }
}
