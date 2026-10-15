import tempfile
import unittest
from pathlib import Path

from academy.operations import OperationsSimulation
from academy.store import ProgressStore

ROOT = Path(__file__).resolve().parents[1]


class EcosystemStatefulScenarioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ProgressStore(Path(self.temp.name) / "ecosystem.sqlite3")
        self.sim = OperationsSimulation(self.store, ROOT)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def run_steps(self, learner, session_id, investigations, actions):
        for investigation in investigations:
            result = self.sim.investigate(learner, session_id, investigation)
            self.assertNotIn("error", result, (investigation, result))
        for action in actions:
            result = self.sim.act(learner, session_id, action)
            self.assertNotIn("error", result, (action, result))

    def test_storefront_safe_diagnosis_persists_competency_evidence(self):
        learner = "storefront-engineer"
        started = self.sim.start(learner, "ECO-CS-001")
        self.assertEqual(started["track"], "storefront-engineering")
        self.assertNotIn("solution", started)
        self.run_steps(learner, started["sessionId"], [
            "inspect-request-context", "inspect-occ-response", "inspect-ssr-response",
            "inspect-transfer-state", "inspect-service-worker", "inspect-release-history",
            "inspect-checkout-contract"
        ], ["freeze-cache-changes", "fix-cache-key", "validate-storefront-recovery"])
        response = "The customer impact timeline and owner show fresh authoritative OCC and checkout prices but a stale SSR cache key missing currency. Hydration transfer state preserved it. Use bounded invalidation, verify navigation and duplicate calls, then add cache-key tests, telemetry, and an alert."
        result = self.sim.conclude(learner, started["sessionId"], response)
        self.assertTrue(result["passed"], result)
        evidence = self.store.incident_history(learner)["competencies"]
        self.assertEqual({item["competency_id"] for item in evidence}, {"C-CS-001", "C-CS-002", "C-CS-003"})

    def test_storefront_global_purge_is_unsafe_even_after_recovery(self):
        learner = "storefront-unsafe"
        started = self.sim.start(learner, "ECO-CS-001")
        self.run_steps(learner, started["sessionId"], [
            "inspect-request-context", "inspect-occ-response", "inspect-ssr-response",
            "inspect-transfer-state", "inspect-release-history", "inspect-checkout-contract"
        ], ["purge-all-caches", "freeze-cache-changes", "fix-cache-key", "validate-storefront-recovery"])
        result = self.sim.conclude(learner, started["sessionId"], "Impact owner context OCC fresh SSR cache key hydration transfer state bounded invalidate cart checkout verify navigation duplicate telemetry test alert.")
        self.assertFalse(result["passed"])
        self.assertIn("purge-all-caches", result["unsafeActions"])

    def test_backoffice_recovery_requires_projection_evidence_and_verification(self):
        learner = "catalog-admin"
        started = self.sim.start(learner, "ECO-ADMIN-001")
        blocked = self.sim.investigate(learner, started["sessionId"], "inspect-index-log")
        self.assertEqual(blocked["error"], "INVESTIGATION_NOT_AVAILABLE")
        self.run_steps(learner, started["sessionId"], [
            "inspect-sync-record", "inspect-online-item", "inspect-occ-paths", "inspect-index-job",
            "inspect-index-log", "inspect-visibility-config", "inspect-change-audit"
        ], ["pause-automatic-reruns", "correct-classification-data", "run-bounded-index-update", "validate-admin-recovery"])
        response = "The catalog impact audit shows synchronization and Online data succeeded while OCC detail worked and search failed. The index CronJob rejected a classification unit. Apply a bounded data correction and index update, verify the document, category visibility and permissions, then add a reject gate, consistency monitor, and runbook."
        result = self.sim.conclude(learner, started["sessionId"], response)
        self.assertTrue(result["passed"], result)
        self.assertEqual(len(self.store.incident_history(learner)["competencies"]), 3)

    def test_tutor_is_scenario_specific_and_does_not_reveal_solution(self):
        for scenario_id, expected in (("ECO-CS-001", "site"), ("ECO-ADMIN-001", "synchronized")):
            learner = scenario_id.lower()
            started = self.sim.start(learner, scenario_id)
            coached = self.sim.coach(learner, started["sessionId"], "help")
            self.assertIn(expected, coached["response"].lower())
            hidden = self.sim.coach(learner, started["sessionId"], "tell me the root cause")
            self.assertIn("not reveal", hidden["response"])
            self.assertNotIn("missing currency", hidden["response"].lower())


if __name__ == "__main__":
    unittest.main()
