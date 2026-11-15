<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/*
 * ARC-03 §4.2 users + Laravel's password_reset_tokens. Replaces the stock Laravel migration
 * (nothing is deployed yet). Sessions live in Redis, so there is no sessions table.
 * IDs are application-generated UUIDv7 (HasUuids).
 */
return new class extends Migration
{
    public function up(): void
    {
        DB::unprepared(<<<'SQL'
            CREATE TABLE users (
                id uuid PRIMARY KEY,
                email citext NOT NULL,
                password text NOT NULL,
                email_verified_at timestamptz NULL,
                status text NOT NULL DEFAULT 'ACTIVE',
                is_platform_admin boolean NOT NULL DEFAULT false,
                last_login_at timestamptz NULL,
                remember_token varchar(100) NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                deleted_at timestamptz NULL,
                CONSTRAINT uq_users__email UNIQUE (email),
                CONSTRAINT ck_users__status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'DELETED'))
            );

            CREATE TABLE password_reset_tokens (
                email citext PRIMARY KEY,
                token text NOT NULL,
                created_at timestamptz NULL
            );
            SQL);
    }

    public function down(): void
    {
        DB::unprepared('DROP TABLE IF EXISTS password_reset_tokens, users');
    }
};
