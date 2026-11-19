<?php

namespace App\Services;

use App\Models\User;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/** The owner's personal tenant, created on first use (personal mode has exactly one, ADR-014). */
class PersonalTenant
{
    public function idFor(User $user): string
    {
        $existing = DB::table('tenant_memberships')->where('user_id', $user->getKey())->value('tenant_id');
        if ($existing !== null) {
            return (string) $existing;
        }
        $id = (string) Str::uuid7();
        DB::table('tenants')->insert(['id' => $id, 'name' => 'Personal', 'slug' => 'personal-'.substr(str_replace('-', '', (string) $user->getKey()), 0, 12), 'kind' => 'PERSONAL']);
        DB::table('tenant_memberships')->insert(['id' => (string) Str::uuid7(), 'tenant_id' => $id, 'user_id' => $user->getKey(), 'role' => 'OWNER']);

        return $id;
    }
}
