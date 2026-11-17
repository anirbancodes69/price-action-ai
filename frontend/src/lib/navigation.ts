import {
  BookOpenText,
  ClipboardList,
  FlaskConical,
  LayoutDashboard,
  LineChart,
  ListChecks,
  Radar,
  Settings,
  Wallet,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Extra path prefixes that should mark this item active. */
  match?: string[];
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const DEFAULT_ANALYSIS_SYMBOL = "RELIANCE";

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [{ label: "Dashboard", href: "/dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Market",
    items: [
      { label: "Market Scanner", href: "/market-scanner", icon: Radar },
      { label: "Stock Analysis", href: `/analysis/${DEFAULT_ANALYSIS_SYMBOL}`, icon: LineChart, match: ["/analysis"] },
      { label: "Watchlists", href: "/watchlists", icon: ListChecks },
    ],
  },
  {
    label: "Trading",
    items: [
      { label: "Trade Plans", href: "/trade-plans", icon: ClipboardList },
      { label: "Active trades", href: "/portfolio", icon: Wallet },
      { label: "Trading Journal", href: "/journal", icon: BookOpenText },
      { label: "Backtesting", href: "/backtesting", icon: FlaskConical },
    ],
  },
  {
    label: "System",
    items: [{ label: "Settings", href: "/settings", icon: Settings }],
  },
];

const ALL_ITEMS = NAV_GROUPS.flatMap((g) => g.items.map((i) => ({ ...i, group: g.label })));

export function isNavActive(item: NavItem, pathname: string) {
  const prefixes = [item.href, ...(item.match ?? [])];
  return prefixes.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/** Breadcrumb trail for a pathname, e.g. ["Market", "Stock Analysis", "RELIANCE"]. */
export function breadcrumbFor(pathname: string): { label: string; href?: string }[] {
  const item = ALL_ITEMS.find((i) => isNavActive(i, pathname));
  if (!item) return [{ label: "PriceAction AI" }];
  const trail: { label: string; href?: string }[] = [{ label: item.group }, { label: item.label, href: item.href }];
  if (pathname.startsWith("/analysis/")) {
    const symbol = decodeURIComponent(pathname.split("/")[2] ?? "");
    trail[1] = { label: item.label, href: "/market-scanner" };
    if (symbol) trail.push({ label: symbol });
  }
  return trail;
}
