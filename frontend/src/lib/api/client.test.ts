import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiRequest, parseError, readXsrfToken } from "./client";
import { loginErrorMessage } from "./auth";

afterEach(() => vi.restoreAllMocks());

describe("readXsrfToken", () => {
  it("reads and decodes the Sanctum cookie", () => {
    expect(readXsrfToken("a=1; XSRF-TOKEN=ab%3Dcd; b=2")).toBe("ab=cd");
    expect(readXsrfToken("a=1")).toBeUndefined();
  });
});

describe("parseError", () => {
  it("reads the API error envelope", () => {
    const e = parseError(422, { error: { code: "VALIDATION_FAILED", message: "bad", details: { field_errors: { email: ["x"] } }, request_id: "r1" } });
    expect(e).toBeInstanceOf(ApiError);
    expect([e.status, e.code, e.message, e.requestId]).toEqual([422, "VALIDATION_FAILED", "bad", "r1"]);
    expect(e.fieldErrors).toEqual({ email: ["x"] });
  });
  it("falls back to the status and the response header when the body is not an envelope", () => {
    const e = parseError(502, "<html>", "hdr-1");
    expect([e.code, e.requestId, e.fieldErrors]).toEqual(["HTTP_502", "hdr-1", {}]);
  });
});

const res = (status: number, body: unknown = {}, headers: Record<string, string> = {}) =>
  new Response(status === 204 ? null : JSON.stringify(body), { status, headers });

describe("apiRequest", () => {
  it("sends credentials and JSON, and returns the envelope", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(res(200, { data: { x: 1 }, meta: { request_id: "r" } }));
    const out = await apiRequest<{ x: number }>("/api/v1/me");
    expect(out.data.x).toBe(1);
    const [path, init] = f.mock.calls[0]!;
    expect(path).toBe("/api/v1/me");
    expect(init).toMatchObject({ method: "GET", credentials: "same-origin" });
  });

  it("fetches the CSRF cookie before an unsafe request and sends the token header", async () => {
    vi.stubGlobal("document", { cookie: "" });
    const f = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).includes("csrf-cookie")) {
        (document as { cookie: string }).cookie = "XSRF-TOKEN=tok%2B1";
        return res(204);
      }
      return res(200, { data: {}, meta: { request_id: "r" } });
    });
    await apiRequest("/api/v1/auth/login", { method: "POST", body: { email: "a@b.co" } });
    expect(f.mock.calls.map((c) => String(c[0]))).toEqual(["/sanctum/csrf-cookie", "/api/v1/auth/login"]);
    const headers = (f.mock.calls[1]![1] as RequestInit).headers as Record<string, string>;
    expect(headers["X-XSRF-TOKEN"]).toBe("tok+1");
    expect(headers["Content-Type"]).toBe("application/json");
    expect((f.mock.calls[1]![1] as RequestInit).body).toBe('{"email":"a@b.co"}');
    vi.unstubAllGlobals();
  });

  it("retries once after a 419 with a fresh CSRF cookie", async () => {
    vi.stubGlobal("document", { cookie: "XSRF-TOKEN=old" });
    let posts = 0;
    const f = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).includes("csrf-cookie")) return res(204);
      posts += 1;
      return posts === 1 ? res(419, { error: { code: "CSRF_TOKEN_MISMATCH", message: "m", request_id: "r" } }) : res(204);
    });
    await expect(apiRequest("/api/v1/auth/logout", { method: "POST" })).resolves.toBeDefined();
    expect(posts).toBe(2);
    expect(f.mock.calls.filter((c) => String(c[0]).includes("csrf-cookie"))).toHaveLength(1);
    vi.unstubAllGlobals();
  });

  it("throws ApiError with the code and request id for an error response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(res(401, { error: { code: "UNAUTHENTICATED", message: "no", request_id: "r9" } }));
    await expect(apiRequest("/api/v1/me")).rejects.toMatchObject({ status: 401, code: "UNAUTHENTICATED", requestId: "r9" });
  });
});

describe("loginErrorMessage", () => {
  it("never reveals whether the email exists", () => {
    expect(loginErrorMessage("INVALID_CREDENTIALS", 422)).toBe("Email or password is incorrect.");
    expect(loginErrorMessage("ACCOUNT_SUSPENDED", 423)).toBe("This account is not active.");
    expect(loginErrorMessage("RATE_LIMITED", 429)).toMatch(/Too many attempts/);
    expect(loginErrorMessage("CSRF_TOKEN_MISMATCH", 419)).toMatch(/expired/);
    expect(loginErrorMessage("X", 500)).toBe("Sign in failed. Try again.");
  });
});
