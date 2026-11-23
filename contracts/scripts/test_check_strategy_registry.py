import shutil
import tempfile
import unittest
from pathlib import Path

import check_strategy_registry as chk

REPO = Path(__file__).resolve().parents[2]
FILES = (
    "contracts/strategy-registry.json",
    "contracts/api/openapi.yaml",
    "python-engine/app/domain/setups/types.py",
    "backend/app/Http/Requests/Api/V1/ScannerRequest.php",
    "backend/app/Http/Requests/Api/V1/TradePlanRequest.php",
    "frontend/src/lib/api/scanner.ts",
)


def copy_repo(dst: Path) -> None:
    for f in FILES:
        (dst / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / f, dst / f)


class StrategyRegistryTest(unittest.TestCase):
    def test_the_repository_is_consistent(self) -> None:
        self.assertEqual(chk.problems(REPO), [])

    def test_trend_continuation_is_unsupported_everywhere_but_the_stored_enum(self) -> None:
        c = chk.collect(REPO)
        self.assertNotIn("TREND_CONTINUATION", c["laravel scanner filter"])
        self.assertNotIn("TREND_CONTINUATION", c["laravel trade plan"])
        self.assertNotIn("TREND_CONTINUATION", c["engine SetupType"])

    def test_failed_breakdown_reclaim_is_in_every_validator(self) -> None:
        c = chk.collect(REPO)
        for k in ("laravel scanner filter", "laravel trade plan", "openapi SetupType", "frontend SETUP_TYPE"):
            self.assertIn("FAILED_BREAKDOWN_RECLAIM", c[k], k)

    def test_drift_in_a_validator_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            copy_repo(root)
            p = root / "backend/app/Http/Requests/Api/V1/ScannerRequest.php"
            p.write_text(p.read_text().replace("'FAILED_BREAKDOWN_RECLAIM',", "'TREND_CONTINUATION',"))
            found = chk.problems(root)
            self.assertTrue(any("scanner filter" in f for f in found), found)


if __name__ == "__main__":
    unittest.main()
