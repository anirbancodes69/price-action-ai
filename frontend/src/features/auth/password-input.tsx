"use client";

import { forwardRef, useState } from "react";
import { Eye, EyeOff, Lock } from "lucide-react";
import { Input, type InputProps } from "@/components/ui/input";

export const PasswordInput = forwardRef<HTMLInputElement, Omit<InputProps, "type">>(function PasswordInput(props, ref) {
  const [show, setShow] = useState(false);
  return (
    <Input
      ref={ref}
      type={show ? "text" : "password"}
      inputSize="lg"
      leading={<Lock />}
      trailing={
        <button
          type="button"
          onClick={() => setShow((s) => !s)}
          className="rounded p-1.5 text-fg-subtle hover:text-fg"
          aria-label={show ? "Hide password" : "Show password"}
        >
          {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
        </button>
      }
      {...props}
    />
  );
});
