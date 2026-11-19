"use client";

import { useState } from "react";
import { Save } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import type { TradePlan } from "@/types";
import { addFill, logTrade, nowIstLocal, setLevels, validateFill, validateLevels, type FillForm, type LevelsForm, type LoggedTrade } from "@/lib/api/trades";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";

export type TradeDialogMode = { kind: "open" } | { kind: "fill"; trade: LoggedTrade; side: "BUY" | "SELL" } | { kind: "levels"; trade: LoggedTrade };

/**
 * Records a fill the owner got at the broker: the first BUY of a new trade, or a later BUY or SELL of an existing one.
 * Nothing here places an order (ADR-010). The form is mounted per open, so it always starts from its defaults.
 */
export function TradeDialog({ mode, onClose, onDone, plans = [] }: { mode: TradeDialogMode | null; onClose: () => void; onDone: () => void; plans?: TradePlan[] }) {
  return (
    <Dialog
      open={mode !== null}
      onClose={onClose}
      title={mode?.kind === "fill" ? `Record a fill · ${mode.trade.symbol}` : mode?.kind === "levels" ? `Stop and target · ${mode.trade.symbol}` : "Log a trade"}
      description={
        mode?.kind === "levels"
          ? "Your own levels for this trade. The stop counts as its open risk in today's limits. This app never places an order."
          : "Enter what you executed on your broker's platform. This app never places an order."
      }
    >
      {mode?.kind === "levels" && <LevelsForm key={mode.trade.id} trade={mode.trade} onClose={onClose} onDone={onDone} />}
      {mode && mode.kind !== "levels" && <TradeForm key={mode.kind === "fill" ? `${mode.trade.id}:${mode.side}` : "open"} mode={mode} onClose={onClose} onDone={onDone} plans={plans} />}
    </Dialog>
  );
}

