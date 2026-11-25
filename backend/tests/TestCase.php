<?php

namespace Tests;

use Illuminate\Foundation\Application;
use Illuminate\Foundation\Testing\TestCase as BaseTestCase;
use Illuminate\Support\Facades\DB;
use Tests\Support\DatabaseGuard;

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

        $app = parent::createApplication();

        // Fail closed before any connection: the resolved default connection must be an approved test database.
        $config = $app->make('config');
        DatabaseGuard::assertConnectionConfig((array) $config->get('database.connections.'.$config->get('database.default')));

        return $app;
    }

    /**
     * Runs before any test trait is set up: `RefreshDatabase` (which runs `migrate:fresh`), seeding, transactions.
     * So the live connection is verified before migrations, fixtures, cleanup or writes. (A hook named
     * `beforeRefreshingDatabase` on this class would be shadowed by the trait's own empty method.)
     */
    protected function setUpTraits()
    {
        $this->assertLiveTestDatabase();

        return parent::setUpTraits();
    }

    private function assertLiveTestDatabase(): void
    {
        $row = DB::selectOne('select current_database() as db, current_user as role');
        DatabaseGuard::assertLive((string) $row->db, (string) $row->role);
    }
}
