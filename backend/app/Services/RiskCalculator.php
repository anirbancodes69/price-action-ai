<?php

namespace App\Services;

use App\Models\User;
use App\Services\Engine\EngineClient;
use App\Support\ApiException;
use Illuminate\Support\Facades\DB;

/**
 * Sizes a long plan through the engine (RM-01: every risk figure is the engine's). Laravel gathers the inputs: the risk
 * profile, the book's account state, the instrument's tick and lot size and the session clock. A rule violation is a 422
 * carrying the whole calculation, so callers can explain the limits.
 */
class RiskCalculator
{
    public function __construct(
        private readonly EngineClient $engine,
        private readonly RiskProfileResolver $profiles,
        private readonly AccountStateService $accounts,
        private readonly RulesetParameters $ruleset,
        private readonly SessionClock $clock,
    ) {}

    /** @return array<string, mixed> the engine's `RiskResult` */
    public function calculate(User $user, string $book, string $symbol, string $direction, string $entry, string $stop, string $target, ?string $riskPct = null): array
    {
        $inst = DB::table('instruments as i')
            ->leftJoin('instrument_snapshots as s', fn ($j) => $j->on('s.instrument_id', '=', 'i.id')->whereNull('s.effective_to'))
            ->where('i.exchange', 'NSE')->where('i.status', 'ACTIVE')->where('i.trading_symbol', $symbol)
            ->first(['s.tick_size', 's.lot_size']);
        if ($inst === null) {
            throw new ApiException('NOT_FOUND', 'Unknown instrument.', 404);
        }

        $profile = $this->profiles->for($user);
        $result = $this->engine->positionSize([
            'book' => $book,
            'direction' => $direction,
            'capital' => $profile['capital'],
            'risk_pct' => $riskPct ?? $profile['risk_pct'],
            'entry' => $entry,
            'stop' => $stop,
            'target' => $target,
            'tick_size' => $inst->tick_size === null ? '0.05' : (string) $inst->tick_size,
            'lot_size' => (int) ($inst->lot_size ?? 1),
            'max_position_value' => $profile['max_position_value'],
            'max_open_positions' => $profile['max_open_positions'],
            'max_open_risk_pct' => $profile['max_open_risk_pct'],
            'daily_loss_limit_pct' => $profile['daily_loss_limit_pct'],
            'max_consecutive_losses' => $profile['max_consecutive_losses'],
            'min_rr' => $profile['min_rr'],
            'account_state' => $this->accounts->forBook($user, $book),
            'as_of_ts' => $this->clock->lastBarEnd()->format('Y-m-d\TH:i:sP'),
            'entry_cutoff_at' => $this->clock->entryCutoff()->format('Y-m-d\TH:i:sP'),
            'ruleset_version' => $this->ruleset->version(),
        ]);

        $errors = $result['errors'] ?? [];
        if ($errors !== []) {
            throw new ApiException((string) $errors[0], 'The plan does not pass the risk rules.', 422, ['errors' => $errors, 'calculation' => $result]);
        }

        return $result;
    }
}
