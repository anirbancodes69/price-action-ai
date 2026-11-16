<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use Ramsey\Uuid\Uuid;
use RuntimeException;

/**
 * Seeds ruleset `pa-core 0.1.0` (TRD-01 §6, ARC-03 §7.1). Parameters are the registry defaults and are all
 * HYPOTHESIS (not validated). A row that already exists is never modified: an ACTIVE ruleset is immutable,
 * and any change to values is a new ruleset version, not an edit of this file.
 */
class RulesetSeeder extends Seeder
{
    public const NAMESPACE_UUID = '6f0c2b1e-5a43-4d6e-9c1f-3b7a8e2d4c10';

    public const CODE = 'pa-core';

    public const VERSION = '0.1.0';

    public const SCORE_VERSION = 'paqs-0.1.0';

    public static function parameters(): array
    {
        $path = __DIR__.'/data/pa-core-0.1.0.json';
        $decoded = json_decode((string) file_get_contents($path), true, flags: JSON_THROW_ON_ERROR);
        if (! is_array($decoded)) {
            throw new RuntimeException("Ruleset file {$path} must contain a JSON object.");
        }
        ksort($decoded);

        return $decoded;
    }

    /** Canonical JSON: sorted keys, no whitespace, unescaped slashes and unicode, floats keep ".0" (as Python json.dumps). The engine must hash the same form. */
    public static function canonicalJson(array $parameters): string
    {
        return json_encode($parameters, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_PRESERVE_ZERO_FRACTION | JSON_THROW_ON_ERROR);
    }

    public static function parametersHash(array $parameters): string
    {
        return hash('sha256', self::canonicalJson($parameters));
    }

    public function run(): void
    {
        $parameters = self::parameters();

        DB::table('ruleset_versions')->insertOrIgnore([
            'id' => Uuid::uuid5(self::NAMESPACE_UUID, self::CODE.':'.self::VERSION)->toString(),
            'ruleset_code' => self::CODE,
            'version' => self::VERSION,
            'parameters' => self::canonicalJson($parameters),
            'parameters_hash' => self::parametersHash($parameters),
            'score_version' => self::SCORE_VERSION,
            'status' => 'ACTIVE',
            'validation_status' => 'HYPOTHESIS',
            'activated_at' => now(),
        ]);
    }
}
