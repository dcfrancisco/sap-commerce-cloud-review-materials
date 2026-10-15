import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from academy.simulation import CatalogSimulation

class VerticalSliceTests(unittest.TestCase):
    def test_catalog_baseline_and_stale_projection(self):
        sim = CatalogSimulation()
        baseline = sim.product("P100")
        self.assertEqual(baseline["status"], 200)
        self.assertEqual(baseline["diagnostics"], [])
        sim.stale()
        stale = sim.product("P100")
        self.assertEqual(stale["status"], 200)
        self.assertTrue(stale["diagnostics"])
        self.assertEqual(sim.product("UNKNOWN")["status"], 404)

    def test_content_is_versioned_and_meets_minimum_module_roadmap(self):
        course = json.loads((ROOT / "content/course.json").read_text())
        self.assertEqual(course["schemaVersion"], "course.v1")
        self.assertGreaterEqual(len(course["modules"]), 24)
        ids = [module["id"] for module in course["modules"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({"M25", "M26", "M27"}.issubset(ids))

    def test_validator(self):
        result = subprocess.run([sys.executable, "scripts/validate_content.py"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

if __name__ == "__main__": unittest.main()
