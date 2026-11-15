"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowLeft, MailCheck, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { validateEmail } from "./validation";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const err = validateEmail(email);
    setError(err);
    if (err) return;
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setSent(true);
    }, 700);
  };

  if (sent) {
    return (
      <div className="flex flex-col items-start">
        <span className="flex size-10 items-center justify-center rounded-md border border-bull/30 bg-bull/10 text-bull">
          <MailCheck className="size-5" aria-hidden />
        </span>
        <h1 className="mt-5 text-xl font-semibold tracking-tight text-fg">Check your inbox</h1>
        <p className="mt-1.5 text-[13px] leading-relaxed text-fg-muted">
          If an account exists for <span className="font-medium text-fg">{email}</span>, you&apos;ll receive a link to reset your password.
          The link expires in 30 minutes.
        </p>
        <ol className="mt-5 flex list-decimal flex-col gap-1.5 pl-4 text-xs text-fg-muted">
          <li>Open the email from PriceAction AI.</li>
          <li>Click “Reset password” and choose a new password.</li>
          <li>Sign in with your new password.</li>
        </ol>
        <p className="mt-5 rounded border border-border bg-subtle px-3 py-2 text-2xs text-fg-subtle">Demo build: no email is actually sent.</p>
        <div className="mt-6 flex w-full flex-col gap-2">
          <Button variant="secondary" size="lg" className="w-full" onClick={() => setSent(false)}>
            Use a different email
          </Button>
          <Link href="/login" className="mt-2 inline-flex items-center justify-center gap-1.5 text-xs font-medium text-accent hover:underline">
            <ArrowLeft className="size-3.5" /> Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-xl font-semibold tracking-tight text-fg">Reset your password</h1>
      <p className="mt-1 text-[13px] text-fg-muted">Enter the email you signed up with and we&apos;ll send reset instructions.</p>
      <form onSubmit={submit} noValidate className="mt-7 flex flex-col gap-4">
        <Input label="Email" type="email" autoComplete="email" inputSize="lg" leading={<Mail />} placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} error={error} />
        <Button type="submit" variant="primary" size="lg" loading={loading} className="w-full">
          Send reset link
        </Button>
      </form>
      <Link href="/login" className="mt-8 flex items-center justify-center gap-1.5 text-xs font-medium text-accent hover:underline">
        <ArrowLeft className="size-3.5" /> Back to sign in
      </Link>
    </div>
  );
}
