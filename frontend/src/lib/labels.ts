/**
 * Single source of truth for how domain enums are named and toned in the UI.
 * Components look up labels here instead of hard-coding strings.
 */
import type {
  AccountBlockReason,
  Bias,
  Book,
  MarketStructure,
  SetupStatus,
  SetupType,
  SignalState,
  TradeOutcome,
  TradePlanStatus,
} from "@/types";
import type { Tone } from "./colors";

export type { Tone };

interface LabelMeta {
  label: string;
  tone: Tone;
  description: string;
}

export const SIGNAL_STATES: Record<SignalState, LabelMeta> = {
  "buy-watch": {
    label: "BUY WATCH",
    tone: "warning",
    description:
      "A setup is forming. Wait for the entry trigger before acting. This is not an entry.",
  },
  "entry-confirmed": {
    label: "ENTRY CONFIRMED",
    tone: "success",
    description:
      "The entry conditions of the setup have been met on a closing basis. Evaluate the plan and risk before placing any order.",
  },
  hold: {
    label: "HOLD",
    tone: "info",
    description:
      "An existing position remains valid. Structure is intact and the stop has not been hit.",
  },
  exit: {
    label: "EXIT",
    tone: "destructive",
    description:
      "An exit condition has been met: the target was reached, the stop was hit, or structure invalidated the trade.",
  },
  "no-trade": {
    label: "NO TRADE",
    tone: "neutral",
    description:
      "No setup meets the criteria. Staying flat is a valid decision.",
  },
};

export const SETUP_TYPES: Record<SetupType, { label: string; short: string }> = {
  "opening-range-breakout": { label: "Opening Range Breakout", short: "ORB" },
  "prev-day-high-break": { label: "Previous-Day High Break", short: "PDH Break" },
  "prev-day-low-break": { label: "Previous-Day Low Break", short: "PDL Break" },
  "breakout-retest": { label: "Breakout & Retest", short: "BO-Retest" },
  "pullback-to-support": { label: "Pullback to Support", short: "Pullback" },
  "range-breakout": { label: "Range Breakout", short: "Range BO" },
  "breakdown-retest": { label: "Breakdown & Retest", short: "BD-Retest" },
  "trend-continuation": { label: "Trend Continuation", short: "Continuation" },
  "liquidity-sweep-reversal": { label: "Liquidity Sweep Reversal", short: "Sweep" },
  "failed-breakdown-reclaim": { label: "Failed Breakdown Reclaim", short: "Reclaim" },
  "range-bound": { label: "Range-bound", short: "Range" },
};

export const SETUP_STATUS: Record<SetupStatus, LabelMeta> = {
  detected: {
    label: "Forming",
    tone: "info",
    description: "Pattern identified by the analysis. No trigger yet.",
  },
  "awaiting-confirmation": {
    label: "Awaiting confirmation",
    tone: "warning",
    description: "Price is near the trigger level. Waiting for a confirming close.",
  },
  "entry-confirmed": {
    label: "Entry confirmed",
    tone: "success",
    description: "Trigger condition met on a closing basis.",
  },
  invalidated: {
    label: "Invalidated",
    tone: "destructive",
    description: "Price violated the setup's invalidation level.",
  },
  expired: {
    label: "Expired",
    tone: "neutral",
    description: "The setup's window passed without a trigger (for example, after the entry cutoff).",
  },
};

export const STRUCTURES: Record<MarketStructure, LabelMeta> = {
  uptrend: {
    label: "Uptrend",
    tone: "bull",
    description: "Higher highs and higher lows.",
  },
  downtrend: {
    label: "Downtrend",
    tone: "bear",
    description: "Lower highs and lower lows.",
  },
  range: {
    label: "Range",
    tone: "neutral",
    description: "Price oscillating between defined support and resistance.",
  },
  transition: {
    label: "Transition",
    tone: "warning",
    description: "A change of character has occurred; the new trend is not yet established.",
  },
};

export const BIAS: Record<Bias, { label: string; tone: Tone }> = {
  bullish: { label: "Bullish", tone: "bull" },
  bearish: { label: "Bearish", tone: "bear" },
  neutral: { label: "Neutral", tone: "neutral" },
};

export const PLAN_STATUS: Record<TradePlanStatus, LabelMeta> = {
  pending: {
    label: "Pending",
    tone: "warning",
    description: "Proposed plan waiting for its entry trigger.",
  },
  "entry-confirmed": {
    label: "Entry confirmed",
    tone: "info",
    description: "Trigger met. No order has been executed yet.",
  },
  active: {
    label: "Active",
    tone: "success",
    description: "An order linked to this plan was executed and the position is open.",
  },
  completed: {
    label: "Completed",
    tone: "neutral",
    description: "Position exited at target or stop.",
  },
  invalidated: {
    label: "Invalidated",
    tone: "destructive",
    description: "Setup failed before entry was triggered.",
  },
  cancelled: {
    label: "Cancelled",
    tone: "neutral",
    description: "Withdrawn by the trader.",
  },
};

export const OUTCOMES: Record<TradeOutcome, { label: string; tone: Tone }> = {
  win: { label: "Win", tone: "success" },
  loss: { label: "Loss", tone: "destructive" },
  breakeven: { label: "Breakeven", tone: "neutral" },
};

/** Why a book cannot take new plans (TRD-05 §8). */
export const ACCOUNT_BLOCK_REASONS: Record<AccountBlockReason, string> = {
  "daily-loss-limit": "Daily loss limit reached",
  "max-consecutive-losses": "Losing-streak limit reached",
  "max-open-positions": "Open-position limit reached",
  "open-risk-limit": "Open-risk limit reached",
  "entry-cutoff-passed": "Entry cutoff passed",
  "session-closed": "Session closed",
};

/** Engine reasons a signal is NO_TRADE or a setup was not created (TRD-04 §8). Unknown codes fall back to the code itself. */
export const SIGNAL_REASONS: Record<string, string> = {
  NO_SETUP: "No setup on the latest closed bar",
  LOW_SCORE: "The quality score is below the minimum",
  RR_BELOW_MINIMUM: "Reward to risk is below the minimum",
  NO_TARGET: "No target level above the entry",
  AFTER_ENTRY_CUTOFF: "The entry cutoff has passed",
  MISSING_CONTEXT: "Previous-day levels are not available",
  OPENED_ABOVE_LEVEL: "The session opened above the level",
  OPENED_BELOW_LEVEL: "The session opened below the level",
};

export const BOOKS: Record<Book, string> = { paper: "Paper", actual: "Actual" };
