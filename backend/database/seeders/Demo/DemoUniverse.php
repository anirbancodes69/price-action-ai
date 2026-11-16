<?php

namespace Database\Seeders\Demo;

/**
 * SAMPLE DATA. Illustrative NSE universe ported from frontend/src/mocks/universe.ts. Prices are representative
 * values chosen for the demo, not quotes. Every row seeded from here is flagged `is_demo`.
 */
final class DemoUniverse
{
    /** Last trading date of the generated series (frontend SAMPLE_AS_OF). */
    public const AS_OF = '2026-11-13';

    public const SERIES_LENGTH = 240;

    /** Instrument name for index rows seeded as segment INDEX (NSE only; SENSEX is BSE and out of scope). */
    public const INDICES = [
        ['NIFTY 50', 'Nifty 50'],
        ['NIFTY BANK', 'Nifty Bank'],
        ['INDIA VIX', 'India VIX'],
    ];

    /**
     * [symbol, name, sector, last close, average daily volume, template].
     * Sector is kept for the later API/UI mapping; `instruments` has no sector column yet.
     *
     * @var list<array{0: string, 1: string, 2: string, 3: float, 4: int, 5: string}>
     */
    public const EQUITIES = [
        ['RELIANCE', 'Reliance Industries Ltd', 'Energy', 1486.4, 9_800_000, 'breakout'],
        ['TCS', 'Tata Consultancy Services Ltd', 'IT', 3124.6, 2_600_000, 'range'],
        ['HDFCBANK', 'HDFC Bank Ltd', 'Banking', 1002.35, 14_200_000, 'pullback'],
        ['ICICIBANK', 'ICICI Bank Ltd', 'Banking', 1411.8, 11_400_000, 'breakout'],
        ['INFY', 'Infosys Ltd', 'IT', 1528.15, 6_900_000, 'pullback'],
        ['BHARTIARTL', 'Bharti Airtel Ltd', 'Telecom', 2068.9, 5_200_000, 'breakout'],
        ['SBIN', 'State Bank of India', 'Banking', 948.55, 12_800_000, 'breakout'],
        ['ITC', 'ITC Ltd', 'FMCG', 412.3, 13_500_000, 'range'],
        ['LT', 'Larsen & Toubro Ltd', 'Infrastructure', 3918.75, 2_100_000, 'pullback'],
        ['AXISBANK', 'Axis Bank Ltd', 'Banking', 1214.4, 7_400_000, 'range'],
        ['KOTAKBANK', 'Kotak Mahindra Bank Ltd', 'Banking', 2116.2, 4_100_000, 'breakout'],
        ['HINDUNILVR', 'Hindustan Unilever Ltd', 'FMCG', 2442.05, 1_900_000, 'breakdown'],
        ['BAJFINANCE', 'Bajaj Finance Ltd', 'Financial Services', 1012.6, 6_300_000, 'pullback'],
        ['MARUTI', 'Maruti Suzuki India Ltd', 'Automobile', 16124.5, 520_000, 'breakout'],
        ['SUNPHARMA', 'Sun Pharmaceutical Industries Ltd', 'Pharma', 1712.85, 3_300_000, 'range'],
        ['TITAN', 'Titan Company Ltd', 'Consumer', 3712.4, 1_400_000, 'pullback'],
        ['ASIANPAINT', 'Asian Paints Ltd', 'Consumer', 2398.6, 1_600_000, 'breakdown'],
        ['ULTRACEMCO', 'UltraTech Cement Ltd', 'Cement', 12086.3, 320_000, 'range'],
        ['NTPC', 'NTPC Ltd', 'Utilities', 341.85, 15_600_000, 'breakout'],
        ['POWERGRID', 'Power Grid Corporation of India Ltd', 'Utilities', 292.4, 12_100_000, 'pullback'],
        ['TATASTEEL', 'Tata Steel Ltd', 'Metals', 168.72, 32_000_000, 'breakout'],
        ['JSWSTEEL', 'JSW Steel Ltd', 'Metals', 1148.9, 2_800_000, 'range'],
        ['HCLTECH', 'HCL Technologies Ltd', 'IT', 1556.3, 3_700_000, 'breakdown'],
        ['WIPRO', 'Wipro Ltd', 'IT', 251.45, 9_900_000, 'breakdown'],
        ['ADANIPORTS', 'Adani Ports and SEZ Ltd', 'Infrastructure', 1452.2, 3_100_000, 'breakout'],
        ['DRREDDY', 'Dr. Reddy\'s Laboratories Ltd', 'Pharma', 1258.65, 2_200_000, 'pullback'],
        ['EICHERMOT', 'Eicher Motors Ltd', 'Automobile', 6874.1, 620_000, 'breakout'],
        ['TRENT', 'Trent Ltd', 'Consumer', 4812.55, 980_000, 'breakdown'],
        ['BEL', 'Bharat Electronics Ltd', 'Capital Goods', 418.35, 18_400_000, 'pullback'],
        ['HAL', 'Hindustan Aeronautics Ltd', 'Capital Goods', 4706.2, 1_700_000, 'breakout'],
        ['DMART', 'Avenue Supermarts Ltd', 'Consumer', 4318.9, 420_000, 'range'],
        ['PIDILITIND', 'Pidilite Industries Ltd', 'Consumer', 1524.3, 780_000, 'pullback'],
        ['TVSMOTOR', 'TVS Motor Company Ltd', 'Automobile', 3486.75, 890_000, 'breakout'],
        ['PERSISTENT', 'Persistent Systems Ltd', 'IT', 5928.4, 610_000, 'breakdown'],
        ['POLYCAB', 'Polycab India Ltd', 'Capital Goods', 7214.6, 380_000, 'breakout'],
        ['CUMMINSIND', 'Cummins India Ltd', 'Capital Goods', 3918.2, 540_000, 'pullback'],
    ];
}
