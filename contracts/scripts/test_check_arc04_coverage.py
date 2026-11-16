import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "check_arc04_coverage.py"

DOC = """\
| # | Method & path | Auth |
|---|---|---|
| A1 | `GET /sanctum/csrf-cookie` | none |
| A2 | `POST /api/v1/auth/register` | none |
| N5 | `GET /api/v1/analysis/{symbol}` | session |

**R1** `POST /api/v1/risk/calculate` — Auth: session.
"""

SPEC = {
    "paths": {
        "/sanctum/csrf-cookie": {"get": {"x-arc04-id": "A1", "operationId": "a1"}},
        "/api/v1/auth/register": {"post": {"x-arc04-id": "A2", "operationId": "a2"}},
        "/api/v1/analysis/{symbol}": {"get": {"x-arc04-id": "N5", "operationId": "n5"}},
        "/api/v1/risk/calculate": {"post": {"x-arc04-id": "R1", "operationId": "r1"}},
    }
}


def run(spec: dict, doc: str = DOC) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "spec.json").write_text(json.dumps(spec))
        (Path(d) / "arc04.md").write_text(doc)
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), str(Path(d) / "spec.json"), str(Path(d) / "arc04.md")],
            capture_output=True, text=True,
        )


class CoverageCheck(unittest.TestCase):
    def test_matching_documents_pass(self):
        r = run(SPEC)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("4 endpoints", r.stdout)

    def test_endpoint_missing_from_spec_fails(self):
        spec = copy.deepcopy(SPEC)
        del spec["paths"]["/api/v1/risk/calculate"]
        r = run(spec)
        self.assertEqual(r.returncode, 1)
        self.assertIn("R1", r.stdout)

    def test_extra_endpoint_in_spec_fails(self):
        spec = copy.deepcopy(SPEC)
        spec["paths"]["/api/v1/extra"] = {"get": {"x-arc04-id": "Q9", "operationId": "q9"}}
        r = run(spec)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Q9", r.stdout)

    def test_path_or_method_mismatch_fails(self):
        spec = copy.deepcopy(SPEC)
        spec["paths"]["/api/v1/auth/signup"] = spec["paths"].pop("/api/v1/auth/register")
        r = run(spec)
        self.assertEqual(r.returncode, 1)
        self.assertIn("A2", r.stdout)

    def test_operation_without_id_fails(self):
        spec = copy.deepcopy(SPEC)
        spec["paths"]["/api/v1/auth/register"]["post"].pop("x-arc04-id")
        r = run(spec)
        self.assertNotEqual(r.returncode, 0)

    def test_duplicate_operation_id_fails(self):
        spec = copy.deepcopy(SPEC)
        spec["paths"]["/api/v1/auth/register"]["post"]["operationId"] = "a1"
        r = run(spec)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
