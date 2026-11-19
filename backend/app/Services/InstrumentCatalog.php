<?php

namespace App\Services;

use Illuminate\Support\Facades\DB;

/** Active NSE instruments in the API `Instrument` shape, keyed by trading symbol. */
class InstrumentCatalog
{
    /**
     * @param  list<string>  $symbols
     * @return array<string, array<string, mixed>>
     */
    public function bySymbols(array $symbols): array
    {
        if ($symbols === []) {
            return [];
        }
        $rows = DB::table('instruments as i')
            ->leftJoin('instrument_snapshots as s', fn ($j) => $j->on('s.instrument_id', '=', 'i.id')->whereNull('s.effective_to'))
            ->where('i.exchange', 'NSE')->where('i.status', 'ACTIVE')->whereIn('i.trading_symbol', $symbols)
            ->get(['i.id', 'i.trading_symbol', 'i.name', 'i.exchange', 'i.segment', 'i.isin', 'i.status', 's.tick_size', 's.lot_size']);

        $out = [];
        foreach ($rows as $r) {
            $out[$r->trading_symbol] = [
                'id' => $r->id, 'symbol' => $r->trading_symbol, 'name' => $r->name, 'exchange' => $r->exchange,
                'segment' => $r->segment, 'sector' => null, 'isin' => $r->isin, 'status' => $r->status,
                'tick_size' => $r->tick_size === null ? '0.05' : (string) $r->tick_size,
                'lot_size' => (int) ($r->lot_size ?? 1),
            ];
        }

        return $out;
    }
}
