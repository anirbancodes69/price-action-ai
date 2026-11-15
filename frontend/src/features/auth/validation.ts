const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function validateEmail(v: string) {
  if (!v.trim()) return "Email is required";
  if (!EMAIL.test(v.trim())) return "Enter a valid email address";
  return undefined;
}

export function validatePassword(v: string, { strict = false } = {}) {
  if (!v) return "Password is required";
  if (strict) {
    if (v.length < 8) return "Use at least 8 characters";
    if (!/[A-Za-z]/.test(v) || !/\d/.test(v)) return "Include at least one letter and one number";
  }
  return undefined;
}

/** 0–4 heuristic strength score for the password meter. */
export function passwordStrength(v: string) {
  let s = 0;
  if (v.length >= 8) s++;
  if (v.length >= 12) s++;
  if (/[A-Z]/.test(v) && /[a-z]/.test(v)) s++;
  if (/\d/.test(v) && /[^A-Za-z0-9]/.test(v)) s++;
  return s;
}
