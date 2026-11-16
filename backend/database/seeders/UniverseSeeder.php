<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use Ramsey\Uuid\Uuid;

/**
 * Seeds the universe rows allowed by ARC-03 §6.4. Only `DEMO` gets members (DemoSeeder). The real NIFTY universes
 * are created empty: effective-dated membership comes from the universe loader in M2 (T-203 area, ENG-01 M2).
 */
class UniverseSeeder extends Seeder
{
    public const NAMESPACE_UUID = '1c9d5e7a-2b84-4f0a-8d36-7e5a9b1c3f42';

    /** @var list<array{0: string, 1: string, 2: ?string, 3: bool}> */
    private const UNIVERSES = [
        ['NIFTY500', 'NIFTY 500', 'NSE Indices', false],
        ['NIFTY50', 'NIFTY 50', 'NSE Indices', false],
        ['NIFTY100', 'NIFTY 100', 'NSE Indices', false],
        ['NIFTY200', 'NIFTY 200', 'NSE Indices', false],
        ['NIFTYMIDCAP150', 'NIFTY Midcap 150', 'NSE Indices', false],
        ['DEMO', 'Demo universe (sample data)', 'PriceAction AI sample data', true],
    ];

    public static function id(string $code): string
    {
        return Uuid::uuid5(self::NAMESPACE_UUID, 'universe:'.$code)->toString();
    }

    public function run(): void
    {
        foreach (self::UNIVERSES as [$code, $name, $source, $isDemo]) {
            DB::table('universes')->insertOrIgnore([
                'id' => self::id($code), 'code' => $code, 'name' => $name, 'source' => $source, 'is_demo' => $isDemo,
            ]);
        }
    }
}
