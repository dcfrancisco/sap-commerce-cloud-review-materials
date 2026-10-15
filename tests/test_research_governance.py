import subprocess
import sys
import unittest
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ResearchGovernanceTests(unittest.TestCase):
    def test_research_registry_and_coverage(self):
        result = subprocess.run([sys.executable, "scripts/validate_research.py"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        course = json.loads((ROOT / "content/course.json").read_text())
        count = len(course["modules"])
        self.assertIn(f"module coverage: {count}/{count}", result.stdout)

if __name__ == "__main__": unittest.main()
