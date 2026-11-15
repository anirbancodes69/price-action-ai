import { describe, expect, it } from "vitest";
import {
  formatDate,
  formatInr,
  formatLakhCrore,
  formatPct,
  formatPrice,
  formatR,
  formatRR,
  formatSignedInr,
} from "./format";

describe("format (en-IN, Asia/Kolkata)", () => {
  it("formats prices with Indian digit grouping and 2 decimals", () => {
    expect(formatPrice(1495.5)).toBe("1,495.50");
    expect(formatPrice(1234567.891)).toBe("12,34,567.89");
  });

  it("formats INR with a true minus sign for negatives", () => {
    expect(formatInr(1000000)).toBe("₹10,00,000.00");
    expect(formatInr(-56)).toBe("−₹56.00");
    expect(formatInr(3089.5, { decimals: false })).toBe("₹3,090");
  });

  it("signs P&L values", () => {
    expect(formatSignedInr(1234)).toBe("+₹1,234.00");
    expect(formatSignedInr(-1234)).toBe("−₹1,234.00");
    expect(formatSignedInr(0)).toBe("₹0.00");
  });

  it("compacts to lakh and crore", () => {
    expect(formatLakhCrore(250000)).toBe("₹2.50 L");
    expect(formatLakhCrore(12500000)).toBe("₹1.25 Cr");
    expect(formatLakhCrore(-99999)).toBe("−₹99,999");
  });

  it("formats percentages, R:R and R-multiples", () => {
    expect(formatPct(1.234)).toBe("+1.23%");
    expect(formatPct(-0.5, { decimals: 1 })).toBe("−0.5%");
    expect(formatPct(0)).toBe("0.00%");
    expect(formatRR(2.44)).toBe("1 : 2.4");
    expect(formatR(2.3)).toBe("+2.3R");
    expect(formatR(-1)).toBe("−1.0R");
  });

  it("treats YYYY-MM-DD as an exchange (IST) date regardless of runner TZ", () => {
    expect(formatDate("2026-11-13")).toBe("13 Nov 2026");
  });
});
