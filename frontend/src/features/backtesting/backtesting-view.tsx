"use client";

import { useState } from "react";
import { FlaskConical, Info, Play } from "lucide-react";
import type { BacktestStrategy } from "@/types";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel, PanelHeader } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { EquityChart } from "@/components/charts/equity-chart";
import { Badge } from "@/components/data/badge";
import { MetricCard } from "@/components/data/metric-card";
import { Skeleton } from "@/components/data/loading-skeleton";

interface Config {
  strategy: string;
  universe: string;
  symbol: string;
  from: string;
  to: string;
  capital: string;
  risk: string;
}

type RunState = "idle" | "running" | "queued";

export function BacktestingView({
  strategies,
  symbols,
  placeholderCurve,
}: {
  strategies: BacktestStrategy[];
  symbols: string[];
  placeholderCurve: { time: string; value: number }[];
}) {
  const toast = useToast();
  const [cfg, setCfg] = useState<Config>({
    strategy: strategies[0]?.id ?? "",
    universe: "single",
    symbol: symbols[0] ?? "",
    from: "2023-01-01",
    to: "2026-10-31",
    capital: "1000000",
    risk: "1",
  });
  const [errors, setErrors] = useState<Partial<Record<keyof Config, string>>>({});
  const [run, setRun] = useState<RunState>("idle");
  const set = (k: keyof Config, v: string) => setCfg((c) => ({ ...c, [k]: v }));
  const strategy = strategies.find((s) => s.id === cfg.strategy);

  const validate = () => {
    const e: Partial<Record<keyof Config, string>> = {};
    if (!cfg.from || !cfg.to) e.from = "Choose a date range";
    else if (cfg.from >= cfg.to) e.to = "End date must be after start date";
    if (!(Number(cfg.capital) >= 10000)) e.capital = "Minimum ₹10,000";
    const r = Number(cfg.risk);
    if (!(r > 0 && r <= 5)) e.risk = "Between 0.1% and 5%";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const onRun = () => {
    if (!validate()) return;
    setRun("running");
    setTimeout(() => {
      setRun("queued");
      toast({ title: "Backtest engine not connected", description: "Configuration validated. Results will be computed by the analysis engine in a later phase.", tone: "info" });
    }, 1200);
  };

  return (
    <PageContainer>
      <PageHeader
        title="Backtesting"
        description="Evaluate how a price-action setup would have behaved historically."
        meta={<Badge tone="warn" variant="outline">Engine not connected</Badge>}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[340px_minmax(0,1fr)] lg:gap-5">
        <Panel className="h-fit">
          <PanelHeader title="Configuration" icon={<FlaskConical />} />
          <form
            className="flex flex-col gap-3.5 p-4"
            onSubmit={(e) => {
              e.preventDefault();
              onRun();
            }}
          >
            <Select label="Strategy" value={cfg.strategy} onChange={(e) => set("strategy", e.target.value)} options={strategies.map((s) => ({ value: s.id, label: s.name }))} />
            {strategy && <p className="-mt-1.5 text-2xs leading-relaxed text-fg-subtle">{strategy.description}</p>}
            <Select
              label="Instruments"
              value={cfg.universe}
              onChange={(e) => set("universe", e.target.value)}
              options={[
                { value: "single", label: "Single stock" },
                { value: "nifty50", label: "NIFTY 50 constituents" },
                { value: "watchlist", label: "Watchlist: Swing candidates" },
              ]}
            />
            {cfg.universe === "single" && (
              <Select label="Symbol" value={cfg.symbol} onChange={(e) => set("symbol", e.target.value)} options={symbols.map((s) => ({ value: s, label: s }))} />
            )}
            <div className="grid grid-cols-2 gap-3">
              <Input label="From" type="date" value={cfg.from} onChange={(e) => set("from", e.target.value)} error={errors.from} />
              <Input label="To" type="date" value={cfg.to} onChange={(e) => set("to", e.target.value)} error={errors.to} />
            </div>
            <Input label="Starting capital (₹)" inputMode="numeric" value={cfg.capital} onChange={(e) => set("capital", e.target.value)} error={errors.capital} />
            <Input label="Risk per trade (%)" inputMode="decimal" value={cfg.risk} onChange={(e) => set("risk", e.target.value)} error={errors.risk} hint="Position size is derived from stop distance." />
            <Select label="Timeframe" value="1D" onChange={() => undefined} options={[{ value: "1D", label: "Daily" }]} />
            <Button type="submit" variant="primary" size="lg" loading={run === "running"} className="mt-1">
              {run !== "running" && <Play />} {run === "running" ? "Validating…" : "Run backtest"}
            </Button>
          </form>
        </Panel>

        <div className="flex min-w-0 flex-col gap-4 lg:gap-5">
          <div className="flex items-start gap-2.5 rounded-md border border-info/25 bg-info/5 px-4 py-3 text-xs text-fg-muted">
            <Info className="mt-0.5 size-4 shrink-0 text-info" aria-hidden />
            <p>
              No backtest results are shown in this phase. The metrics below are empty placeholders, and the curve is an
              <span className="font-medium text-fg"> illustrative layout sample, not a result</span>.
            </p>
          </div>

          <section className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5" aria-label="Results summary">
            {["Win rate", "Profit factor", "Max drawdown", "Total trades", "Net return"].map((label) =>
              run === "running" ? (
                <Skeleton key={label} className="h-[92px]" />
              ) : (
                <MetricCard key={label} label={label} value={<span className="text-fg-subtle">—</span>} hint="Awaiting engine" />
              ),
            )}
          </section>

          <Panel className="overflow-hidden">
            <PanelHeader
              title="Equity curve"
              description="Placeholder visual — not derived from any backtest"
              actions={<Badge tone="warn" variant="outline" size="xs">Illustrative sample</Badge>}
            />
            <div className="relative h-72 md:h-80">
              <div className="absolute inset-0 opacity-35 grayscale">
                <EquityChart points={placeholderCurve} />
              </div>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="rounded border border-border-strong bg-raised/90 px-3 py-1.5 text-xs text-fg-muted shadow-pop">
                  {run === "queued" ? "Configuration validated · engine not connected" : "Run a backtest to see results"}
                </span>
              </div>
            </div>
          </Panel>

          <Panel>
            <PanelHeader title="Trade list" description="Individual simulated trades will appear here" />
            <p className="px-4 py-8 text-center text-xs text-fg-subtle">No trades — backtest engine not connected.</p>
          </Panel>
        </div>
      </div>
    </PageContainer>
  );
}
