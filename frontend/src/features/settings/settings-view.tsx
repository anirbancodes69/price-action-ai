"use client";

import { useState, type ReactNode } from "react";
import { Bell, Cable, Database, Palette, ShieldCheck, SlidersHorizontal, UserRound, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UserProfile } from "@/types";
import { PageContainer, PageHeader } from "@/components/layout/page-header";
import { useTheme, type ThemeName } from "@/components/layout/theme";
import { Avatar } from "@/components/layout/user-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel } from "@/components/ui/panel";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/toast";
import { Badge } from "@/components/data/badge";

type SectionId = "profile" | "trading" | "risk" | "data" | "broker" | "notifications" | "appearance";

const SECTIONS: { id: SectionId; label: string; icon: LucideIcon }[] = [
  { id: "profile", label: "Profile", icon: UserRound },
  { id: "trading", label: "Trading preferences", icon: SlidersHorizontal },
  { id: "risk", label: "Risk management", icon: ShieldCheck },
  { id: "data", label: "Market data", icon: Database },
  { id: "broker", label: "Broker connection", icon: Cable },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "appearance", label: "Appearance", icon: Palette },
];

function Section({ title, description, children, footer }: { title: string; description?: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <Panel>
      <header className="border-b border-border px-5 py-4">
        <h2 className="text-sm font-semibold text-fg">{title}</h2>
        {description && <p className="mt-0.5 text-xs text-fg-muted">{description}</p>}
      </header>
      <div className="flex flex-col gap-5 px-5 py-5">{children}</div>
      {footer && <footer className="flex justify-end gap-2 border-t border-border px-5 py-3">{footer}</footer>}
    </Panel>
  );
}

function ConnectionRow({ name, detail, status, action }: { name: string; detail: string; status: ReactNode; action: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 rounded border border-border bg-subtle px-4 py-3 sm:flex-row sm:items-center">
      <div className="flex size-9 shrink-0 items-center justify-center rounded border border-border bg-raised text-xs font-semibold text-fg-muted" aria-hidden>
        {name.slice(0, 2).toUpperCase()}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-[13px] font-medium text-fg">{name}</p>
          {status}
        </div>
        <p className="text-xs text-fg-subtle">{detail}</p>
      </div>
      {action}
    </div>
  );
}

