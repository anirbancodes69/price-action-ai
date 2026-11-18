<?php

namespace App\Services;

use App\Support\ApiException;
use Illuminate\Support\Facades\DB;

/**
 * Reads parameters of the ACTIVE ruleset from `ruleset_versions` (seeded from the engine's ruleset file).
 * Laravel never decides trading rules; it only needs a few values to build requests (e.g. the entry-cutoff
 * offset for the session clock) and to show defaults.
 */
class RulesetParameters
{
    /** @var array{code: string, version: string, parameters: array<string, mixed>}|null */
    private ?array $active = null;

    /** @return array{code: string, version: string, parameters: array<string, mixed>} */
    public function active(): array
    {
        if ($this->active === null) {
            $row = DB::table('ruleset_versions')->where('status', 'ACTIVE')->orderByDesc('activated_at')->first();
            if ($row === null) {
                throw new ApiException('RULESET_UNAVAILABLE', 'No active ruleset is configured.', 409);
            }
            $params = json_decode((string) $row->parameters, true);
            $this->active = [
                'code' => $row->ruleset_code, 'version' => $row->version, 'parameters' => is_array($params) ? $params : [],
            ];
        }

        return $this->active;
    }

    public function version(): string
    {
        return $this->active()['version'];
    }

    public function get(string $key): mixed
    {
        $params = $this->active()['parameters'];
        if (! array_key_exists($key, $params)) {
            throw new ApiException('RULESET_UNAVAILABLE', "The active ruleset has no parameter {$key}.", 409);
        }

        return $params[$key];
    }
}
