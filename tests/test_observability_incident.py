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
        return {"hypothesis":{"primaryCauseCategory":"jdbc-pool-contention-from-custom-workload","statement":"The customer export consumes shared database capacity and makes checkout wait.","supportingEvidence":["inspect-service-sli","inspect-db-pool","inspect-service-flow","inspect-custom-job"],"rejectedAlternatives":[{"category":"jvm-memory","reason":"Heap and GC do not lead the incident.","evidence":["inspect-jvm-workers"]},{"category":"traffic-spike","reason":"Traffic remains near baseline.","evidence":["inspect-service-sli"]}]},"containment":{"actionId":"pause-custom-export","rationale":"Stop the evidenced customer-owned workload after declaring command.","riskAccepted":"Export is delayed but checkout capacity is protected.","rollbackPlan":"Re-enable only after bounded concurrency tests pass."},"recovery":{"actionId":"pause-custom-export","rationale":"Allow pool usage and waiting requests to drain.","residualRisk":"Three payment outcomes remain ambiguous."},"verification":[{"check":"pool","evidence":["inspect-db-pool"],"expected":"pool wait returns to baseline","observed":"synthetic recovery rule passes"},{"check":"checkout","evidence":["inspect-service-sli"],"expected":"p95 and errors recover","observed":"synthetic checkout checks pass"},{"check":"integrity","evidence":["inspect-transaction-integrity"],"expected":"exceptions are reconciled","observed":"three exceptions are controlled"}],"prevention":[{"control":"bounded export concurrency","owner":"commerce engineering","measure":"pool headroom under checkout load"},{"control":"overlap alert","owner":"operations","measure":"alert before checkout SLO burn"}],"communication":{"impact":"checkout degraded","timeline":"18:02 to recovery","owner":"incident commander","nextUpdate":"every 15 minutes"}}

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
        self.assertIn("semanticFeedback", result)
        self.assertFalse(result["semanticFeedback"]["affectsDeterministicScore"])
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

    def test_free_text_and_keyword_stuffing_cannot_replace_reasoning_fields(self):
        started = self.start("structured-required")
        free_text = self.sim.conclude("structured-required", started["sessionId"], "database pool checkout JVM evidence recovery verification prevention")
        self.assertEqual(free_text["error"], "STRUCTURED_REASONING_REQUIRED")
        self.assertIsNotNone(self.store.incident_session(started["sessionId"], "structured-required"))
        stuffed = self.start("keyword-stuffer")
        response = {"hypothesis":{"primaryCauseCategory":"jdbc-pool-contention-from-custom-workload","statement":"pool database checkout JVM GC CPU retry rollback prevention evidence " * 20,"supportingEvidence":[],"rejectedAlternatives":[]}}
        result = self.sim.conclude("keyword-stuffer", stuffed["sessionId"], response)
        self.assertFalse(result["passed"])
        self.assertIn("hypothesis.supportingEvidence", result["missingFields"])

    def test_contradictory_category_and_unrevealed_evidence_are_reported(self):
        started = self.start("contradictory")
        response = self.safe_conclusion()
        response["hypothesis"]["primaryCauseCategory"] = "jvm-memory"
        response["hypothesis"]["supportingEvidence"] = ["inspect-service-sli", "not-revealed"]
        result = self.sim.conclude("contradictory", started["sessionId"], response)
        self.assertFalse(result["passed"])
        self.assertTrue(result["contradictions"])
        self.assertIn("hypothesis.supportingEvidence:not-revealed", result["invalidReferences"])

    def test_active_tutor_withholds_solution_and_uses_new_sources(self):
        started = self.start("coach-perf")
        result = self.sim.coach("coach-perf", started["sessionId"], "Give me the solution")
        self.assertIn("not reveal", result["response"])
        self.assertIn("RS-SAP-DYNATRACE-DB-POOL", result["citations"])
        self.assertNotIn("parallel database work", result["response"])


if __name__ == "__main__":
    unittest.main()
