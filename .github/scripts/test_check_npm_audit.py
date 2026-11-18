import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check_npm_audit.py"
GHSA = "GHSA-fc5q-39xc-vjpf"


def report(severity: str = "high", ghsa: str = GHSA) -> dict:
    adv = {"source": 1, "name": "picomatch", "severity": severity, "title": "ReDoS", "url": f"https://github.com/advisories/{ghsa}"}
    return {
        "vulnerabilities": {
            "picomatch": {"severity": severity, "via": [adv]},
            "tinyglobby": {"severity": severity, "via": ["picomatch"]},  # transitive: no advisory of its own
        }
    }


def waiver(**over: str) -> dict:
    base = {"id": GHSA, "package": "picomatch", "justification": "dev tooling only", "owner": "owner", "expires": "2026-12-18"}
    return {"exceptions": [base | over]}


def run(audit: dict, config: dict, today: str = "2026-11-18") -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "a.json").write_text(json.dumps(audit))
        (Path(d) / "e.json").write_text(json.dumps(config))
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), str(Path(d) / "a.json"), str(Path(d) / "e.json"), today], capture_output=True, text=True
        )


class AuditExceptions(unittest.TestCase):
    def test_unexcepted_high_advisory_fails(self):
        r = run(report(), {"exceptions": []})
        self.assertEqual(r.returncode, 1)
        self.assertIn(GHSA, r.stdout)

    def test_valid_exception_passes_and_is_reported(self):
        r = run(report(), waiver())
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("excepted " + GHSA, r.stdout)

    def test_expired_exception_fails(self):
        r = run(report(), waiver(), today="2026-12-19")
        self.assertEqual(r.returncode, 1)
        self.assertIn("expired on 2026-12-18", r.stdout)

    def test_incomplete_exception_fails(self):
        r = run(report(), waiver(justification=" "))
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing justification", r.stdout)

    def test_a_different_advisory_is_not_covered(self):
        r = run(report(ghsa="GHSA-aaaa-bbbb-cccc"), waiver())
        self.assertEqual(r.returncode, 1)
        self.assertIn("GHSA-aaaa-bbbb-cccc", r.stdout)

    def test_moderate_advisories_do_not_block(self):
        self.assertEqual(run(report(severity="moderate"), {"exceptions": []}).returncode, 0)

    def test_unused_exception_is_a_note_not_a_failure(self):
        r = run({"vulnerabilities": {}}, waiver())
        self.assertEqual(r.returncode, 0)
        self.assertIn("matches no current finding", r.stdout)

    def test_audit_that_could_not_run_fails(self):
        self.assertEqual(run({"error": {"code": "ENOAUDIT"}}, {"exceptions": []}).returncode, 1)


if __name__ == "__main__":
    unittest.main()
