import { ApiError } from "./client";

/**
 * The id a person can quote to match an error with the logs (ENG-06): the API request id of an
 * `ApiError`, else the Next.js digest of a server error. Never the message or stack.
 */
export function errorReference(error: unknown): string | undefined {
  if (error instanceof ApiError) return error.requestId || undefined;
  if (error instanceof Error && "digest" in error) {
    const digest = (error as Error & { digest?: unknown }).digest;
    return digest ? String(digest) : undefined;
  }
  return undefined;
}
