import tempfile
import unittest
from pathlib import Path

from academy.practice import PracticeEngine
from academy.store import ProgressStore

ROOT = Path(__file__).resolve().parents[1]


class PracticeEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.store = ProgressStore(Path(self.temp.name) / "practice.sqlite3"); self.engine = PracticeEngine(self.store, ROOT)

    def tearDown(self):
        self.store.db.close(); self.temp.cleanup()

    def test_catalog_has_distinct_deep_exercise_types(self):
        catalog = self.engine.catalog()
        self.assertEqual(len(catalog), 31)
        self.assertGreaterEqual(len({item["type"] for item in catalog}), 24)
        self.assertNotIn("published", {item["reviewStatus"] for item in catalog})

    def test_seed_is_reproducible_and_private_fields_are_withheld(self):
        first = self.engine.start("learner", "OPS-EX-D03-002", "same-seed")
        second = self.engine.start("learner", "OPS-EX-D03-002", "same-seed")
        other = self.engine.start("learner", "OPS-EX-D03-002", "different-seed")
        self.assertEqual(first["variant"], second["variant"])
        self.assertNotEqual(first["variant"]["signature"], other["variant"]["signature"])
        self.assertNotIn("referenceSolution", first["exercise"])
        self.assertNotIn("evaluation", first["exercise"])
        self.assertNotIn("hints", first["exercise"])
        self.assertIn("never count", first["variantCountingPolicy"])

    def test_progressive_hint_marks_evidence_assisted(self):
        started = self.engine.start("hinted", "OPS-EX-D03-002", "hint-seed")
        hint = self.engine.hint("hinted", started["sessionId"])
        self.assertEqual(hint["level"], 1)
        self.assertFalse(hint["independentEvidenceEligible"])
        response = self.good_recovery_response(started["variant"])
        result = self.engine.submit("hinted", started["sessionId"], response)
        self.assertTrue(result["passed"], result)
        self.assertTrue(result["assisted"])
        self.assertFalse(result["independentEvidenceEligible"])
        history = self.store.practice_history("hinted")
        self.assertEqual(history["competencies"][0]["independentEvidence"], 0)

    def test_independent_submission_persists_mastery_evidence(self):
        started = self.engine.start("independent", "OPS-EX-D03-002", "independent-seed")
        result = self.engine.submit("independent", started["sessionId"], self.good_recovery_response(started["variant"]))
        self.assertTrue(result["passed"], result)
        self.assertTrue(result["independentEvidenceEligible"])
        self.assertIn("referenceSolution", result)
        history = self.store.practice_history("independent")
        self.assertEqual(len(history["sessions"]), 1)
        self.assertEqual(len(history["competencies"]), 2)
        self.assertEqual(history["competencies"][0]["independentEvidence"], 1)

    def test_unsafe_phrase_hard_fails_even_with_full_coverage(self):
        started = self.engine.start("unsafe", "OPS-EX-D03-002", "unsafe-seed")
        response = self.good_recovery_response(started["variant"]) + " We will initialize production."
        result = self.engine.submit("unsafe", started["sessionId"], response)
        self.assertFalse(result["passed"])
        self.assertEqual(result["dimensions"]["safety"], 0.0)
        self.assertIn("initialize production", result["unsafeFindings"])

    @staticmethod
    def good_recovery_response(variant):
        return f"Use schema compatibility and migration evidence to compare rollback and corrected roll-forward. The backup is {variant['backup']['ageMinutes']} minutes old during {variant['traffic']['businessWindow']}, so quantify RPO and RTO. Verify database, media, search index, health and acceptance tests. Reconcile payment, ERP and order effects. Engage managed SAP support and escalate with logs, timeline, correlation records and validation evidence."


if __name__ == "__main__": unittest.main()
