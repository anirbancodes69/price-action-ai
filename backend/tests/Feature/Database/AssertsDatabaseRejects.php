<?php

namespace Tests\Feature\Database;

use Illuminate\Database\QueryException;
use Illuminate\Support\Facades\DB;

/** Constraint tests: the statement must fail inside the database, whatever the application does. */
trait AssertsDatabaseRejects
{
    private function assertRejected(callable $statement): void
    {
        try {
            DB::transaction($statement);
        } catch (QueryException) {
            $this->addToAssertionCount(1);

            return;
        }
        $this->fail('Expected the database to reject the statement.');
    }
}
