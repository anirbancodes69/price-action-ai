<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/*
 * ARC-03 §2: citext (case-insensitive emails/slugs), btree_gist (exclusion constraints on uuid + ranges),
 * pgcrypto. Production creates them in infrastructure/docker/postgres/init; this keeps CI and fresh
 * databases working. All three are "trusted" extensions, so the database owner may create them.
 * Sorts before create_users_table on purpose.
 */
return new class extends Migration
{
    public function up(): void
    {
        DB::unprepared('CREATE EXTENSION IF NOT EXISTS citext');
        DB::unprepared('CREATE EXTENSION IF NOT EXISTS btree_gist');
        DB::unprepared('CREATE EXTENSION IF NOT EXISTS pgcrypto');
    }

    public function down(): void
    {
        // Extensions are shared database infrastructure; never dropped by a rollback.
    }
};
