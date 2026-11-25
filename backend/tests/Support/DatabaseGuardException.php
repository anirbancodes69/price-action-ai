<?php

namespace Tests\Support;

use RuntimeException;

/** The test suite was pointed at a database that is not an approved test database. */
final class DatabaseGuardException extends RuntimeException {}
