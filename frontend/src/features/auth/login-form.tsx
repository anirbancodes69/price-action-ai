"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "./password-input";
import { validateEmail, validatePassword } from "./validation";

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [loading, setLoading] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const next = { email: validateEmail(email), password: validatePassword(password) };
    setErrors(next);
    if (next.email || next.password) return;
    setLoading(true);
    // Demo only — no authentication backend in Phase 1.
    setTimeout(() => router.push("/dashboard"), 700);
  };

  return (
    <div>
      <h1 className="text-xl font-semibold tracking-tight text-fg">Sign in</h1>
      <p className="mt-1 text-[13px] text-fg-muted">Welcome back. Continue to your analysis workspace.</p>

      <form onSubmit={submit} noValidate className="mt-7 flex flex-col gap-4">
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          inputSize="lg"
          leading={<Mail />}
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={errors.email}
        />
        <div className="flex flex-col gap-1.5">
          <PasswordInput
            label="Password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={errors.password}
          />
        </div>
        <div className="flex items-center justify-between">
          <Checkbox label="Remember me" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
          <Link href="/forgot-password" className="text-xs font-medium text-accent hover:underline">
            Forgot password?
          </Link>
        </div>
        <Button type="submit" variant="primary" size="lg" loading={loading} className="mt-2 w-full">
          Sign in {!loading && <ArrowRight />}
        </Button>
      </form>

      <div className="mt-4 rounded border border-border bg-subtle px-3 py-2.5 text-2xs leading-relaxed text-fg-subtle">
        Demo build: any valid email and password signs you in to a sample workspace. No account is created.
      </div>

      <p className="mt-8 text-center text-xs text-fg-muted">
        New to PriceAction AI?{" "}
        <Link href="/register" className="font-medium text-accent hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  );
}
