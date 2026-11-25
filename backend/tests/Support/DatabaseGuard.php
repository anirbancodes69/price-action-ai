<?php

namespace Tests\Support;

/**
 * Fail-closed guard for the PHPUnit suite (D0, DR-6).
 *
 * `RefreshDatabase` runs `migrate:fresh`, which drops every table of the connected database. That must never
 * happen to the development database, so the target is checked at three points, each before anything is
 * written: the process environment (tests/bootstrap.php, before the application boots), the resolved
 * connection configuration (TestCase::createApplication, before any connection), and the live connection
 * (TestCase::setUpTraits, before any test trait: migrations, seeding, cleanup). Messages carry only database and role
 * names, never a password or URL.
 *
 * Approved: PostgreSQL, a database named `priceaction_test` optionally followed by `_` and lowercase letters
 * or digits, reached as a named role that is not a live application or administrative role, with `DB_URL`
 * empty. An unset value is a refusal: the target must be stated explicitly.
 */
final class DatabaseGuard
{
    public const APPROVED_DATABASE = '/^priceaction_test(_[a-z0-9]+)*$/';

    /** Roles that run the live application, own the development schema, or administer the cluster. */
    public const FORBIDDEN_ROLES = ['postgres', 'app_backend', 'app_engine', 'app_migrator'];

    /**
     * The values the framework would use, read from the real process environment.
     *
     * @return array<string, string>
     */
    public static function processEnvironment(): array
    {
        $values = [];
        foreach (['DB_CONNECTION', 'DB_URL', 'DB_DATABASE', 'DB_USERNAME'] as $key) {
            $value = getenv($key);
            if ($value === false) {
                $value = $_ENV[$key] ?? $_SERVER[$key] ?? '';
            }
            $values[$key] = is_string($value) ? $value : '';
        }

        return $values;
    }

    /** @param array<string, string> $env */
    public static function assertEnvironment(array $env): void
    {
        if (($env['DB_CONNECTION'] ?? '') !== 'pgsql') {
            throw new DatabaseGuardException('DB_CONNECTION must be set to pgsql: only PostgreSQL test databases are approved');
        }
        if (($env['DB_URL'] ?? '') !== '') {
            throw new DatabaseGuardException('DB_URL must be empty: a URL could change the target database');
        }
        self::assertTarget($env['DB_DATABASE'] ?? '', $env['DB_USERNAME'] ?? '');
    }

    /** @param array<string, mixed> $connection a resolved `database.connections.*` configuration */
    public static function assertConnectionConfig(array $connection): void
    {
        if (($connection['driver'] ?? '') !== 'pgsql') {
            throw new DatabaseGuardException('the default connection must use the pgsql driver');
        }
        if (! empty($connection['url'])) {
            throw new DatabaseGuardException('the connection configuration carries a URL that could change the target database');
        }
        self::assertTarget((string) ($connection['database'] ?? ''), (string) ($connection['username'] ?? ''));
    }

    /** Re-check the live connection's identity (`select current_database(), current_user`). */
    public static function assertLive(string $database, string $role): void
    {
        self::assertTarget($database, $role);
    }

    public static function assertTarget(string $database, string $role): void
    {
        if ($database === '') {
            throw new DatabaseGuardException('DB_DATABASE is not set: the test database must be named explicitly');
        }
        if (preg_match(self::APPROVED_DATABASE, $database) !== 1) {
            throw new DatabaseGuardException("database '{$database}' is not an approved test database");
        }
        if ($role === '') {
            throw new DatabaseGuardException('DB_USERNAME is not set: the dedicated test role must be named explicitly');
        }
        if (in_array($role, self::FORBIDDEN_ROLES, true)) {
            throw new DatabaseGuardException("role '{$role}' is a live application, schema-owner or administrative role");
        }
    }
}
