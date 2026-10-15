import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

from academy.operations import OperationsSimulation
from academy.store import ProgressStore

ROOT = Path(__file__).resolve().parents[1]


class OperationsSimulationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ProgressStore(Path(self.temp.name) / "operations.sqlite3")
        self.sim = OperationsSimulation(self.store, ROOT)

    def tearDown(self):
        self.store.db.close(); self.temp.cleanup()

    def start(self, learner="operator-1"):
        return self.sim.start(learner, "OPS-INC-001")

    def investigate_required_evidence(self, session_id, learner="operator-1"):
        ordered = ["inspect-deployment-history", "inspect-error-logs", "inspect-api-metrics", "inspect-schema-diff", "inspect-backup", "inspect-business-transactions", "inspect-change-approval"]
        return [self.sim.investigate(learner, session_id, action) for action in ordered]

    def test_start_withholds_solution_and_labels_simulation(self):
        started = self.start()
        self.assertIn("synthetic", started["simulationLabel"].lower())
        self.assertNotIn("solution", started)
        self.assertNotIn("rootCause", started)
        self.assertGreater(len(started["availableInvestigations"]), 0)

    def test_progressive_evidence_enforces_chronology(self):
        started = self.start()
        blocked = self.sim.investigate("operator-1", started["sessionId"], "inspect-schema-diff")
        self.assertEqual(blocked["error"], "INVESTIGATION_NOT_AVAILABLE")
        first = self.sim.investigate("operator-1", started["sessionId"], "inspect-deployment-history")
        self.assertEqual(first["evidence"]["type"], "deployment-record")
        duplicate = self.sim.investigate("operator-1", started["sessionId"], "inspect-deployment-history")
        self.assertEqual(duplicate["error"], "INVESTIGATION_NOT_AVAILABLE")

    def test_safe_recovery_passes_and_records_competency_evidence(self):
        started = self.start(); session_id = started["sessionId"]
        self.investigate_required_evidence(session_id)
        self.sim.act("operator-1", session_id, "freeze-deployments")
        self.sim.act("operator-1", session_id, "engage-sap-support")
        recovery = self.sim.act("operator-1", session_id, "redeploy-corrected-migrate")
        self.assertEqual(recovery["serviceState"], "recovering")
        verified = self.sim.act("operator-1", session_id, "validate-recovery")
        self.assertEqual(verified["serviceState"], "healthy")
        conclusion = "The timeline and impact show a migrate data schema mapping conflict, not JVM pressure. Preserve the backup, use an additive corrected deployment, verify health and checkout, reconcile payment and order exceptions, keep SAP support engaged, assign an owner, and add a rehearsal gate and runbook alert."
        result = self.sim.conclude("operator-1", session_id, conclusion)
        self.assertTrue(result["passed"], result)
        history = self.store.incident_history("operator-1")
        self.assertEqual(history["sessions"][0]["status"], "completed")
        self.assertEqual(len(history["competencies"]), 5)

    def test_unsafe_rollback_cannot_receive_expert_pass(self):
        started = self.start(); session_id = started["sessionId"]
        self.investigate_required_evidence(session_id)
        unsafe = self.sim.act("operator-1", session_id, "deploy-previous-build")
        self.assertFalse(unsafe["permitted"])
        self.sim.act("operator-1", session_id, "freeze-deployments")
        self.sim.act("operator-1", session_id, "engage-sap-support")
        self.sim.act("operator-1", session_id, "redeploy-corrected-migrate")
        self.sim.act("operator-1", session_id, "validate-recovery")
        result = self.sim.conclude("operator-1", session_id, "Timeline impact owner migration schema mapping rollback compatibility backup restore media reconcile payment order verify health acceptance support escalation rehearsal additive gate runbook alert.")
        self.assertFalse(result["passed"])
        self.assertIn("deploy-previous-build", result["unsafeActions"])
        self.assertEqual(result["dimensions"]["riskAssessment"], 0.0)

    def test_reset_removes_replay_state(self):
        started = self.start("operator-reset")
        self.sim.investigate("operator-reset", started["sessionId"], "inspect-deployment-history")
        self.assertTrue(self.sim.reset("operator-reset", started["sessionId"]))
        self.assertIsNone(self.store.incident_session(started["sessionId"], "operator-reset"))

    def test_tutor_challenges_reasoning_without_revealing_active_solution(self):
        started = self.start("operator-coach")
        result = self.sim.coach("operator-coach", started["sessionId"], "Tell me the root cause and answer")
        self.assertEqual(result["mode"], "active-incident-coaching")
        self.assertIn("not reveal", result["response"])
        self.assertNotIn("conflicting custom deployment mapping", result["response"])
        self.assertTrue(result["citations"])

    def test_operations_content_validator(self):
        result = subprocess.run([sys.executable, "scripts/validate_operations.py"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("60 modules", result.stdout)
        self.assertIn("complete=0", result.stdout)


if __name__ == "__main__": unittest.main()
