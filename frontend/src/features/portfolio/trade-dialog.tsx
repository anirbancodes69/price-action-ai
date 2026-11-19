"use client";

import { useState } from "react";
import { Save } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { addFill, logTrade, nowIstLocal, validateFill, type FillForm, type LoggedTrade } from "@/lib/api/trades";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";

export type TradeDialogMode = { kind: "open" } | { kind: "fill"; trade: LoggedTrade; side: "BUY" | "SELL" };

/**
 * Records a fill the owner got at the broker: the first BUY of a new trade, or a later BUY or SELL of an existing one.
 * Nothing here places an order (ADR-010). The form is mounted per open, so it always starts from its defaults.
 */
export function TradeDialog({ mode, onClose, onDone }: { mode: TradeDialogMode | null; onClose: () => void; onDone: () => void }) {
  return (
    <Dialog
      open={mode !== null}
      onClose={onClose}
      title={mode?.kind === "fill" ? `Record a fill · ${mode.trade.symbol}` : "Log a trade"}
      description="Enter what you executed on your broker's platform. This app never places an order."
    >
      {mode && <TradeForm key={mode.kind === "fill" ? `${mode.trade.id}:${mode.side}` : "open"} mode={mode} onClose={onClose} onDone={onDone} />}
    </Dialog>
  );
}

function TradeForm({ mode, onClose, onDone }: { mode: TradeDialogMode; onClose: () => void; onDone: () => void }) {
  const toast = useToast();
  const fill = mode.kind === "fill";
  const [form, setForm] = useState<FillForm>({
    symbol: "",
    side: fill ? mode.side : "BUY",
    quantity: fill && mode.side === "SELL" ? String(mode.trade.quantityOpen) : "",
    price: "",
    executedAt: nowIstLocal(),
    fees: "",
  });
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
