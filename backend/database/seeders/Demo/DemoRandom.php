<?php

namespace Database\Seeders\Demo;

/**
 * Port of frontend/src/mocks/rng.ts. All arithmetic is kept to unsigned 32 bits so the sequence is identical
 * to JavaScript's `Math.imul` / `>>> 0` semantics (PHP integers are 64-bit and would otherwise overflow to float).
 */
final class DemoRandom
{
    private const MASK = 0xFFFFFFFF;

    private int $a;

    public function __construct(int $seed)
    {
        $this->a = $seed & self::MASK;
    }

    /** Equivalent of Math.imul, returned as an unsigned 32-bit value. */
    public static function imul(int $a, int $b): int
    {
        $a &= self::MASK;
        $b &= self::MASK;
        $ah = $a >> 16;
        $al = $a & 0xFFFF;
        $bh = $b >> 16;
        $bl = $b & 0xFFFF;

        return (($al * $bl) + ((($ah * $bl + $al * $bh) & 0xFFFF) << 16)) & self::MASK;
    }

    /** mulberry32: next float in [0, 1). */
    public function next(): float
    {
        $this->a = ($this->a + 0x6D2B79F5) & self::MASK;
        $t = $this->a;
        $t = self::imul($t ^ ($t >> 15), $t | 1);
        $t ^= ($t + self::imul($t ^ ($t >> 7), $t | 61)) & self::MASK;

        return (($t ^ ($t >> 14)) & self::MASK) / 4294967296;
    }

    /** FNV-1a 32-bit over the string's UTF-16 code units (ASCII symbols only here). */
    public static function hashString(string $s): int
    {
        $h = 2166136261;
        $n = strlen($s);
        for ($i = 0; $i < $n; $i++) {
            $h ^= ord($s[$i]);
            $h = self::imul($h, 16777619);
        }

        return $h & self::MASK;
    }

    /** Round to NSE tick size (₹0.05), with JavaScript Math.round semantics (ties toward +infinity). */
    public static function toTick(float $n): float
    {
        return floor($n * 20 + 0.5) / 20;
    }
}
