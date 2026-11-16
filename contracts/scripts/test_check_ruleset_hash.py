import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "check_ruleset_hash.py"
REPO = HERE.parents[1]

TRD = """\
Ruleset ID: **`pa-core`**, version **`0.1.0`**. Every parameter is configurable.

## 6. Ruleset Parameter Registry (authoritative)

| Key | Default | Unit |
|---|---|---|
| `pivot.left_bars` | 2 | bars |
| `risk.min_rr` | 2.0 | ratio |
| `exit.structure_exit_enabled` | true | bool |
| `structure.break_buffer_pct` | 0.10 | % |

## 7. Outputs and vocabulary
"""
PARAMS = {"pivot.left_bars": 2, "risk.min_rr": 2.0, "exit.structure_exit_enabled": True, "structure.break_buffer_pct": 0.1}


def make_repo(root: Path, engine: dict, seeder: dict, trd: str = TRD) -> None:
    (root / "python-engine/rulesets/pa-core").mkdir(parents=True)
    (root / "backend/database/seeders/data").mkdir(parents=True)
    (root / "docs/trading").mkdir(parents=True)
    (root / "python-engine/rulesets/pa-core/0.1.0.json").write_text(json.dumps(engine))
    (root / "backend/database/seeders/data/pa-core-0.1.0.json").write_text(json.dumps(seeder))
    (root / "docs/trading/01_TRADING_METHODOLOGY.md").write_text(trd)


def run(engine: dict, seeder: dict, trd: str = TRD) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as d:
        make_repo(Path(d), engine, seeder, trd)
        return subprocess.run([sys.executable, "-I", str(SCRIPT), d], capture_output=True, text=True)


class RulesetCheck(unittest.TestCase):
    def test_identical_files_matching_the_doc_pass(self):
        r = run(PARAMS, PARAMS)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("sha256", r.stdout)

    def test_engine_and_seeder_difference_fails(self):
        r = run(PARAMS, PARAMS | {"pivot.left_bars": 3})
        self.assertEqual(r.returncode, 1)
        self.assertIn("pivot.left_bars", r.stdout)

    def test_value_differing_from_trd01_fails(self):
        changed = PARAMS | {"risk.min_rr": 2.5}
        r = run(changed, changed)
        self.assertEqual(r.returncode, 1)
        self.assertIn("risk.min_rr", r.stdout)

    def test_key_missing_from_or_extra_to_the_doc_fails(self):
        extra = PARAMS | {"zone.new_key": 1}
        r = run(extra, extra)
        self.assertEqual(r.returncode, 1)
        self.assertIn("zone.new_key is in the ruleset file but not in TRD-01", r.stdout)
        missing = {k: v for k, v in PARAMS.items() if k != "pivot.left_bars"}
        r = run(missing, missing)
        self.assertEqual(r.returncode, 1)
        self.assertIn("pivot.left_bars is in TRD-01", r.stdout)

    def test_equal_numbers_with_different_formatting_are_the_same_value(self):
        # 0.10 in the doc, 0.1 in the file; 2.0 in the doc, 2 in the file.
        r = run(PARAMS | {"risk.min_rr": 2}, PARAMS | {"risk.min_rr": 2})
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_seeder_without_engine_file_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            make_repo(root, PARAMS, PARAMS)
            (root / "backend/database/seeders/data/pa-core-0.2.0.json").write_text(json.dumps(PARAMS))
            r = subprocess.run([sys.executable, "-I", str(SCRIPT), d], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("pa-core-0.2.0.json has no engine ruleset", r.stdout)

    def test_real_repository_is_consistent(self):
        r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(REPO)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        # Pinned in backend/tests/Feature/Database/SeedersTest.php: the PHP seeder must produce the same hash.
        self.assertIn("6807859f97e9b52b7b3cc02312efacccc4b03660fe2c6cea498379667ff66deb", r.stdout)


if __name__ == "__main__":
    unittest.main()