export function SettingsView({ user }: { user: UserProfile }) {
  const toast = useToast();
  const [section, setSection] = useState<SectionId>("profile");
  const [theme, setTheme] = useTheme();
  const [profile, setProfile] = useState({ name: user.name, email: user.email });
  const [notif, setNotif] = useState({ triggers: true, invalidations: true, digest: false, email: true, push: false });
  const [risk, setRisk] = useState({ capital: "1000000", perTrade: "1", maxOpen: "6", maxDaily: "2" });
  const save = (what: string) => toast({ title: `${what} saved`, description: "Demo mode — stored for this session only." });

  const content: Record<SectionId, ReactNode> = {
    profile: (
      <Section title="Profile" description="Your account details." footer={<Button size="sm" variant="primary" onClick={() => save("Profile")}>Save changes</Button>}>
        <div className="flex items-center gap-3">
          <Avatar name={profile.name} className="size-12 text-sm" />
          <div>
            <p className="text-[13px] font-medium text-fg">{profile.name}</p>
            <p className="text-xs text-fg-subtle">{user.plan}</p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input label="Full name" value={profile.name} onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))} />
          <Input label="Email" type="email" value={profile.email} onChange={(e) => setProfile((p) => ({ ...p, email: e.target.value }))} />
        </div>
      </Section>
    ),
    trading: (
      <Section title="Trading preferences" description="Defaults used by the scanner and analysis views." footer={<Button size="sm" variant="primary" onClick={() => save("Preferences")}>Save changes</Button>}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Select label="Trading style" defaultValue="swing" options={[{ value: "swing", label: "Swing (days to weeks)" }, { value: "positional", label: "Positional (weeks to months)" }]} />
          <Select label="Default timeframe" defaultValue="1D" options={[{ value: "1D", label: "Daily" }, { value: "1W", label: "Weekly" }]} />
          <Select label="Market universe" defaultValue="nifty100" options={[{ value: "nifty50", label: "NIFTY 50" }, { value: "nifty100", label: "NIFTY 100" }, { value: "nifty200", label: "NIFTY 200" }, { value: "all", label: "All NSE equities" }]} />
          <Select label="Direction" defaultValue="long" options={[{ value: "long", label: "Long only (cash equity)" }, { value: "both", label: "Long and short (reference)" }]} />
        </div>
      </Section>
    ),
    risk: (
      <Section title="Risk management" description="Limits used to size proposed plans. Nothing here places orders." footer={<Button size="sm" variant="primary" onClick={() => save("Risk settings")}>Save changes</Button>}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input label="Trading capital (₹)" inputMode="numeric" value={risk.capital} onChange={(e) => setRisk((r) => ({ ...r, capital: e.target.value }))} />
          <Input label="Max risk per trade (%)" inputMode="decimal" value={risk.perTrade} onChange={(e) => setRisk((r) => ({ ...r, perTrade: e.target.value }))} hint={`≈ ₹${Math.round((Number(risk.capital) * Number(risk.perTrade)) / 100).toLocaleString("en-IN")} per trade`} />
          <Input label="Max open positions" inputMode="numeric" value={risk.maxOpen} onChange={(e) => setRisk((r) => ({ ...r, maxOpen: e.target.value }))} />
          <Input label="Max portfolio heat (%)" inputMode="decimal" value={risk.maxDaily} onChange={(e) => setRisk((r) => ({ ...r, maxDaily: e.target.value }))} hint="Combined open risk to stops" />
        </div>
        <Switch checked label="Require a stop-loss on every plan" description="Plans without a stop cannot be saved." onChange={() => toast({ title: "Stop-loss requirement is always on", tone: "info" })} />
      </Section>
    ),
    data: (
      <Section title="Market data connection" description="Where prices and history come from.">
        <ConnectionRow
          name="Sample data"
          detail="Built-in illustrative dataset. Not live, not historical."
          status={<Badge tone="warn" dot>Active</Badge>}
          action={<Button size="sm" variant="outline" disabled>In use</Button>}
        />
        <ConnectionRow
          name="NSE end-of-day"
          detail="Daily OHLCV after market close. Available in a later phase."
          status={<Badge tone="neutral">Coming soon</Badge>}
          action={<Button size="sm" variant="outline" onClick={() => toast({ title: "Not available yet", tone: "info" })}>Configure</Button>}
        />
      </Section>
    ),
    broker: (
      <Section title="Broker connection" description="Broker integrations are placeholders in this phase. No credentials are collected.">
        <ConnectionRow
          name="Zerodha Kite"
          detail="Holdings, positions and order linking via Kite Connect."
          status={<Badge tone="neutral">Not connected</Badge>}
          action={<Button size="sm" variant="secondary" onClick={() => toast({ title: "Broker connection unavailable", description: "Zerodha integration will be added with the backend.", tone: "info" })}>Connect</Button>}
        />
        <ConnectionRow
          name="Upstox"
          detail="Planned integration."
          status={<Badge tone="neutral">Planned</Badge>}
          action={<Button size="sm" variant="outline" disabled>Connect</Button>}
        />
      </Section>
    ),
    notifications: (
      <Section title="Notifications" description="Choose what you hear about and where." footer={<Button size="sm" variant="primary" onClick={() => save("Notification settings")}>Save changes</Button>}>
        <Switch checked={notif.triggers} onChange={(v) => setNotif((n) => ({ ...n, triggers: v }))} label="Entry triggers" description="When a setup on your watchlists meets its entry condition." />
        <Switch checked={notif.invalidations} onChange={(v) => setNotif((n) => ({ ...n, invalidations: v }))} label="Invalidations" description="When a setup or open plan is invalidated." />
        <Switch checked={notif.digest} onChange={(v) => setNotif((n) => ({ ...n, digest: v }))} label="End-of-day digest" description="Summary of scan results after market close." />
        <div className="h-px bg-border" />
        <Switch checked={notif.email} onChange={(v) => setNotif((n) => ({ ...n, email: v }))} label="Email" />
        <Switch checked={notif.push} onChange={(v) => setNotif((n) => ({ ...n, push: v }))} label="Browser push" />
      </Section>
    ),
    appearance: (
      <Section title="Appearance" description="Dark is the primary theme. Light is an early preview.">
        <div role="radiogroup" aria-label="Theme" className="grid grid-cols-2 gap-3 sm:max-w-md">
          {(["dark", "light"] as ThemeName[]).map((t) => (
            <button
              key={t}
              type="button"
              role="radio"
              aria-checked={theme === t}
              onClick={() => setTheme(t)}
              className={cn("rounded-md border p-2 text-left transition-colors", theme === t ? "border-accent ring-2 ring-accent/25" : "border-border hover:border-border-strong")}
            >
              <span className={cn("flex h-16 flex-col gap-1 rounded p-2", t === "dark" ? "bg-[#0B1120]" : "bg-[#F6F8FB]")} aria-hidden>
                <span className={cn("h-1.5 w-10 rounded-full", t === "dark" ? "bg-[#334159]" : "bg-[#CBD5E1]")} />
                <span className="h-1.5 w-6 rounded-full bg-[#22C55E]" />
                <span className="h-1.5 w-8 rounded-full bg-[#6366F1]" />
              </span>
              <span className="mt-2 block text-xs font-medium text-fg">{t === "dark" ? "Dark" : "Light (preview)"}</span>
            </button>
          ))}
        </div>
      </Section>
    ),
  };

  return (
    <PageContainer className="max-w-[1200px]">
      <PageHeader title="Settings" description="Manage your profile, trading defaults and connections." />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-[220px_minmax(0,1fr)] lg:gap-6">
        <nav aria-label="Settings sections" className="no-scrollbar -mx-3 flex gap-1 overflow-x-auto px-3 md:mx-0 md:flex-col md:px-0">
          {SECTIONS.map((s) => {
            const Icon = s.icon;
            const on = section === s.id;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => setSection(s.id)}
                aria-current={on ? "page" : undefined}
                className={cn(
                  "flex h-8 shrink-0 items-center gap-2 rounded px-2.5 text-[13px] font-medium transition-colors",
                  on ? "bg-accent/12 text-fg" : "text-fg-muted hover:bg-hover hover:text-fg",
                )}
              >
                <Icon className={cn("size-4", on ? "text-accent" : "text-fg-subtle")} aria-hidden />
                {s.label}
              </button>
            );
          })}
        </nav>
        <div className="min-w-0">{content[section]}</div>
      </div>
    </PageContainer>
  );
}
