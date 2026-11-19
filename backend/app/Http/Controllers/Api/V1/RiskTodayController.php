<?php

namespace App\Http\Controllers\Api\V1;

use App\Http\Controllers\Controller;
use App\Models\User;
use App\Services\AccountStateService;
use App\Services\Engine\EngineClient;
use App\Services\RiskProfileResolver;
use App\Services\Scanner\ScannerRowMapper;
use App\Services\SessionClock;
use App\Support\ApiException;
use App\Support\ApiResponse;
use Carbon\CarbonImmutable;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * `GET /api/v1/risk/today` (R2): the book's account state for the current session. Laravel derives the state from the
 * trade tables; the engine applies the limits (RM-01), so what remains and the blocking rule are the engine's answer.
 */
class RiskTodayController extends Controller
{
    public function show(Request $request, AccountStateService $accounts, RiskProfileResolver $profiles, EngineClient $engine, SessionClock $clock): JsonResponse
    {
        $book = $request->query('book');
        if (! in_array($book, ['PAPER', 'ACTUAL'], true)) {
            throw new ApiException('BOOK_REQUIRED', 'Choose a book: PAPER or ACTUAL.', 422, ['field_errors' => ['book' => ['Use PAPER or ACTUAL.']]]);
        }
        /** @var User $user */
        $user = $request->user();
        $profile = $profiles->for($user);
        $now = CarbonImmutable::now();
        $cutoff = $clock->entryCutoff($now);
        $state = $accounts->forBook($user, $book, $now);

        $result = $engine->accountState([
            'book' => $book,
            'capital' => $profile['capital'],
            'daily_loss_limit_pct' => $profile['daily_loss_limit_pct'],
            'max_consecutive_losses' => $profile['max_consecutive_losses'],
            'max_open_positions' => $profile['max_open_positions'],
            'account_state' => $state,
            'session_open' => $clock->isOpen($now),
            'as_of_ts' => $clock->lastBarEnd($now)->format('Y-m-d\TH:i:sP'),
            'entry_cutoff_at' => $cutoff->format('Y-m-d\TH:i:sP'),
        ]);
        $a = $result['account_state'];

        return ApiResponse::ok([
            'book' => $book,
            'session_date' => $now->setTimezone(SessionClock::TZ)->toDateString(),
            'realised_net_pnl_today' => $this->money($a['realised_net_pnl_today']),
            'open_risk' => $this->money($a['open_risk']),
            'losing_streak' => (int) $a['losing_streak'],
            'open_positions' => (int) $state['open_positions'],
            'daily_loss_limit' => $this->money($result['daily_loss_limit']),
            'remaining_daily_loss' => $this->money($a['remaining_daily_loss']),
            'max_consecutive_losses' => (int) $result['max_consecutive_losses'],
            'max_open_positions' => (int) $result['max_open_positions'],
            'blocked_reason' => $a['blocked_reason'],
            'entry_cutoff_at' => ScannerRowMapper::time($cutoff->toIso8601String()),
            'session_end_exit_at' => ScannerRowMapper::time($clock->sessionEndExit($now)->toIso8601String()),
        ]);
    }

    private function money(string $v): string
    {
        return bcadd($v, '0', 2);
    }
}
