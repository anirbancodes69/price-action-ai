import { describe, expect, it } from "vitest";
import { passwordStrength, validateEmail, validatePassword } from "./validation";

describe("auth validation", () => {
  it("validates email", () => {
    expect(validateEmail("")).toBe("Email is required");
    expect(validateEmail("trader@")).toBe("Enter a valid email address");
    expect(validateEmail(" trader@example.in ")).toBeUndefined();
  });

  it("applies the strict password policy (ARC-06 §2)", () => {
    expect(validatePassword("", { strict: true })).toBe("Password is required");
    expect(validatePassword("abc123", { strict: true })).toBe("Use at least 8 characters");
    expect(validatePassword("abcdefgh", { strict: true })).toBe("Include at least one letter and one number");
    expect(validatePassword("abcdefg1", { strict: true })).toBeUndefined();
    expect(validatePassword("x")).toBeUndefined();
  });

  it("scores password strength 0–4", () => {
    expect(passwordStrength("short")).toBe(0);
    expect(passwordStrength("Abcdefgh1!xyz")).toBe(4);
  });
});