function TradeForm({ mode, onClose, onDone, plans }: { mode: Exclude<TradeDialogMode, { kind: "levels" }>; onClose: () => void; onDone: () => void; plans: TradePlan[] }) {
  const toast = useToast();
  const fill = mode.kind === "fill";
  const [form, setForm] = useState<FillForm>({
    symbol: "",
    side: fill ? mode.side : "BUY",
    quantity: fill && mode.side === "SELL" ? String(mode.trade.quantityOpen) : "",
    price: "",
    executedAt: nowIstLocal(),
    fees: "",
    stop: "",
    target: "",
    planId: "",
  });
  const openPlans = plans.filter((p) => p.apiId && (p.status === "pending" || p.status === "entry-confirmed"));
  /** Choosing a plan fills the symbol, the price (if empty) and the plan's stop and target. */
  const choosePlan = (apiId: string) => {
    const plan = openPlans.find((p) => p.apiId === apiId);
    setForm((f) =>
      plan
        ? { ...f, planId: apiId, symbol: plan.symbol, price: f.price || String(plan.entry), stop: String(plan.stopLoss), target: String(plan.target) }
        : { ...f, planId: "" },
    );
  };
  const [serverError, setServerError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [touched, setTouched] = useState(false);
  const errors = touched ? validateFill(form, !fill) : {};
  const set = <K extends keyof FillForm>(k: K, v: FillForm[K]) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async () => {
    setTouched(true);
    if (Object.keys(validateFill(form, !fill)).length > 0) return;
    setBusy(true);
    setServerError(null);
    try {
      if (mode.kind === "fill") await addFill(mode.trade.id, form);
      else await logTrade(form);
      toast({ title: "Trade recorded", description: `${fill ? mode.trade.symbol : form.symbol.toUpperCase()} · ${form.side} ${form.quantity} at ₹${form.price}` });
      onDone();
      onClose();
    } catch (e) {
      setServerError(
        e instanceof ApiError && e.code === "OVERSELL_NOT_ALLOWED"
          ? "You cannot sell more shares than the trade has open."
          : e instanceof ApiError && e.code === "NOT_FOUND"
            ? "That symbol is not in the instrument list."
            : e instanceof ApiError && e.status === 422
              ? Object.values(e.fieldErrors).flat()[0] ?? "Check the values and try again."
              : "The trade could not be saved. Nothing was changed.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      {!fill && openPlans.length > 0 && (
        <Select
          label="Following a plan (optional)"
          value={form.planId}
          onChange={(e) => choosePlan(e.target.value)}
          options={[{ value: "", label: "No plan" }, ...openPlans.map((p) => ({ value: p.apiId ?? "", label: `${p.id} · ${p.symbol} · entry ${p.entry}` }))]}
        />
      )}
      {!fill && <Input label="Symbol" value={form.symbol} onChange={(e) => set("symbol", e.target.value.toUpperCase())} error={errors.symbol} placeholder="RELIANCE" autoFocus />}
      {fill && (
        <Select
          label="Side"
          value={form.side}
          onChange={(e) => set("side", e.target.value as "BUY" | "SELL")}
          options={[
            { value: "SELL", label: "Sell" },
            { value: "BUY", label: "Buy (add to the position)" },
          ]}
        />
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Input label="Quantity" inputMode="numeric" value={form.quantity} onChange={(e) => set("quantity", e.target.value)} error={errors.quantity} />
        <Input label="Price (₹)" inputMode="decimal" value={form.price} onChange={(e) => set("price", e.target.value)} error={errors.price} />
        <Input label="Executed at (IST)" type="datetime-local" value={form.executedAt} onChange={(e) => set("executedAt", e.target.value)} error={errors.executedAt} />
        {!fill && <Input label="Stop (₹, optional)" inputMode="decimal" value={form.stop} onChange={(e) => set("stop", e.target.value)} error={errors.stop} hint="Below your price. Counts as this trade's open risk." />}
        {!fill && <Input label="Target (₹, optional)" inputMode="decimal" value={form.target} onChange={(e) => set("target", e.target.value)} error={errors.target} hint="Above your price." />}
        <Input label="Charges (₹, optional)" inputMode="decimal" value={form.fees} onChange={(e) => set("fees", e.target.value)} error={errors.fees} hint="Brokerage, taxes and fees of this fill." />
      </div>
      {serverError && (
        <p role="alert" className="text-sm text-destructive">
          {serverError}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" disabled={busy}>
          <Save /> {busy ? "Saving…" : "Save trade"}
        </Button>
      </div>
    </form>
  );
}

function LevelsForm({ trade, onClose, onDone }: { trade: LoggedTrade; onClose: () => void; onDone: () => void }) {
  const toast = useToast();
  const [form, setForm] = useState<LevelsForm>({ stop: trade.stop === null ? "" : String(trade.stop), target: trade.target === null ? "" : String(trade.target) });
  const [busy, setBusy] = useState(false);
  const [touched, setTouched] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const errors = touched ? validateLevels(form) : {};

  const submit = async () => {
    setTouched(true);
    if (Object.keys(validateLevels(form)).length > 0) return;
    setBusy(true);
    setServerError(null);
    try {
      await setLevels(trade.id, form);
      toast({ title: "Levels saved", description: `${trade.symbol} · stop ${form.stop || "none"}, target ${form.target || "none"}` });
      onDone();
      onClose();
    } catch {
      setServerError("The levels could not be saved. Nothing was changed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Input label="Stop (₹)" inputMode="decimal" value={form.stop} onChange={(e) => setForm((f) => ({ ...f, stop: e.target.value }))} error={errors.stop} hint="Leave empty to clear. A trailed stop may sit above your entry." autoFocus />
        <Input label="Target (₹)" inputMode="decimal" value={form.target} onChange={(e) => setForm((f) => ({ ...f, target: e.target.value }))} error={errors.target} hint="Leave empty to clear." />
      </div>
      {serverError && (
        <p role="alert" className="text-sm text-destructive">
          {serverError}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" disabled={busy}>
          <Save /> {busy ? "Saving…" : "Save levels"}
        </Button>
      </div>
    </form>
  );
}
