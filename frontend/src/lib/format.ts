/**
 * Number/date formatting. Locale and time zone are pinned (en-IN, Asia/Kolkata)
 * so server and client renders are identical and hydration-safe.
 */

const LOCALE = "en-IN";
const TZ = "Asia/Kolkata";

const priceFmt = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const intFmt = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 });

const compactFmt = new Intl.NumberFormat(LOCALE, {
  notation: "compact",
  maximumFractionDigits: 1,
});

export function formatPrice(n: number) {
  return priceFmt.format(n);
}

export function formatInr(n: number, opts: { decimals?: boolean } = {}) {
  const abs = Math.abs(n);
  const body = opts.decimals === false ? intFmt.format(abs) : priceFmt.format(abs);
  return `${n < 0 ? "−" : ""}₹${body}`;
}

/** Signed ₹ value for P&L: +₹1,234.00 / −₹56.00 */
export function formatSignedInr(n: number, opts: { decimals?: boolean } = {}) {
  if (n === 0) return formatInr(0, opts);
  return `${n > 0 ? "+" : ""}${formatInr(n, opts)}`;
}

/** Indian short-scale: 1.2 L, 3.4 Cr. */
export function formatLakhCrore(n: number) {
  const abs = Math.abs(n);
  const sign = n < 0 ? "−" : "";
  if (abs >= 1e7) return `${sign}₹${(abs / 1e7).toFixed(2)} Cr`;
  if (abs >= 1e5) return `${sign}₹${(abs / 1e5).toFixed(2)} L`;
  return `${sign}₹${intFmt.format(abs)}`;
}

export function formatInt(n: number) {
  return intFmt.format(n);
}

export function formatCompact(n: number) {
  return compactFmt.format(n);
}

export function formatPct(n: number, opts: { signed?: boolean; decimals?: number } = {}) {
  const { signed = true, decimals = 2 } = opts;
  const body = Math.abs(n).toFixed(decimals);
  if (!signed) return `${n < 0 ? "−" : ""}${body}%`;
  if (n > 0) return `+${body}%`;
  if (n < 0) return `−${body}%`;
  return `${body}%`;
}

export function formatSignedNumber(n: number) {
  const body = priceFmt.format(Math.abs(n));
  if (n > 0) return `+${body}`;
  if (n < 0) return `−${body}`;
  return body;
}

export function formatRR(rr: number) {
  return `1 : ${rr.toFixed(1)}`;
}

export function formatR(r: number) {
  return `${r > 0 ? "+" : r < 0 ? "−" : ""}${Math.abs(r).toFixed(1)}R`;
}

const dateFmt = new Intl.DateTimeFormat(LOCALE, {
  day: "2-digit",
  month: "short",
  year: "numeric",
  timeZone: TZ,
});
const shortDateFmt = new Intl.DateTimeFormat(LOCALE, {
  day: "2-digit",
  month: "short",
  timeZone: TZ,
});
const dateTimeFmt = new Intl.DateTimeFormat(LOCALE, {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: TZ,
});

/** Accepts "YYYY-MM-DD" or a full ISO timestamp. */
function toDate(value: string) {
  return value.length === 10 ? new Date(`${value}T12:00:00+05:30`) : new Date(value);
}

export function formatDate(value: string) {
  return dateFmt.format(toDate(value));
}

export function formatShortDate(value: string) {
  return shortDateFmt.format(toDate(value));
}

export function formatDateTime(value: string) {
  return `${dateTimeFmt.format(toDate(value))} IST`;
}
