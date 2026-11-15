import { mockSource } from "./mock-source";
import type { DataSource } from "./source";

/**
 * The active data source. Swap `mockSource` for an HTTP-backed implementation
 * (e.g. selected via NEXT_PUBLIC_DATA_SOURCE) when the backend is available.
 */
export const data: DataSource = mockSource;

export type { DataSource, DashboardSummary } from "./source";
