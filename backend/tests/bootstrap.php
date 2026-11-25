<?php

use Tests\Support\DatabaseGuard;
use Tests\Support\DatabaseGuardException;

/*
 * PHPUnit bootstrap with a fail-closed database guard (D0, DR-6).
 *
 * Runs before the application boots, before `.env` is read and before any connection: if the process
 * environment does not name an approved test database and role, the run stops here with a non-zero exit
 * status and no test executes.
 */

require __DIR__.'/../vendor/autoload.php';
require_once __DIR__.'/Support/DatabaseGuardException.php';
require_once __DIR__.'/Support/DatabaseGuard.php';

try {
    DatabaseGuard::assertEnvironment(DatabaseGuard::processEnvironment());
} catch (DatabaseGuardException $e) {
    fwrite(STDERR, "\nREFUSING TO RUN THE TEST SUITE: {$e->getMessage()}.\n"
        .'Tests may only run against a database named priceaction_test as a dedicated test role '
        ."(see docs/engineering/08_DEVELOPMENT_ENVIRONMENT.md). No test was executed.\n\n");
    exit(2);
}
