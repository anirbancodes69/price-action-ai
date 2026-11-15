<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;

/* ARC-03 §4.1, §4.3–§4.6: tenants, memberships, profiles, onboarding progress, audit log. */
return new class extends Migration
{
    public function up(): void
    {
        DB::unprepared(<<<'SQL'
            CREATE TABLE tenants (
                id uuid PRIMARY KEY,
                name text NOT NULL,
                slug citext NOT NULL,
                kind text NOT NULL,
                status text NOT NULL DEFAULT 'ACTIVE',
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_tenants__slug UNIQUE (slug),
                CONSTRAINT ck_tenants__kind CHECK (kind IN ('PERSONAL', 'ORGANIZATION')),
                CONSTRAINT ck_tenants__status CHECK (status IN ('ACTIVE', 'SUSPENDED', 'CLOSED'))
            );

            -- Roles are a fixed enum; no roles/permissions tables in MVP (ARC-03 §4.3).
            CREATE TABLE tenant_memberships (
                id uuid PRIMARY KEY,
                tenant_id uuid NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
                user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
                role text NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT uq_tenant_memberships__tenant_id_user_id UNIQUE (tenant_id, user_id),
                CONSTRAINT ck_tenant_memberships__role CHECK (role IN ('OWNER', 'ADMIN', 'MEMBER', 'VIEWER'))
            );
            CREATE INDEX ix_tenant_memberships__user_id ON tenant_memberships (user_id);

            CREATE TABLE user_profiles (
                user_id uuid PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
                display_name text NOT NULL,
                experience_level text NULL,
                timezone text NOT NULL DEFAULT 'Asia/Kolkata',
                locale text NOT NULL DEFAULT 'en-IN',
                updated_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT ck_user_profiles__experience_level
                    CHECK (experience_level IS NULL OR experience_level IN ('NEW', 'INTERMEDIATE', 'ADVANCED'))
            );

            -- Progress only; answers live in their owning tables (PRD-05).
            CREATE TABLE onboarding_progress (
                user_id uuid PRIMARY KEY REFERENCES users (id),
                tenant_id uuid NOT NULL REFERENCES tenants (id),
                flow_version smallint NOT NULL DEFAULT 1,
                status text NOT NULL DEFAULT 'NOT_STARTED',
                current_step text NOT NULL DEFAULT 'WELCOME',
                completed_steps text[] NOT NULL DEFAULT '{}',
                skipped_steps text[] NOT NULL DEFAULT '{}',
                started_at timestamptz NULL,
                completed_at timestamptz NULL,
                updated_at timestamptz NOT NULL DEFAULT now(),
                CONSTRAINT ck_onboarding_progress__status CHECK (status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED')),
                CONSTRAINT ck_onboarding_progress__current_step
                    CHECK (current_step IN ('WELCOME', 'EXPERIENCE', 'STYLE', 'UNIVERSE', 'DATA_SOURCE', 'RISK', 'DONE'))
            );
            CREATE INDEX ix_onboarding_progress__tenant_id ON onboarding_progress (tenant_id);

            -- Append-only (ARC-03 §4.6). Partitioning is deferred until volume justifies it.
            CREATE TABLE audit_logs (
                id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                occurred_at timestamptz NOT NULL DEFAULT now(),
                tenant_id uuid NULL,
                actor_type text NOT NULL,
                actor_id uuid NULL,
                action text NOT NULL,
                entity_type text NULL,
                entity_id uuid NULL,
                request_id text NULL,
                ip inet NULL,
                user_agent text NULL,
                changes jsonb NULL,
                metadata jsonb NULL,
                CONSTRAINT ck_audit_logs__actor_type CHECK (actor_type IN ('USER', 'SYSTEM', 'SERVICE'))
            );
            CREATE INDEX ix_audit_logs__tenant_id_occurred_at ON audit_logs (tenant_id, occurred_at DESC);
            CREATE INDEX ix_audit_logs__entity ON audit_logs (entity_type, entity_id);

            -- Runtime roles are created by infrastructure/docker/postgres/init; absent in CI.
            DO $$
            DECLARE r text;
            BEGIN
                FOREACH r IN ARRAY ARRAY['app_backend', 'app_engine'] LOOP
                    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                        EXECUTE format('REVOKE UPDATE, DELETE, TRUNCATE ON audit_logs FROM %I', r);
                    END IF;
                END LOOP;
            END
            $$;
            SQL);
    }

    public function down(): void
    {
        DB::unprepared('DROP TABLE IF EXISTS audit_logs, onboarding_progress, user_profiles, tenant_memberships, tenants');
    }
};
