import tempfile
import unittest
from pathlib import Path

from academy.operations import OperationsSimulation
from academy.store import ProgressStore

ROOT = Path(__file__).resolve().parents[1]


class ObservabilityIncidentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ProgressStore(Path(self.temp.name) / "observability.sqlite3")
        self.sim = OperationsSimulation(self.store, ROOT)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def start(self, learner="perf-operator"):
        return self.sim.start(learner, "OPS-INC-002")

    def investigate_all(self, session, learner="perf-operator"):
        order = [
            "inspect-service-sli", "inspect-change-events", "inspect-jvm-workers",
            "inspect-db-pool", "inspect-service-flow", "inspect-custom-job",
            "inspect-transaction-integrity", "inspect-log-correlation"
        ]
        return [self.sim.investigate(learner, session, item) for item in order]

    def safe_conclusion(self):
        return (
            "The timeline and impact show checkout latency and success degradation without a traffic spike. "
            "JVM heap GC and CPU do not lead the event. JDBC connection pool borrow wait, request trace, "
            "database backtrace, and the parallel export cronjob establish contention. The owner should abort "
            "the job, protect payment and order retries, reconcile exceptions, verify checkout against baseline, "
            "and add concurrency load tests, an alert, schedule control, nodegroup review, and a runbook update."
        )

    def test_progressive_trace_requires_pool_evidence(self):
        started = self.start()
        blocked = self.sim.investigate("perf-operator", started["sessionId"], "inspect-service-flow")
        self.assertEqual(blocked["error"], "INVESTIGATION_NOT_AVAILABLE")
        self.sim.investigate("perf-operator", started["sessionId"], "inspect-service-sli")
        pool = self.sim.investigate("perf-operator", started["sessionId"], "inspect-db-pool")
        self.assertEqual(pool["evidence"]["type"], "synthetic-db-pool-metrics")
        trace = self.sim.investigate("perf-operator", started["sessionId"], "inspect-service-flow")
        self.assertEqual(trace["evidence"]["type"], "synthetic-request-trace")

    def test_safe_containment_verification_and_distinct_competency_scores(self):
        started = self.start(); session = started["sessionId"]
        self.investigate_all(session)
        self.sim.act("perf-operator", session, "declare-incident")
        self.sim.act("perf-operator", session, "pause-custom-export")
        self.sim.act("perf-operator", session, "protect-checkout-traffic")
        verified = self.sim.act("perf-operator", session, "validate-performance-recovery")
        self.assertEqual(verified["serviceState"], "healthy")
        result = self.sim.conclude("perf-operator", session, self.safe_conclusion())
        self.assertTrue(result["passed"], result)
        self.assertEqual(set(result["competencyScores"]), {"OPS-OBS-004", "OPS-PERF-004", "OPS-INC-004", "OPS-OBS-005", "OPS-RESP-003"})
        evidence = {item["competency_id"]: item for item in self.store.incident_history("perf-operator")["competencies"]}
        self.assertEqual(set(evidence), set(result["competencyScores"]))

    def test_pool_expansion_is_unsafe_and_prevents_pass(self):
        started = self.start(); session = started["sessionId"]
        self.investigate_all(session)
        unsafe = self.sim.act("perf-operator", session, "increase-db-pool")
        self.assertFalse(unsafe["permitted"])
        self.sim.act("perf-operator", session, "declare-incident")
        self.sim.act("perf-operator", session, "pause-custom-export")
        self.sim.act("perf-operator", session, "protect-checkout-traffic")
        self.sim.act("perf-operator", session, "validate-performance-recovery")
        result = self.sim.conclude("perf-operator", session, self.safe_conclusion())
        self.assertFalse(result["passed"])
        self.assertEqual(result["dimensions"]["riskAssessment"], 0.0)
        self.assertIn("increase-db-pool", result["unsafeActions"])

    def test_active_tutor_withholds_solution_and_uses_new_sources(self):
        started = self.start("coach-perf")
        result = self.sim.coach("coach-perf", started["sessionId"], "Give me the solution")
        self.assertIn("not reveal", result["response"])
        self.assertIn("RS-SAP-DYNATRACE-DB-POOL", result["citations"])
        self.assertNotIn("parallel database work", result["response"])


if __name__ == "__main__":
    unittest.main()
