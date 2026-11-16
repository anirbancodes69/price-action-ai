"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowLeft, MailCheck, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AuthHeading, DemoNotice } from "./auth-heading";
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
      <div className="flex flex-col items-start gap-6">
        <span className="flex size-10 items-center justify-center rounded-full bg-success/10 text-success">
          <MailCheck className="size-5" aria-hidden />
        </span>
        <AuthHeading
          title="Check your inbox"
          description={
            <>
              If an account exists for <span className="font-medium text-foreground">{email}</span>, you&apos;ll receive a link to reset your
              password. The link expires in 30 minutes.
            </>
          }
        />
        <ol className="flex list-decimal flex-col gap-1 pl-4 text-sm text-muted-foreground">
          <li>Open the email from PriceAction AI.</li>
          <li>Click “Reset password” and choose a new password.</li>
          <li>Sign in with your new password.</li>
        </ol>
        <DemoNotice>Demo build: no email is actually sent.</DemoNotice>
        <div className="flex w-full flex-col gap-3">
          <Button variant="outline" size="lg" className="w-full" onClick={() => setSent(false)}>
            Use a different email
          </Button>
          <Link href="/login" className="inline-flex items-center justify-center gap-1.5 rounded-lg text-sm font-medium text-foreground underline-offset-4 hover:underline">
            <ArrowLeft className="size-3.5" /> Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <AuthHeading title="Reset your password" description="Enter the email you signed up with and we'll send reset instructions." />
      <form onSubmit={submit} noValidate className="flex flex-col gap-4">
        <Input label="Email" type="email" autoComplete="email" inputSize="lg" leading={<Mail />} placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} error={error} />
        <Button type="submit" variant="primary" size="lg" loading={loading} className="w-full">
          Send reset link
        </Button>
      </form>
      <Link href="/login" className="flex items-center justify-center gap-1.5 rounded-lg text-sm font-medium text-foreground underline-offset-4 hover:underline">
        <ArrowLeft className="size-3.5" /> Back to sign in
      </Link>
    </div>
  );
}
