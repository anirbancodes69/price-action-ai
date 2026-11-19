import { describe, expect, it } from "vitest";
import { mapWatchlist } from "./watchlists";

describe("mapWatchlist", () => {
  it("keeps the list id and name and flattens the items to symbols in order", () => {
    expect(
      mapWatchlist({
        id: "w1",
        name: "Breakouts",
        sort_order: 1,
        items: [
          { symbol: "RELIANCE", added_at: "2026-11-18T10:00:00+05:30" },
          { symbol: "TCS", added_at: "2026-11-18T10:01:00+05:30" },
        ],
      }),
    ).toEqual({ id: "w1", name: "Breakouts", symbols: ["RELIANCE", "TCS"] });
  });

  it("maps an empty list", () => {
    expect(
      mapWatchlist({ id: "w2", name: "Empty", sort_order: 0, items: [] })
        .symbols,
    ).toEqual([]);
  });
});
