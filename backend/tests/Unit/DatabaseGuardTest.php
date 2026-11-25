<?php

namespace Tests\Unit;

use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;
use Tests\Support\DatabaseGuard;
use Tests\Support\DatabaseGuardException;

/** The fail-closed database guard (D0). Pure: no application, no database, no connection. */
class DatabaseGuardTest extends TestCase
{
    private const GOOD = ['DB_CONNECTION' => 'pgsql', 'DB_URL' => '', 'DB_DATABASE' => 'priceaction_test', 'DB_USERNAME' => 'app_test_schema'];

    /** @param array<string, string> $overrides */
    private function env(array $overrides = []): array
    {
        return array_merge(self::GOOD, $overrides);
    }

    public function test_the_approved_environment_passes(): void
    {
        DatabaseGuard::assertEnvironment(self::GOOD);
        DatabaseGuard::assertEnvironment($this->env(['DB_USERNAME' => 'ci']));  // the CI role
        DatabaseGuard::assertEnvironment($this->env(['DB_DATABASE' => 'priceaction_test_ci1']));
        $this->addToAssertionCount(1);
    }

    #[DataProvider('refusedDatabases')]
    public function test_other_databases_are_refused(string $database): void
    {
        $this->expectException(DatabaseGuardException::class);
        DatabaseGuard::assertEnvironment($this->env(['DB_DATABASE' => $database]));
    }

    /** @return array<string, array{string}> */
    public static function refusedDatabases(): array
    {
        return [
            'the development database' => ['priceaction'],
            'postgres' => ['postgres'],
            'unset' => [''],
            'suffix without separator' => ['priceaction_testx'],
            'trailing underscore' => ['priceaction_test_'],
            'upper case' => ['Priceaction_Test'],
            'hyphen' => ['priceaction-test'],
            'digit suffix without separator' => ['priceaction_test2'],
            'prefixed' => ['xpriceaction_test'],
            'laravel default' => ['laravel'],
        ];
    }

    #[DataProvider('refusedRoles')]
    public function test_live_application_and_administrative_roles_are_refused_even_for_a_test_database(string $role): void
    {
        $this->expectException(DatabaseGuardException::class);
        DatabaseGuard::assertEnvironment($this->env(['DB_USERNAME' => $role]));
    }

    /** @return array<string, array{string}> */
    public static function refusedRoles(): array
    {
        return ['superuser' => ['postgres'], 'backend' => ['app_backend'], 'engine' => ['app_engine'], 'schema owner' => ['app_migrator'], 'unset' => ['']];
    }

    public function test_a_url_or_another_driver_is_refused(): void
    {
        foreach ([['DB_URL' => 'postgresql://u:p@h/priceaction'], ['DB_CONNECTION' => 'sqlite'], ['DB_CONNECTION' => 'mysql'], ['DB_CONNECTION' => '']] as $bad) {
            try {
                DatabaseGuard::assertEnvironment($this->env($bad));
                $this->fail('expected a refusal for '.json_encode(array_keys($bad)));
            } catch (DatabaseGuardException) {
                $this->addToAssertionCount(1);
            }
        }
    }

    public function test_the_resolved_connection_configuration_is_checked(): void
    {
        DatabaseGuard::assertConnectionConfig(['driver' => 'pgsql', 'url' => null, 'database' => 'priceaction_test', 'username' => 'app_test_schema']);
        foreach ([
            ['driver' => 'pgsql', 'database' => 'priceaction', 'username' => 'app_test_schema'],
            ['driver' => 'pgsql', 'database' => 'priceaction_test', 'username' => 'app_backend'],
            ['driver' => 'pgsql', 'url' => 'postgresql://x', 'database' => 'priceaction_test', 'username' => 'app_test_schema'],
            ['driver' => 'sqlite', 'database' => 'priceaction_test', 'username' => 'app_test_schema'],
            ['driver' => 'pgsql', 'username' => 'app_test_schema'],
        ] as $bad) {
            try {
                DatabaseGuard::assertConnectionConfig($bad);
                $this->fail('expected a refusal for '.json_encode($bad));
            } catch (DatabaseGuardException) {
                $this->addToAssertionCount(1);
            }
        }
    }

    public function test_the_live_identity_check_refuses_the_development_database_and_live_roles(): void
    {
        DatabaseGuard::assertLive('priceaction_test', 'app_test_schema');
        foreach ([['priceaction', 'app_test_schema'], ['priceaction_test', 'app_backend'], ['postgres', 'app_test_schema'], ['priceaction_test', 'postgres']] as [$database, $role]) {
            try {
                DatabaseGuard::assertLive($database, $role);
                $this->fail("expected a refusal for {$database}/{$role}");
            } catch (DatabaseGuardException) {
                $this->addToAssertionCount(1);
            }
        }
    }

    public function test_messages_never_contain_a_password_or_url(): void
    {
        $secret = 's3cr3t-pa55';
        try {
            DatabaseGuard::assertEnvironment($this->env(['DB_URL' => "postgresql://app_backend:{$secret}@h/priceaction"]));
            $this->fail('expected a refusal');
        } catch (DatabaseGuardException $e) {
            $this->assertStringNotContainsString($secret, $e->getMessage());
        }
    }

    public function test_the_wiring_cannot_be_removed_silently(): void
    {
        $root = dirname(__DIR__, 2);
        $this->assertStringContainsString('bootstrap="tests/bootstrap.php"', (string) file_get_contents($root.'/phpunit.xml'));
        $bootstrap = (string) file_get_contents($root.'/tests/bootstrap.php');
        $this->assertStringContainsString('assertEnvironment', $bootstrap);
        $this->assertStringContainsString('exit(2)', $bootstrap);
        $case = (string) file_get_contents($root.'/tests/TestCase.php');
        foreach (['assertConnectionConfig', 'setUpTraits', 'assertLive'] as $needle) {
            $this->assertStringContainsString($needle, $case);
        }
    }
}
