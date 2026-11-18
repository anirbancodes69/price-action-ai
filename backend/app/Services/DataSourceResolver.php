<?php

namespace App\Services;

use App\Support\ApiException;
use Illuminate\Support\Facades\DB;

/**
 * Which `data_sources` row the owner's requests read (personal mode: one source, ADR-011/ADR-014).
 * `ENGINE_DATA_SOURCE_ID` wins; without it the DEMO source is used, which the API always labels as sample data.
 */
class DataSourceResolver
{
    public function id(): string
    {
        $configured = (string) config('services.engine.data_source_id');
        if ($configured !== '') {
            return $configured;
        }

        $demo = DB::table('data_sources')
            ->where('mode', 'DEMO')->where('provider', 'DEMO')->whereNull('tenant_id')
            ->value('id');
        if ($demo === null) {
            throw new ApiException('NO_DATA_SOURCE', 'No data source is configured.', 409);
        }

        return (string) $demo;
    }
}
