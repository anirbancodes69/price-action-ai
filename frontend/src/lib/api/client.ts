/**
 * Browser client for the Laravel API (docs/architecture/04_API_SPECIFICATION.md §2).
 * Same-origin requests with the session cookie; unsafe methods carry the Sanctum CSRF token (`XSRF-TOKEN`
 * cookie → `X-XSRF-TOKEN` header). Errors are the API envelope `{error: {code, message, details?, request_id}}`.
 * No credentials or tokens are stored by this module: the session cookie is HttpOnly.
 */

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly requestId?: string,
    readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** Field errors of a 422 `VALIDATION_FAILED`, keyed by field. */
  get fieldErrors(): Record<string, string[]> {
    const fe = this.details?.field_errors;
    return fe && typeof fe === "object" ? (fe as Record<string, string[]>) : {};
  }
}

export interface ApiEnvelope<T, M = Record<string, unknown>> {
  data: T;
  meta: { request_id: string } & M;
}

const SAFE = new Set(["GET", "HEAD", "OPTIONS"]);

export function readXsrfToken(cookie: string = typeof document === "undefined" ? "" : document.cookie): string | undefined {
  const hit = cookie.split("; ").find((c) => c.startsWith("XSRF-TOKEN="));
  return hit ? decodeURIComponent(hit.slice("XSRF-TOKEN=".length)) : undefined;
}

async function ensureCsrf(force = false): Promise<void> {
  if (!force && readXsrfToken()) return;
  await fetch("/sanctum/csrf-cookie", { credentials: "same-origin", headers: { Accept: "application/json" } });
}

export function parseError(status: number, body: unknown, fallbackRequestId?: string | null): ApiError {
  const e = (body as { error?: { code?: string; message?: string; details?: Record<string, unknown>; request_id?: string } } | null)?.error;
  return new ApiError(
    status,
    e?.code ?? `HTTP_${status}`,
    e?.message ?? "The request failed.",
    e?.request_id ?? fallbackRequestId ?? undefined,
    e?.details,
  );
}

export async function apiRequest<T, M = Record<string, unknown>>(
  path: string,
  opts: { method?: string; body?: unknown; signal?: AbortSignal } = {},
): Promise<ApiEnvelope<T, M>> {
  const method = (opts.method ?? "GET").toUpperCase();
  const send = async () => {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (opts.body !== undefined) headers["Content-Type"] = "application/json";
    if (!SAFE.has(method)) {
      await ensureCsrf();
      const token = readXsrfToken();
      if (token) headers["X-XSRF-TOKEN"] = token;
    }
    return fetch(path, {
      method,
      credentials: "same-origin",
      headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
      signal: opts.signal,
    });
  };

  let res = await send();
  if (res.status === 419 && !SAFE.has(method)) {
    await ensureCsrf(true); // the CSRF cookie expired or was rotated: fetch a fresh one and retry once
    res = await send();
  }
  if (res.status === 204) return { data: undefined as T, meta: { request_id: res.headers.get("X-Request-Id") ?? "" } as ApiEnvelope<T, M>["meta"] };
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) throw parseError(res.status, body, res.headers.get("X-Request-Id"));
  return body as ApiEnvelope<T, M>;
}
