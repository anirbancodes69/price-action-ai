"use client";

import { useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, CircleCheck, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Brand } from "@/components/layout/brand";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Disclaimer } from "@/components/data/disclaimer";
import { AuthHeading } from "@/features/auth/auth-heading";
import { ChoiceCard } from "./choice-card";
import { DATA_SOURCES, EXPERIENCE, STEPS, STYLES, UNIVERSES } from "./options";

interface State {
  experience: string | null;
  styles: string[];
  universe: string;
  dataSource: "demo" | "zerodha";
  capital: string;
  riskPct: string;
  maxPositions: string;
}

const INITIAL: State = { experience: null, styles: [], universe: "nifty100", dataSource: "demo", capital: "500000", riskPct: "1", maxPositions: "5" };

/** A step: heading then body, `gap-6` apart (design-standards §3). */
function Step({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-6">
      <AuthHeading title={title} description={description} />
      {children}
    </div>
  );
}

export function OnboardingFlow() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [s, setS] = useState<State>(INITIAL);
  const [zerodhaOpen, setZerodhaOpen] = useState(false);
  const [error, setError] = useState<string>();
  const current = STEPS[step];
  const isLast = current.id === "done";

  const validate = (): string | undefined => {
    if (current.id === "experience" && !s.experience) return "Select your experience level to continue.";
    if (current.id === "style" && s.styles.length === 0) return "Select at least one trading style.";
    if (current.id === "risk") {
      const r = Number(s.riskPct);
      if (!(Number(s.capital) >= 10000)) return "Capital should be at least ₹10,000.";
      if (!(r > 0 && r <= 5)) return "Risk per trade should be between 0.1% and 5%.";
    }
    return undefined;
  };

  const next = () => {
    const err = validate();
    setError(err);
    if (err) return;
    setStep((i) => Math.min(i + 1, STEPS.length - 1));
  };
  const back = () => {
    setError(undefined);
    setStep((i) => Math.max(i - 1, 0));
  };
  const skip = () => {
    setError(undefined);
    setStep((i) => i + 1);
  };

  const riskAmount = Math.round((Number(s.capital) * Number(s.riskPct)) / 100);

  const body: Record<string, ReactNode> = {
    welcome: (
      <div className="flex flex-col gap-6">
        <span className="flex size-11 items-center justify-center rounded-full bg-muted text-foreground">
          <Sparkles className="size-5" aria-hidden />
        </span>
        <AuthHeading
          title="Welcome to PriceAction AI"
          description="A few quick questions tailor the scanner, analysis and risk defaults to how you trade. It takes about a minute."
        />
        <ul className="flex flex-col gap-3 text-sm text-muted-foreground">
          {["Market structure and key levels for NSE stocks", "Setups explained with evidence, not bare signals", "Risk-first trade plans with defined invalidation"].map((t) => (
            <li key={t} className="flex items-center gap-3">
              <CircleCheck className="size-4 shrink-0 text-foreground" aria-hidden /> {t}
            </li>
          ))}
        </ul>
        <Disclaimer />
      </div>
    ),
    experience: (
      <Step title="How experienced are you?" description="We’ll adjust explanations and defaults to match.">
        <div role="radiogroup" aria-label="Trading experience" className="flex flex-col gap-3">
          {EXPERIENCE.map((c) => (
            <ChoiceCard key={c.value} choice={c} selected={s.experience === c.value} onSelect={() => setS({ ...s, experience: c.value })} />
          ))}
        </div>
      </Step>
    ),
    style: (
      <Step title="How do you trade?" description="Select all that apply.">
        <div role="group" aria-label="Trading style" className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {STYLES.map((c) => {
            const on = s.styles.includes(c.value);
            return (
              <ChoiceCard
                key={c.value}
                multi
                choice={c}
                selected={on}
                onSelect={() => setS({ ...s, styles: on ? s.styles.filter((x) => x !== c.value) : [...s.styles, c.value] })}
              />
            );
          })}
        </div>
      </Step>
    ),
    universe: (
      <Step title="Which stocks should we scan?" description="You can change this any time in Settings.">
        <div role="radiogroup" aria-label="Market universe" className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {UNIVERSES.map((c) => (
            <ChoiceCard key={c.value} choice={c} selected={s.universe === c.value} onSelect={() => setS({ ...s, universe: c.value })} badge={c.value === "nifty100" ? "Recommended" : undefined} />
          ))}
        </div>
      </Step>
    ),
    data: (
      <Step title="Choose a data source" description="Start in demo mode now and connect real data later.">
        <div role="radiogroup" aria-label="Data source" className="flex flex-col gap-3">
          {DATA_SOURCES.map((c) => (
            <ChoiceCard
              key={c.value}
              choice={c}
              selected={s.dataSource === c.value}
              badge={c.value === "zerodha" ? "Placeholder" : undefined}
              disabled={c.value === "zerodha"}
              onSelect={() => (c.value === "zerodha" ? setZerodhaOpen(true) : setS({ ...s, dataSource: "demo" }))}
            />
          ))}
        </div>
        <p className="text-xs text-muted-foreground">Demo mode uses illustrative sample prices. They are clearly labelled throughout the app.</p>
      </Step>
    ),
    risk: (
      <Step title="Set your risk preferences" description="Used to size proposed trade plans. You stay in control of every decision.">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Input label="Trading capital (₹)" inputMode="numeric" inputSize="lg" value={s.capital} onChange={(e) => setS({ ...s, capital: e.target.value })} />
          <Input label="Risk per trade (%)" inputMode="decimal" inputSize="lg" value={s.riskPct} onChange={(e) => setS({ ...s, riskPct: e.target.value })} />
          <Input label="Max open positions" inputMode="numeric" inputSize="lg" value={s.maxPositions} onChange={(e) => setS({ ...s, maxPositions: e.target.value })} />
        </div>
        <p className="rounded-lg bg-muted px-4 py-3 text-sm text-muted-foreground tabular-nums">
          A stop-out on any single plan would cost about{" "}
          <span className="font-medium text-foreground">₹{Number.isFinite(riskAmount) ? riskAmount.toLocaleString("en-IN") : "—"}</span>.
        </p>
      </Step>
    ),
    done: (
      <div className="flex flex-col gap-6">
        <span className="flex size-11 items-center justify-center rounded-full bg-success/10 text-success">
          <Check className="size-5" aria-hidden />
        </span>
        <AuthHeading title="You’re all set" description="Your workspace is ready in demo mode." />
        <dl data-slot="card" className="grid grid-cols-2 gap-x-6 gap-y-4 rounded-xl border bg-card px-5 py-4">
          {[
            ["Experience", EXPERIENCE.find((e) => e.value === s.experience)?.label ?? "—"],
            ["Style", s.styles.map((v) => STYLES.find((x) => x.value === v)?.label).join(", ") || "—"],
            ["Universe", UNIVERSES.find((u) => u.value === s.universe)?.label ?? "—"],
            ["Data", "Demo mode (sample data)"],
            ["Capital", `₹${Number(s.capital).toLocaleString("en-IN")}`],
            ["Risk per trade", `${s.riskPct}%`],
          ].map(([k, v]) => (
            <div key={k} className="flex min-w-0 flex-col gap-1">
              <dt className="text-2xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">{k}</dt>
              <dd className="text-sm text-foreground">{v}</dd>
            </div>
          ))}
        </dl>
      </div>
    ),
  };

  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <header className="flex h-16 items-center justify-between border-b px-6 sm:px-10">
        <Brand href="/onboarding" />
        <span className="text-sm text-muted-foreground tabular-nums">
          Step {step + 1} of {STEPS.length}
        </span>
      </header>

      <div className="mx-auto grid w-full max-w-5xl flex-1 grid-cols-1 gap-6 px-6 py-6 sm:px-10 md:grid-cols-[200px_minmax(0,1fr)] md:gap-12 md:py-12">
        {/* Progress */}
        <nav aria-label="Onboarding progress">
          <div className="h-1 overflow-hidden rounded-full bg-muted md:hidden" role="progressbar" aria-valuemin={1} aria-valuemax={STEPS.length} aria-valuenow={step + 1} aria-label="Onboarding progress">
            <div className="h-full rounded-full bg-primary transition-all duration-300" style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} />
          </div>
          <ol className="hidden flex-col gap-1 md:flex">
            {STEPS.map((st, i) => {
              const done = i < step;
              const active = i === step;
              return (
                <li key={st.id} className="flex items-center gap-3 py-1" aria-current={active ? "step" : undefined}>
                  <span
                    className={cn(
                      "flex size-6 shrink-0 items-center justify-center rounded-full border text-2xs font-semibold tabular-nums transition-colors",
                      done && "border-primary bg-primary text-primary-foreground",
                      active && "border-primary text-foreground ring-1 ring-primary",
                      !done && !active && "border-input text-muted-foreground",
                    )}
                  >
                    {done ? <Check className="size-3.5" /> : i + 1}
                  </span>
                  <span className={cn("text-sm", active ? "font-medium text-foreground" : done ? "text-muted-foreground" : "text-muted-foreground")}>
                    {st.label}
                    {st.optional && <span className="text-xs text-muted-foreground"> (optional)</span>}
                  </span>
                </li>
              );
            })}
          </ol>
        </nav>

        {/* Step body */}
        <div className="flex min-w-0 max-w-xl flex-col gap-6">
          <div key={current.id}>{body[current.id]}</div>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <div className="flex items-center gap-2 border-t pt-6">
            {step > 0 && !isLast && (
              <Button variant="ghost" onClick={back}>
                <ArrowLeft /> Back
              </Button>
            )}
            <div className="ml-auto flex items-center gap-2">
              {current.optional && (
                <Button variant="ghost" onClick={skip}>
                  Skip for now
                </Button>
              )}
              {isLast ? (
                <Button variant="primary" size="lg" onClick={() => router.push("/dashboard")}>
                  Go to dashboard <ArrowRight />
                </Button>
              ) : (
                <Button variant="primary" size="lg" onClick={next}>
                  {step === 0 ? "Get started" : "Continue"} <ArrowRight />
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      <Dialog
        open={zerodhaOpen}
        onClose={() => setZerodhaOpen(false)}
        title="Zerodha connection is coming soon"
        description="Broker authentication is not part of this release."
        size="sm"
        footer={
          <Button size="sm" variant="primary" onClick={() => setZerodhaOpen(false)}>
            Continue in demo mode
          </Button>
        }
      >
        <p className="leading-relaxed text-muted-foreground">
          When available, you will authorise PriceAction AI through Zerodha’s official Kite Connect login. We will never ask for your
          broker password here.
        </p>
      </Dialog>
    </div>
  );
}
