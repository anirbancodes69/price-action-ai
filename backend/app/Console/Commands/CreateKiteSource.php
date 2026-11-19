<?php

namespace App\Console\Commands;

use App\Models\User;
use App\Services\PersonalTenant;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * Creates the owner's PERSONAL Zerodha Kite data source and its provider connection (ARC-08 §4.1).
 *
 * The in-app connect flow is not built: the Kite token lives in a local file written by `scripts/kite_login.py`
 * (OQ-INT-05). That shortcut skipped the rows the flow would have created, and nothing could be ingested or served
 * without them (a PERSONAL data source requires a tenant and a provider connection). No token is stored here: the
 * connection is marked CONNECTED with an empty token column and the id of the local token file as its provider user.
 * The tables are Laravel's (single writer), so this is an artisan command and not an engine script.
 */
class CreateKiteSource extends Command
{
    protected $signature = 'source:create-kite {email? : The owner\'s login email (default: the only user)}';

    protected $description = 'Create the PERSONAL Kite data source for the owner (idempotent) and print its id';

    public const PROVIDER_USER = 'local-token-file';

    public function handle(PersonalTenant $tenants): int
    {
        $email = $this->argument('email');
        $users = User::query()->when($email, fn ($q) => $q->where('email', mb_strtolower((string) $email)))->get();
        if ($users->count() !== 1) {
            $this->error($users->isEmpty() ? 'No such user. Create the owner first: php artisan owner:create <email>' : 'More than one user: pass the owner\'s email.');

            return self::FAILURE;
        }
        /** @var User $user */
        $user = $users->first();
        $tenant = $tenants->idFor($user);

        $existing = DB::table('data_sources')->where('tenant_id', $tenant)->where('mode', 'PERSONAL')->where('provider', 'ZERODHA_KITE')->value('id');
        $id = $existing !== null ? (string) $existing : DB::transaction(fn () => $this->create($user, $tenant));

        DB::table('data_source_selections')->updateOrInsert(
            ['tenant_id' => $tenant],
            ['data_source_id' => $id, 'selected_by' => $user->getKey(), 'selected_at' => now()],
        );

        $this->info($existing !== null ? 'The Kite data source already exists.' : 'Created the PERSONAL Kite data source.');
        $this->line("Data source id: {$id}");
        $this->line('Put it in .env as INGEST_DATA_SOURCE_ID (the engine writes bars for it; Compose passes the same id to the API as ENGINE_DATA_SOURCE_ID), then restart the stack.');

        return self::SUCCESS;
    }

    private function create(User $user, string $tenant): string
    {
        $connection = (string) Str::uuid7();
        DB::table('provider_connections')->insert([
            'id' => $connection, 'tenant_id' => $tenant, 'user_id' => $user->getKey(), 'provider' => 'ZERODHA_KITE',
            'provider_user_id' => self::PROVIDER_USER, 'status' => 'CONNECTED', 'access_token_encrypted' => null, 'last_connected_at' => now(),
        ]);
        $id = (string) Str::uuid7();
        DB::table('data_sources')->insert([
            'id' => $id, 'mode' => 'PERSONAL', 'provider' => 'ZERODHA_KITE', 'tenant_id' => $tenant,
            'provider_connection_id' => $connection, 'name' => 'Zerodha Kite (personal)',
        ]);

        return $id;
    }
}
