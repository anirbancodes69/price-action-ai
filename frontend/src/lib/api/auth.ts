import { apiRequest } from "./client";

export interface ApiUser {
  id: string;
  email: string;
  email_verified: boolean;
  display_name: string | null;
  experience_level: string | null;
  timezone: string | null;
}

/** `POST /api/v1/auth/login` (A3). Throws `ApiError` (`INVALID_CREDENTIALS` 422, `ACCOUNT_SUSPENDED` 423, 429). */
export async function login(email: string, password: string, remember: boolean): Promise<ApiUser> {
  const res = await apiRequest<{ user: ApiUser }>("/api/v1/auth/login", { method: "POST", body: { email, password, remember } });
  return res.data.user;
}

/** `POST /api/v1/auth/logout` (A4). */
export async function logout(): Promise<void> {
  await apiRequest<void>("/api/v1/auth/logout", { method: "POST" });
}

/** `GET /api/v1/me` (A9). Throws `ApiError` 401 `UNAUTHENTICATED` without a session. */
export async function getMe(signal?: AbortSignal): Promise<ApiUser> {
  const res = await apiRequest<{ user: ApiUser }>("/api/v1/me", { signal });
  return res.data.user;
}

/** Message for a failed login, without revealing whether the email exists. */
export function loginErrorMessage(code: string, status: number): string {
  if (code === "INVALID_CREDENTIALS") return "Email or password is incorrect.";
  if (code === "ACCOUNT_SUSPENDED") return "This account is not active.";
  if (status === 429) return "Too many attempts. Wait a minute and try again.";
  if (status === 419) return "Your session expired. Reload the page and try again.";
  return "Sign in failed. Try again.";
}
