<?php

namespace Database\Seeders;

use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    use WithoutModelEvents;

    /**
     * Seed reference data (ruleset, universes) and the DEMO data mode. Run as the schema owner: `make seed`.
     */
    public function run(): void
    {
        $this->call(DemoSeeder::class);
    }
}
