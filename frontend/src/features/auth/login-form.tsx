"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { AuthHeading, DemoNotice, TextLink } from "./auth-heading";
import { PasswordInput } from "./password-input";
import { validateEmail, validatePassword } from "./validation";
import { ApiError } from "@/lib/api/client";
import { login, loginErrorMessage } from "@/lib/api/auth";
import { USE_HTTP } from "@/lib/api/config";

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
    if (!USE_HTTP) {
      // Mock data source: no authentication backend.
      setTimeout(() => router.push("/dashboard"), 700);
      return;
    }
    login(email.trim(), password, remember)
      .then(() => router.push("/dashboard"))
      .catch((err: unknown) => {
        const message = err instanceof ApiError ? loginErrorMessage(err.code, err.status) : "Sign in failed. Try again.";
        setErrors({ password: message });
        setLoading(false);
      });
  };

  return (
    <div className="flex flex-col gap-6">
      <AuthHeading title="Sign in" description="Welcome back. Continue to your analysis workspace." />

      <form onSubmit={submit} noValidate className="flex flex-col gap-4">
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
        <PasswordInput
          label="Password"
          autoComplete="current-password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.password}
        />
        <div className="flex items-center justify-between gap-3">
          <Checkbox label="Remember me" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
          <TextLink href="/forgot-password" className="text-sm">
            Forgot password?
          </TextLink>
        </div>
        <Button type="submit" variant="primary" size="lg" loading={loading} className="w-full">
          Sign in {!loading && <ArrowRight />}
        </Button>
      </form>

      <DemoNotice>Demo build: any valid email and password signs you in to a sample workspace. No account is created.</DemoNotice>

      <p className="text-center text-sm text-muted-foreground">
        New to PriceAction AI? <TextLink href="/register">Create an account</TextLink>
      </p>
    </div>
  );
}
