/**
 * SAMPLE DATA — illustrative NSE universe. Prices are representative values
 * chosen for the demo, not quotes. Do not treat as live or historical data.
 */
import type { Exchange, IndexMembership, Sector } from "@/types";

export type DemoTemplate = "breakout" | "pullback" | "range" | "breakdown";

export interface UniverseEntry {
  symbol: string;
  name: string;
  exchange: Exchange;
  sector: Sector;
  indices: IndexMembership[];
  /** Target last close for the generated series. */
  price: number;
  /** Typical daily volume (shares). */
  avgVolume: number;
  template: DemoTemplate;
}

const N50: IndexMembership[] = ["NIFTY 50"];
const NN50: IndexMembership[] = ["NIFTY NEXT 50"];
const MID: IndexMembership[] = ["NIFTY MIDCAP 100"];

export const SAMPLE_AS_OF = "2026-11-13";

export const UNIVERSE: UniverseEntry[] = [
  { symbol: "RELIANCE", name: "Reliance Industries Ltd", exchange: "NSE", sector: "Energy", indices: N50, price: 1486.4, avgVolume: 9_800_000, template: "breakout" },
  { symbol: "TCS", name: "Tata Consultancy Services Ltd", exchange: "NSE", sector: "IT", indices: N50, price: 3124.6, avgVolume: 2_600_000, template: "range" },
  { symbol: "HDFCBANK", name: "HDFC Bank Ltd", exchange: "NSE", sector: "Banking", indices: N50, price: 1002.35, avgVolume: 14_200_000, template: "pullback" },
  { symbol: "ICICIBANK", name: "ICICI Bank Ltd", exchange: "NSE", sector: "Banking", indices: N50, price: 1411.8, avgVolume: 11_400_000, template: "breakout" },
  { symbol: "INFY", name: "Infosys Ltd", exchange: "NSE", sector: "IT", indices: N50, price: 1528.15, avgVolume: 6_900_000, template: "pullback" },
  { symbol: "BHARTIARTL", name: "Bharti Airtel Ltd", exchange: "NSE", sector: "Telecom", indices: N50, price: 2068.9, avgVolume: 5_200_000, template: "breakout" },
  { symbol: "SBIN", name: "State Bank of India", exchange: "NSE", sector: "Banking", indices: N50, price: 948.55, avgVolume: 12_800_000, template: "breakout" },
  { symbol: "ITC", name: "ITC Ltd", exchange: "NSE", sector: "FMCG", indices: N50, price: 412.3, avgVolume: 13_500_000, template: "range" },
  { symbol: "LT", name: "Larsen & Toubro Ltd", exchange: "NSE", sector: "Infrastructure", indices: N50, price: 3918.75, avgVolume: 2_100_000, template: "pullback" },
  { symbol: "AXISBANK", name: "Axis Bank Ltd", exchange: "NSE", sector: "Banking", indices: N50, price: 1214.4, avgVolume: 7_400_000, template: "range" },
  { symbol: "KOTAKBANK", name: "Kotak Mahindra Bank Ltd", exchange: "NSE", sector: "Banking", indices: N50, price: 2116.2, avgVolume: 4_100_000, template: "breakout" },
  { symbol: "HINDUNILVR", name: "Hindustan Unilever Ltd", exchange: "NSE", sector: "FMCG", indices: N50, price: 2442.05, avgVolume: 1_900_000, template: "breakdown" },
  { symbol: "BAJFINANCE", name: "Bajaj Finance Ltd", exchange: "NSE", sector: "Financial Services", indices: N50, price: 1012.6, avgVolume: 6_300_000, template: "pullback" },
  { symbol: "MARUTI", name: "Maruti Suzuki India Ltd", exchange: "NSE", sector: "Automobile", indices: N50, price: 16124.5, avgVolume: 520_000, template: "breakout" },
  { symbol: "SUNPHARMA", name: "Sun Pharmaceutical Industries Ltd", exchange: "NSE", sector: "Pharma", indices: N50, price: 1712.85, avgVolume: 3_300_000, template: "range" },
  { symbol: "TITAN", name: "Titan Company Ltd", exchange: "NSE", sector: "Consumer", indices: N50, price: 3712.4, avgVolume: 1_400_000, template: "pullback" },
  { symbol: "ASIANPAINT", name: "Asian Paints Ltd", exchange: "NSE", sector: "Consumer", indices: N50, price: 2398.6, avgVolume: 1_600_000, template: "breakdown" },
  { symbol: "ULTRACEMCO", name: "UltraTech Cement Ltd", exchange: "NSE", sector: "Cement", indices: N50, price: 12086.3, avgVolume: 320_000, template: "range" },
  { symbol: "NTPC", name: "NTPC Ltd", exchange: "NSE", sector: "Utilities", indices: N50, price: 341.85, avgVolume: 15_600_000, template: "breakout" },
  { symbol: "POWERGRID", name: "Power Grid Corporation of India Ltd", exchange: "NSE", sector: "Utilities", indices: N50, price: 292.4, avgVolume: 12_100_000, template: "pullback" },
  { symbol: "TATASTEEL", name: "Tata Steel Ltd", exchange: "NSE", sector: "Metals", indices: N50, price: 168.72, avgVolume: 32_000_000, template: "breakout" },
  { symbol: "JSWSTEEL", name: "JSW Steel Ltd", exchange: "NSE", sector: "Metals", indices: N50, price: 1148.9, avgVolume: 2_800_000, template: "range" },
  { symbol: "HCLTECH", name: "HCL Technologies Ltd", exchange: "NSE", sector: "IT", indices: N50, price: 1556.3, avgVolume: 3_700_000, template: "breakdown" },
  { symbol: "WIPRO", name: "Wipro Ltd", exchange: "NSE", sector: "IT", indices: N50, price: 251.45, avgVolume: 9_900_000, template: "breakdown" },
  { symbol: "ADANIPORTS", name: "Adani Ports and SEZ Ltd", exchange: "NSE", sector: "Infrastructure", indices: N50, price: 1452.2, avgVolume: 3_100_000, template: "breakout" },
  { symbol: "DRREDDY", name: "Dr. Reddy's Laboratories Ltd", exchange: "NSE", sector: "Pharma", indices: N50, price: 1258.65, avgVolume: 2_200_000, template: "pullback" },
  { symbol: "EICHERMOT", name: "Eicher Motors Ltd", exchange: "NSE", sector: "Automobile", indices: N50, price: 6874.1, avgVolume: 620_000, template: "breakout" },
  { symbol: "TRENT", name: "Trent Ltd", exchange: "NSE", sector: "Consumer", indices: N50, price: 4812.55, avgVolume: 980_000, template: "breakdown" },
  { symbol: "BEL", name: "Bharat Electronics Ltd", exchange: "NSE", sector: "Capital Goods", indices: N50, price: 418.35, avgVolume: 18_400_000, template: "pullback" },
  { symbol: "HAL", name: "Hindustan Aeronautics Ltd", exchange: "NSE", sector: "Capital Goods", indices: NN50, price: 4706.2, avgVolume: 1_700_000, template: "breakout" },
  { symbol: "DMART", name: "Avenue Supermarts Ltd", exchange: "NSE", sector: "Consumer", indices: NN50, price: 4318.9, avgVolume: 420_000, template: "range" },
  { symbol: "PIDILITIND", name: "Pidilite Industries Ltd", exchange: "NSE", sector: "Consumer", indices: NN50, price: 1524.3, avgVolume: 780_000, template: "pullback" },
  { symbol: "TVSMOTOR", name: "TVS Motor Company Ltd", exchange: "NSE", sector: "Automobile", indices: NN50, price: 3486.75, avgVolume: 890_000, template: "breakout" },
  { symbol: "PERSISTENT", name: "Persistent Systems Ltd", exchange: "NSE", sector: "IT", indices: MID, price: 5928.4, avgVolume: 610_000, template: "breakdown" },
  { symbol: "POLYCAB", name: "Polycab India Ltd", exchange: "NSE", sector: "Capital Goods", indices: MID, price: 7214.6, avgVolume: 380_000, template: "breakout" },
  { symbol: "CUMMINSIND", name: "Cummins India Ltd", exchange: "NSE", sector: "Capital Goods", indices: MID, price: 3918.2, avgVolume: 540_000, template: "pullback" },
];
