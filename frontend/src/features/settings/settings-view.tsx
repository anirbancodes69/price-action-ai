"use client";

import { useState, type ReactNode } from "react";
import { Bell, Cable, Check, Database, Palette, ShieldCheck, SlidersHorizontal, UserRound, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { UserProfile } from "@/types";
import { PageFrame, PageHeader } from "@/components/layout/page-frame";
import { useTheme, type ThemePreference } from "@/components/layout/theme";
import { Avatar } from "@/components/layout/user-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Panel, RowList } from "@/components/ui/panel";
import { SectionLinks } from "@/components/ui/section-links";
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

/** One settings section: a boxed panel with its save action pinned to the foot. */
function Section({ title, description, children, footer }: { title: string; description?: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <Panel boxed title={title} hint={description} footer={footer ? <div className="flex w-full justify-end gap-2">{footer}</div> : undefined}>
      <div className="flex flex-col gap-4">{children}</div>
    </Panel>
  );
}

function ConnectionRow({ name, detail, status, action }: { name: string; detail: string; status: ReactNode; action: ReactNode }) {
  return (
    <li className="flex flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-card text-xs font-semibold text-muted-foreground ring-1 ring-border" aria-hidden>
        {name.slice(0, 2).toUpperCase()}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-medium text-foreground">{name}</p>
          {status}
        </div>
        <p className="text-xs text-muted-foreground">{detail}</p>
      </div>
      {action}
    </li>
  );
}

const THEMES: { value: ThemePreference; label: string; hint: string }[] = [
  { value: "light", label: "Light", hint: "Bright surfaces" },
  { value: "dark", label: "Dark", hint: "Default · low glare" },
  { value: "system", label: "Match system", hint: "Follows your OS setting" },
];

/** Miniature page drawn with the real tokens of a theme (a nested [data-theme] restates them). */
function ThemePreview({ theme }: { theme: "light" | "dark" }) {
  return (
    <span data-theme={theme} className="flex h-16 flex-1 gap-1.5 bg-background p-2" aria-hidden>
      <span className="w-3 rounded-sm bg-sidebar" />
      <span className="flex flex-1 flex-col gap-1 rounded-sm border bg-card p-1.5">
        <span className="h-1.5 w-10 rounded-full bg-foreground/70" />
        <span className="h-1.5 w-6 rounded-full bg-bull" />
        <span className="mt-auto h-2 w-8 rounded-full bg-cta" />
      </span>
    </span>
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
      <Section title="Profile" description="Your account details." footer={<Button variant="primary" onClick={() => save("Profile")}>Save changes</Button>}>
        <div className="flex items-center gap-3">
          <Avatar name={profile.name} className="size-12 text-sm" />
          <div>
            <p className="text-sm font-medium text-foreground">{profile.name}</p>
            <p className="text-xs text-muted-foreground">{user.plan}</p>
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input label="Full name" value={profile.name} onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))} />
          <Input label="Email" type="email" value={profile.email} onChange={(e) => setProfile((p) => ({ ...p, email: e.target.value }))} />
        </div>
      </Section>
    ),
    trading: (
      <Section title="Trading preferences" description="Defaults used by the scanner and analysis views." footer={<Button variant="primary" onClick={() => save("Preferences")}>Save changes</Button>}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Select label="Trading style" defaultValue="swing" options={[{ value: "swing", label: "Swing (days to weeks)" }, { value: "positional", label: "Positional (weeks to months)" }]} />
          <Select label="Default timeframe" defaultValue="1D" options={[{ value: "1D", label: "Daily" }, { value: "1W", label: "Weekly" }]} />
          <Select label="Market universe" defaultValue="nifty100" options={[{ value: "nifty50", label: "NIFTY 50" }, { value: "nifty100", label: "NIFTY 100" }, { value: "nifty200", label: "NIFTY 200" }, { value: "all", label: "All NSE equities" }]} />
          <Select label="Direction" defaultValue="long" options={[{ value: "long", label: "Long only (cash equity)" }, { value: "both", label: "Long and short (reference)" }]} />
        </div>
      </Section>
    ),
    risk: (
      <Section title="Risk management" description="Limits used to size proposed plans. Nothing here places orders." footer={<Button variant="primary" onClick={() => save("Risk settings")}>Save changes</Button>}>
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
        <RowList>
        <ConnectionRow
          name="Sample data"
          detail="Built-in illustrative dataset. Not live, not historical."
          status={<Badge tone="warning" dot>Active · sample data</Badge>}
          action={<Button variant="outline" disabled>In use</Button>}
        />
        <ConnectionRow
          name="NSE end-of-day"
          detail="Daily OHLCV after market close. Available in a later phase."
          status={<Badge tone="neutral">Coming soon</Badge>}
          action={<Button variant="outline" onClick={() => toast({ title: "Not available yet", tone: "info" })}>Configure</Button>}
        />
        </RowList>
      </Section>
    ),
    broker: (
      <Section title="Broker connection" description="Broker integrations are placeholders in this phase. No credentials are collected.">
        <RowList>
        <ConnectionRow
          name="Zerodha Kite"
          detail="Holdings, positions and order linking via Kite Connect."
          status={<Badge tone="neutral">Not connected</Badge>}
          action={<Button variant="outline" onClick={() => toast({ title: "Broker connection unavailable", description: "Zerodha integration will be added with the backend.", tone: "info" })}>Connect</Button>}
        />
        <ConnectionRow
          name="Upstox"
          detail="Planned integration."
          status={<Badge tone="neutral">Planned</Badge>}
          action={<Button variant="outline" disabled>Connect</Button>}
        />
        </RowList>
      </Section>
    ),
    notifications: (
      <Section title="Notifications" description="Choose what you hear about and where." footer={<Button variant="primary" onClick={() => save("Notification settings")}>Save changes</Button>}>
        <Switch checked={notif.triggers} onChange={(v) => setNotif((n) => ({ ...n, triggers: v }))} label="Entry triggers" description="When a setup on your watchlists meets its entry condition." />
        <Switch checked={notif.invalidations} onChange={(v) => setNotif((n) => ({ ...n, invalidations: v }))} label="Invalidations" description="When a setup or open plan is invalidated." />
        <Switch checked={notif.digest} onChange={(v) => setNotif((n) => ({ ...n, digest: v }))} label="End-of-day digest" description="Summary of scan results after market close." />
        <div className="h-px bg-border" role="separator" />
        <Switch checked={notif.email} onChange={(v) => setNotif((n) => ({ ...n, email: v }))} label="Email" />
        <Switch checked={notif.push} onChange={(v) => setNotif((n) => ({ ...n, push: v }))} label="Browser push" />
      </Section>
    ),
    appearance: (
      <Section title="Appearance" description="Dark is the default. Light and system modes use the same design tokens.">
        <div role="radiogroup" aria-label="Theme" className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {THEMES.map((t) => {
            const on = theme === t.value;
            return (
              <button
                key={t.value}
                type="button"
                role="radio"
                aria-checked={on}
                onClick={() => setTheme(t.value)}
                className={cn(
                  "flex flex-col overflow-hidden rounded-xl border bg-card text-left transition-colors",
                  on ? "border-primary ring-1 ring-primary" : "hover:border-input",
                )}
              >
                <span className="flex border-b">
                  {t.value === "system" ? (
                    <>
                      <ThemePreview theme="light" />
                      <ThemePreview theme="dark" />
                    </>
                  ) : (
                    <ThemePreview theme={t.value} />
                  )}
                </span>
                <span className="flex items-center justify-between gap-2 px-4 py-3">
                  <span className="flex flex-col gap-1">
                    <span className="text-sm font-medium text-foreground">{t.label}</span>
                    <span className="text-xs text-muted-foreground">{t.hint}</span>
                  </span>
                  {on && <Check className="size-4 text-foreground" aria-hidden />}
                </span>
              </button>
            );
          })}
        </div>
      </Section>
    ),
  };

  return (
    <PageFrame>
      <PageHeader title="Settings" description="Manage your profile, trading defaults and connections." />
      <div className="grid grid-cols-1 gap-6 md:grid-cols-[14rem_minmax(0,1fr)]">
        <SectionLinks
          ariaLabel="Settings sections"
          value={section}
          onChange={setSection}
          items={SECTIONS.map((x) => ({ value: x.id, label: x.label, icon: x.icon }))}
        />
        <div className="min-w-0 max-w-4xl">{content[section]}</div>
      </div>
    </PageFrame>
  );
}
