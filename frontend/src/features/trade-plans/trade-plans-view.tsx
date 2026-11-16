"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ClipboardList, LayoutGrid, MoreHorizontal, Rows3, XCircle, Ban, Receipt } from "lucide-react";
import { formatInr, formatInt, formatRR } from "@/lib/format";
import { PLAN_STATUS, SETUP_TYPES } from "@/lib/labels";
import type { TradePlan, TradePlanStatus } from "@/types";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { Button, ButtonLink } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Dropdown } from "@/components/ui/dropdown";
import { ChoiceGroup } from "@/components/ui/choice-group";
import { Tabs } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { DataTable, type Column } from "@/components/data/data-table";
import { Disclaimer } from "@/components/data/disclaimer";
import { Empty } from "@/components/data/empty";
import { Stat, StatGrid } from "@/components/data/stat";
import { SampleDataBadge } from "@/components/data/sample-data-badge";
import { StatusBadge } from "@/components/data/status-badge";
import { LifecycleStrip } from "@/components/trading/lifecycle-strip";
import { SignalBadge } from "@/components/trading/signal-badge";
import { PlanLevelsInline, TradePlanCard } from "@/components/trading/trade-plan-card";

type TabValue = "all" | TradePlanStatus;
const ORDER: TradePlanStatus[] = ["pending", "entry-confirmed", "active", "completed", "invalidated", "cancelled"];

