/**
 * Data source selection (ARC-04, ADR-016). `mock` (default) renders the sample data of `src/mocks`;
 * `http` talks to Laravel `/api/v1` through the same-origin proxy (`/api/*`, `/sanctum/*`, see `next.config.ts`).
 * Inlined at build time (`NEXT_PUBLIC_*`), so it is set when the app is built or started in dev.
 */
export const USE_HTTP = process.env.NEXT_PUBLIC_DATA_SOURCE === "http";
