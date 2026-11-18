<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use Ramsey\Uuid\Uuid;
use RuntimeException;

/**
 * Seeds the ruleset versions (TRD-01 §6, ARC-03 §7.1). `pa-intraday 0.1.0` is the active ruleset (ADR-014);
 * `pa-core 0.1.0` (the daily scope) is kept as RETIRED. Parameters are all HYPOTHESIS.
 *
 * A row that already exists keeps its content (an ACTIVE or RETIRED ruleset is immutable; any change of values is
 * a new version). The only update is moving a still-ACTIVE `pa-core` row to RETIRED, which the content trigger allows.
 * Parameter files: `data/<code>-<version>.json`, byte-identical to `python-engine/rulesets/<code>/<version>.json`
 * (checked by `contracts/scripts/check_ruleset_hash.py`).
 */
class RulesetSeeder extends Seeder
{
    public const NAMESPACE_UUID = '6f0c2b1e-5a43-4d6e-9c1f-3b7a8e2d4c10';

    /** @var list<array{code: string, version: string, score_version: string, status: string}> */
    public const RULESETS = [
        ['code' => 'pa-core', 'version' => '0.1.0', 'score_version' => 'paqs-0.1.0', 'status' => 'RETIRED'],
        ['code' => 'pa-intraday', 'version' => '0.1.0', 'score_version' => 'paqs-intraday-0.1.0', 'status' => 'ACTIVE'],
    ];

    public const ACTIVE_CODE = 'pa-intraday';

    public static function parameters(string $code = 'pa-core', string $version = '0.1.0'): array
    {
        $path = __DIR__."/data/{$code}-{$version}.json";
        $decoded = json_decode((string) file_get_contents($path), true, flags: JSON_THROW_ON_ERROR);
        if (! is_array($decoded)) {
            throw new RuntimeException("Ruleset file {$path} must contain a JSON object.");
        }
        ksort($decoded);

        return $decoded;
    }

    /** Canonical JSON: sorted keys, no whitespace, unescaped slashes and unicode, floats keep ".0" (as Python json.dumps). */
    public static function canonicalJson(array $parameters): string
    {
        return json_encode($parameters, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_PRESERVE_ZERO_FRACTION | JSON_THROW_ON_ERROR);
    }

    public static function parametersHash(array $parameters): string
    {
        return hash('sha256', self::canonicalJson($parameters));
    }

    public static function id(string $code, string $version): string
    {
        return Uuid::uuid5(self::NAMESPACE_UUID, $code.':'.$version)->toString();
    }

    public function run(): void
    {
        foreach (self::RULESETS as $r) {
            $parameters = self::parameters($r['code'], $r['version']);
            DB::table('ruleset_versions')->insertOrIgnore([
                'id' => self::id($r['code'], $r['version']),
                'ruleset_code' => $r['code'],
                'version' => $r['version'],
                'parameters' => self::canonicalJson($parameters),
                'parameters_hash' => self::parametersHash($parameters),
                'score_version' => $r['score_version'],
                'status' => $r['status'],
                'validation_status' => 'HYPOTHESIS',
                'activated_at' => now(),
                'retired_at' => $r['status'] === 'RETIRED' ? now() : null,
            ]);
        }

        // Databases seeded before ADR-014 have pa-core ACTIVE.
        DB::table('ruleset_versions')->where(['ruleset_code' => 'pa-core', 'status' => 'ACTIVE'])
            ->update(['status' => 'RETIRED', 'retired_at' => now()]);
    }
}