export function TradePlansView({ initial, asOf }: { initial: TradePlan[]; asOf: string }) {
  const toast = useToast();
  const [plans, setPlans] = useState(initial);
  const [tab, setTab] = useState<TabValue>("all");
  const [view, setView] = useState<"cards" | "table">("cards");
  const [confirmCancel, setConfirmCancel] = useState<TradePlan | null>(null);

  const visible = useMemo(() => (tab === "all" ? plans : plans.filter((p) => p.status === tab)), [plans, tab]);
  const open = plans.filter((p) => ["pending", "entry-confirmed", "active"].includes(p.status));
  const openRisk = open.reduce((a, p) => a + p.riskAmount, 0);
  const avgRR = open.length ? open.reduce((a, p) => a + p.riskReward, 0) / open.length : 0;

  const setStatus = (id: string, status: TradePlanStatus) =>
    setPlans((ps) => ps.map((p) => (p.id === id ? { ...p, status, signal: status === "cancelled" || status === "invalidated" ? "no-trade" : p.signal } : p)));

  const actions = (p: TradePlan) => {
    if (!["pending", "entry-confirmed"].includes(p.status)) return null;
    return (
      <Dropdown
        width="w-52"
        trigger={({ open, toggle, id }) => (
          <Button size="icon-sm" variant="ghost" onClick={toggle} aria-label={`Actions for plan ${p.id}`} aria-haspopup="menu" aria-expanded={open} aria-controls={open ? id : undefined}>
            <MoreHorizontal />
          </Button>
        )}
        items={[
          {
            label: "Link executed order…",
            icon: Receipt,
            onSelect: () => toast({ title: "Broker not connected", description: "Orders can be linked once a broker connection is available.", tone: "info" }),
          },
          {
            label: "Mark invalidated",
            icon: XCircle,
            onSelect: () => {
              setStatus(p.id, "invalidated");
              toast({ title: `${p.id} marked invalidated`, tone: "info" });
            },
          },
          "separator",
          { label: "Cancel plan", icon: Ban, tone: "danger", onSelect: () => setConfirmCancel(p) },
        ]}
      />
    );
  };

  const columns: Column<TradePlan>[] = [
    {
      key: "symbol",
      header: "Symbol",
      sticky: true,
      grow: true,
      sortValue: (p) => p.symbol,
      render: (p) => (
        <Link href={`/analysis/${p.symbol}`} className="flex flex-col rounded-lg leading-tight">
          <span className="text-sm font-medium text-foreground underline-offset-4 hover:underline">{p.symbol}</span>
          <span className="font-mono text-xs text-muted-foreground">{p.id}</span>
        </Link>
      ),
    },
    { key: "setup", header: "Setup", hideBelow: "md", sortValue: (p) => p.setupType, render: (p) => <span className="text-muted-foreground">{SETUP_TYPES[p.setupType].label}</span> },
    { key: "levels", header: "Entry / SL / Target", align: "right", render: (p) => <PlanLevelsInline {...p} /> },
    { key: "rr", header: "R:R", align: "right", hideBelow: "sm", sortValue: (p) => p.riskReward, render: (p) => formatRR(p.riskReward) },
    { key: "qty", header: "Qty", align: "right", hideBelow: "lg", sortValue: (p) => p.quantity, render: (p) => formatInt(p.quantity) },
    { key: "risk", header: "Risk ₹", align: "right", hideBelow: "lg", sortValue: (p) => p.riskAmount, render: (p) => <span className="text-bear">{formatInr(p.riskAmount, { decimals: false })}</span> },
    { key: "status", header: "Status", sortValue: (p) => ORDER.indexOf(p.status), render: (p) => <StatusBadge kind="plan" status={p.status} /> },
    { key: "signal", header: "Signal", hideBelow: "md", render: (p) => <SignalBadge signal={p.signal} /> },
    {
      key: "exec",
      header: "Execution",
      hideBelow: "xl",
      render: (p) => (p.linkedOrderId ? <span className="text-xs text-success">Order {p.linkedOrderId}</span> : <span className="text-xs text-muted-foreground">Proposed — no order</span>),
    },
    { key: "actions", header: <span className="sr-only">Actions</span>, align: "right", render: (p) => actions(p) },
  ];

  return (
    <PageFrame>
      <PageHeader
        title="Trade Plans"
        description="Proposed plans you have written against detected setups. A plan is not an order."
        meta={<SampleDataBadge asOf={asOf} />}
        actions={
          <ButtonLink href="/market-scanner" variant="primary">
            <ClipboardList /> New plan from a setup
          </ButtonLink>
        }
      />

      <LifecycleStrip highlight={["plan"]} />

      <StatGrid label="Plan figures">
        <Stat label="Open plans" value={open.length} hint="Pending, entry confirmed or active" />
        <Stat label="Awaiting trigger" value={plans.filter((p) => p.status === "pending").length} hint="No entry condition met yet" />
        <Stat label="Planned risk" value={formatInr(openRisk, { decimals: false })} hint="Lost if every open plan hits its stop" />
        <Stat label="Average R:R" value={avgRR ? formatRR(avgRR) : "—"} hint="Across open plans" />
      </StatGrid>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <Tabs
          ariaLabel="Plan status"
          value={tab}
          onChange={setTab}
          className="sm:flex-1"
          items={[
            { value: "all", label: "All", count: plans.length },
            ...ORDER.map((s) => ({ value: s, label: PLAN_STATUS[s].label, count: plans.filter((p) => p.status === s).length })),
          ]}
        />
        <ChoiceGroup
          ariaLabel="View mode"
          value={view}
          onChange={setView}
          options={[
            { value: "cards", label: "Cards", icon: <LayoutGrid className="size-3.5" aria-hidden /> },
            { value: "table", label: "Table", icon: <Rows3 className="size-3.5" aria-hidden /> },
          ]}
        />
      </div>

      {visible.length === 0 ? (
        <div data-slot="card" className="rounded-xl border bg-card">
          <Empty
            kind="scope"
            icon={ClipboardList}
            title={`No ${tab === "all" ? "" : PLAN_STATUS[tab].label.toLowerCase() + " "}plans`}
            description={tab === "all" ? "Write a plan from a detected setup in the scanner or on a stock's analysis page." : "Plans move between these states as triggers fire, orders are linked, or setups fail. Choose All to see every plan."}
          />
        </div>
      ) : view === "cards" ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {visible.map((p) => (
            <TradePlanCard key={p.id} plan={p} actions={actions(p)} />
          ))}
        </div>
      ) : (
        <DataTable columns={columns} rows={visible} rowKey={(p) => p.id} caption="Trade plans" />
      )}

      <Disclaimer />

      <Dialog
        open={!!confirmCancel}
        onClose={() => setConfirmCancel(null)}
        title={`Cancel ${confirmCancel?.id}?`}
        description={`${confirmCancel?.symbol} · ${confirmCancel ? SETUP_TYPES[confirmCancel.setupType].label : ""}. The plan will move to Cancelled. No orders are affected.`}
        size="sm"
        footer={
          <>
            <Button variant="outline" onClick={() => setConfirmCancel(null)}>Keep plan</Button>
            <Button
              variant="danger"
              onClick={() => {
                if (confirmCancel) {
                  setStatus(confirmCancel.id, "cancelled");
                  toast({ title: `${confirmCancel.id} cancelled`, tone: "info" });
                }
                setConfirmCancel(null);
              }}
            >
              Cancel plan
            </Button>
          </>
        }
      />
    </PageFrame>
  );
}
