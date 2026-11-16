"use client";

import { useMemo, useState } from "react";
import { FileText } from "lucide-react";
import { formatInr, formatInt, formatRR } from "@/lib/format";
import type { StockAnalysis } from "@/types";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";

/** Drafts a PROPOSED trade plan from the analysis levels. Never places an order. */
export function CreatePlanDialog({ a, open, onClose }: { a: StockAnalysis; open: boolean; onClose: () => void }) {
  const toast = useToast();
  const [entry, setEntry] = useState(String(a.levels.entry));
  const [stop, setStop] = useState(String(a.levels.stopLoss));
  const [target, setTarget] = useState(String(a.levels.target));
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

  const disabled = a.setup.direction === "short";

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
            disabled={!calc.valid || disabled}
            onClick={() => {
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
            <Input label="Entry (₹)" inputMode="decimal" value={entry} onChange={(e) => setEntry(e.target.value)} error={calc.errors.entry} />
            <Input label="Stop-loss (₹)" inputMode="decimal" value={stop} onChange={(e) => setStop(e.target.value)} error={calc.errors.stop} />
            <Input label="Target (₹)" inputMode="decimal" value={target} onChange={(e) => setTarget(e.target.value)} error={calc.errors.target} />
          </div>
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
        </div>
      )}
    </Dialog>
  );
}
