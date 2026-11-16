"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Mail, UserRound } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { AuthHeading, TextLink } from "./auth-heading";
import { PasswordInput } from "./password-input";
import { passwordStrength, validateEmail, validatePassword } from "./validation";

type Field = "name" | "email" | "password" | "confirm" | "terms";

const STRENGTH = ["Too weak", "Weak", "Fair", "Good", "Strong"];
const STRENGTH_TONE = ["bg-destructive", "bg-destructive", "bg-warning", "bg-success", "bg-success"];

export function RegisterForm() {
  const router = useRouter();
  const [v, setV] = useState({ name: "", email: "", password: "", confirm: "", terms: false });
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({});
  const [loading, setLoading] = useState(false);
  const strength = passwordStrength(v.password);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const next: Partial<Record<Field, string>> = {
      name: v.name.trim().length < 2 ? "Enter your full name" : undefined,
      email: validateEmail(v.email),
      password: validatePassword(v.password, { strict: true }),
      confirm: !v.confirm ? "Confirm your password" : v.confirm !== v.password ? "Passwords do not match" : undefined,
      terms: v.terms ? undefined : "You must accept the terms to continue",
    };
    setErrors(next);
    if (Object.values(next).some(Boolean)) return;
    setLoading(true);
    setTimeout(() => router.push("/onboarding"), 700);
  };

  return (
    <div className="flex flex-col gap-6">
      <AuthHeading title="Create your account" description="Start with sample data. Connect real market data later." />

      <form onSubmit={submit} noValidate className="flex flex-col gap-4">
        <Input label="Full name" autoComplete="name" inputSize="lg" leading={<UserRound />} value={v.name} onChange={(e) => setV({ ...v, name: e.target.value })} error={errors.name} />
        <Input label="Email" type="email" autoComplete="email" inputSize="lg" leading={<Mail />} placeholder="you@example.com" value={v.email} onChange={(e) => setV({ ...v, email: e.target.value })} error={errors.email} />
        <div className="flex flex-col gap-1">
          <PasswordInput label="Password" autoComplete="new-password" value={v.password} onChange={(e) => setV({ ...v, password: e.target.value })} error={errors.password} />
          {v.password && (
            <div className="flex items-center gap-2" aria-live="polite">
              <div className="flex flex-1 gap-1" aria-hidden>
                {[0, 1, 2, 3].map((i) => (
                  <span key={i} className={cn("h-1 flex-1 rounded-full", i < strength ? STRENGTH_TONE[strength] : "bg-muted")} />
                ))}
              </div>
              <span className="text-xs text-muted-foreground">Strength: {STRENGTH[strength]}</span>
            </div>
          )}
        </div>
        <PasswordInput label="Confirm password" autoComplete="new-password" value={v.confirm} onChange={(e) => setV({ ...v, confirm: e.target.value })} error={errors.confirm} />
        <Checkbox
          checked={v.terms}
          onChange={(e) => setV({ ...v, terms: e.target.checked })}
          error={errors.terms}
          label={
            <>
              I agree to the <span className="font-medium text-foreground">Terms of Service</span> and <span className="font-medium text-foreground">Risk Disclosure</span>, and understand
              that analysis is not investment advice.
            </>
          }
        />
        <Button type="submit" variant="primary" size="lg" loading={loading} className="w-full">
          Create account {!loading && <ArrowRight />}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account? <TextLink href="/login">Sign in</TextLink>
      </p>
    </div>
  );
}
