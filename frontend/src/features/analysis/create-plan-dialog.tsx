"use client";

import { useMemo, useState } from "react";
import { FileText } from "lucide-react";
import { formatInr, formatInt, formatRR } from "@/lib/format";
import { ApiError } from "@/lib/api/client";
import { validatePlanLevels, type PlanLevelsForm } from "@/lib/api/trade-plans";
import type { StockAnalysis } from "@/types";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";

/** Drafts a PROPOSED trade plan from the analysis levels. Never places an order. */
export function CreatePlanDialog({
  a,
  open,
  onClose,
  onCreate,
}: {
  a: StockAnalysis;
  open: boolean;
  onClose: () => void;
  /** HTTP mode: creates the plan on the server, where the engine sizes it (no client-side sizing). */
  onCreate?: (levels: PlanLevelsForm) => Promise<{ quantity: number }>;
}) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [entry, setEntry] = useState(a.levels ? String(a.levels.entry) : "");
  const [stop, setStop] = useState(a.levels ? String(a.levels.stopLoss) : "");
  const [target, setTarget] = useState(a.levels ? String(a.levels.target) : "");
  const [riskBudget, setRiskBudget] = useState("5000");

  const calc = useMemo(() => {
    const e = Number(entry);
    const s = Number(stop);
    const t = Number(target);
    const r = Number(riskBudget);
    const errors: Record<string, string> = {};
    if (!(e > 0)) errors.entry = "Enter a valid price";
    if (!(s > 0)) errors.stop = "Enter a valid price";
    else if (e > 0 && s >= e) errors.stop = "Stop-loss must be below entry for a long plan";
    if (!(t > 0)) errors.target = "Enter a valid price";
    else if (e > 0 && t <= e) errors.target = "Target must be above entry";
    if (!(r > 0)) errors.risk = "Enter the ₹ amount you are willing to lose";
    const perShare = e - s;
    const qty = perShare > 0 && r > 0 ? Math.floor(r / perShare) : 0;
    const rr = perShare > 0 ? (t - e) / perShare : 0;
    return { errors, qty, rr, value: qty * e, valid: Object.keys(errors).length === 0 && qty > 0 };
  }, [entry, stop, target, riskBudget]);

  const disabled = a.setup.direction === "short" || a.levels === null;
  const liveErrors = onCreate ? validatePlanLevels({ entry, stop, target }) : {};
  const liveValid = Object.keys(liveErrors).length === 0;

  const saveLive = async () => {
    if (!onCreate) return;
    setBusy(true);
    setServerError(null);
    try {
      const { quantity } = await onCreate({ entry, stop, target });
      toast({ title: "Proposed plan saved", description: `${a.stock.symbol} · ${formatInt(quantity)} shares, sized by the engine from your risk profile.` });
      onClose();
    } catch (e) {
      setServerError(planError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={`New trade plan · ${a.stock.symbol}`}
      description="Creates a proposed plan for review. It does not place an order with any broker."
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={disabled || busy || (onCreate ? !liveValid : !calc.valid)}
            onClick={() => {
              if (onCreate) return void saveLive();
              toast({
                title: "Proposed plan saved",
                description: `${a.stock.symbol} · ${formatInt(calc.qty)} shares. Demo mode: kept for this session only.`,
              });
              onClose();
            }}
          >
            <FileText /> Save proposed plan
          </Button>
        </>
      }
    >
      {disabled ? (
        <p className="text-muted-foreground">
          Structure is bearish. Long trade plans are not created for this setup; short-side levels are shown for reference only.
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Input label="Entry (₹)" inputMode="decimal" value={entry} onChange={(e) => setEntry(e.target.value)} error={onCreate ? liveErrors.entry : calc.errors.entry} />
            <Input label="Stop-loss (₹)" inputMode="decimal" value={stop} onChange={(e) => setStop(e.target.value)} error={onCreate ? liveErrors.stop : calc.errors.stop} />
            <Input label="Target (₹)" inputMode="decimal" value={target} onChange={(e) => setTarget(e.target.value)} error={onCreate ? liveErrors.target : calc.errors.target} />
          </div>
          {onCreate ? (
            <>
              <p className="text-sm text-muted-foreground">
                The engine sizes the plan from your risk profile and today&apos;s limits. The quantity is shown after saving; a plan that breaks a rule is refused with the reason.
              </p>
              {serverError && (
                <p role="alert" className="text-sm text-destructive">
                  {serverError}
                </p>
              )}
            </>
          ) : (
            <>
          <Input
            label="Risk per trade (₹)"
            inputMode="numeric"
            value={riskBudget}
            onChange={(e) => setRiskBudget(e.target.value)}
            error={calc.errors.risk}
            hint="Quantity is sized so that a stop-out loses at most this amount."
          />
          <dl className="grid grid-cols-3 gap-3 rounded-lg bg-muted px-4 py-3 tabular-nums" aria-live="polite">
            <div className="flex flex-col gap-1">
              <dt className="text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Quantity</dt>
              <dd className="font-stat text-2xl leading-none text-foreground">{formatInt(calc.qty)}</dd>
            </div>
            <div className="flex flex-col gap-1">
              <dt className="text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Position value</dt>
              <dd className="font-stat text-2xl leading-none text-foreground">{formatInr(calc.value, { decimals: false })}</dd>
            </div>
            <div className="flex flex-col gap-1">
              <dt className="text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Risk / reward</dt>
              <dd className="font-stat text-2xl leading-none text-foreground">{calc.rr > 0 ? formatRR(calc.rr) : "—"}</dd>
            </div>
          </dl>
            </>
          )}
        </div>
      )}
    </Dialog>
  );
}

/** Plain words for the errors a plan can be refused with (TRD-04 §12, TRD-05 §8). */
export function planError(e: unknown): string {
  if (!(e instanceof ApiError)) return "The plan could not be saved. Nothing was changed.";
  const known: Record<string, string> = {
    SETUP_NOT_ACTIONABLE: "This setup is not actionable (it is forming, a short, or its reward-to-risk is too low).",
    SETUP_TERMINAL: "This setup has ended.",
    ENTRY_WINDOW_ELAPSED: "The entry window has closed for today.",
    DAILY_LOSS_LIMIT_REACHED: "Today's loss limit is reached. No new plans until tomorrow.",
    MAX_CONSECUTIVE_LOSSES_REACHED: "The consecutive-loss limit is reached for today.",
    MAX_POSITIONS_REACHED: "The open-position limit is reached.",
    SESSION_CLOSED: "The market is closed.",
    ENTRY_CUTOFF_PASSED: "It is past the entry cutoff.",
    RR_BELOW_MINIMUM: "The reward-to-risk is below the minimum.",
    STOP_TOO_TIGHT: "The stop is too close to the entry.",
    STOP_TOO_WIDE: "The stop is too far from the entry.",
    ENGINE_UNAVAILABLE: "The analysis engine is not reachable. Nothing was changed.",
  };
  return known[e.code] ?? "The plan was refused. Check the levels and try again.";
}
