import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from academy.practice import PracticeEngine
from academy.store import ProgressStore

ROOT = Path(__file__).resolve().parents[1]


class DeveloperTestingCompetencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ProgressStore(Path(self.temp.name) / "developer-testing.sqlite3")
        self.engine = PracticeEngine(self.store, ROOT)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def test_each_core_developer_module_has_an_executable_testing_exercise(self):
        catalog = self.engine.catalog()
        developer = [item for item in catalog if item["id"].startswith("DEV-EX-")]
        self.assertEqual(len(developer), 4)
        self.assertEqual({item["moduleId"] for item in developer}, {"M02", "M03", "M04", "M05"})

    def test_correct_implementation_without_tests_is_capped_and_recorded_separately(self):
        started = self.engine.start("implementation-only", "DEV-EX-M02-001", "cap-policy")
        response = "Repair extensioninfo requires academycore dependency. The minimal Spring bean context repair preserves facade service delegation."
        result = self.engine.submit("implementation-only", started["sessionId"], response)
        self.assertTrue(result["implementation"]["passed"], result)
        self.assertFalse(result["testing"]["passed"], result)
        self.assertTrue(result["masteryCapApplied"])
        self.assertLess(result["score"], 0.8)
        self.assertFalse(result["passed"])
        evidence = {item["competency_id"]:item for item in self.store.practice_history("implementation-only")["competencies"]}
        self.assertEqual(evidence["C-EXT-002"]["passed"], 1)
        self.assertEqual(evidence["C-TEST-EXT-001"]["passed"], 0)

    def test_implementation_and_testing_evidence_can_pass_independently(self):
        started = self.engine.start("tested-developer", "DEV-EX-M02-001", "red-green")
        response = "Repair extensioninfo requires academycore dependency and Spring bean context with minimal facade service delegation. Use JUnit unit Mockito and an integration platform context test in testsrc with tenant runtime. Assert verify negative behavior and a red green regression. Capture the missing dependency failure red plus context bean evidence, then command target report and result pass green. State the platform test was not run here."
        result = self.engine.submit("tested-developer", started["sessionId"], response)
        self.assertTrue(result["implementation"]["passed"], result)
        self.assertTrue(result["testing"]["passed"], result)
        self.assertFalse(result["masteryCapApplied"])
        self.assertTrue(result["passed"], result)
        self.assertIn("C-TEST-EXT-001", result["competencyScores"])

    def test_false_live_execution_claim_is_a_hard_fail(self):
        started = self.engine.start("false-claim", "DEV-EX-M05-001", "security")
        response = "Ownership authorization server controller facade policy error status contract support role permission. Unit controller mock contract schema compatibility platform web integration unauthenticated unauthorized forbidden malformed missing negative leak enumeration sensitive report version command result red green pass. Tested on live SAP Commerce."
        result = self.engine.submit("false-claim", started["sessionId"], response)
        self.assertFalse(result["passed"])
        self.assertIn("tested on live sap commerce", result["unsafeFindings"])

    def test_developer_testing_validator(self):
        result = subprocess.run([sys.executable, "scripts/validate_developer_testing.py"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("4 across 4 modules", result.stdout)


if __name__ == "__main__":
    unittest.main()
