import { describe, expect, it } from "vitest";
import { ApiError } from "./client";
import { errorReference } from "./error-reference";

describe("errorReference", () => {
  it("uses the request id of an API error", () => {
    expect(errorReference(new ApiError(502, "HTTP_502", "bad gateway", "req-1"))).toBe("req-1");
  });
  it("has no reference for an API error without a request id", () => {
    expect(errorReference(new ApiError(500, "HTTP_500", "oops"))).toBeUndefined();
  });
  it("uses the digest of a server error, never its message", () => {
    const e = Object.assign(new Error("secret detail"), { digest: "abc123" });
    expect(errorReference(e)).toBe("abc123");
  });
  it("has no reference for plain errors or non-errors", () => {
    expect(errorReference(new Error("x"))).toBeUndefined();
    expect(errorReference("boom")).toBeUndefined();
  });
});
