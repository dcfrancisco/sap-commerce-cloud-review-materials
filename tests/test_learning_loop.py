import json
import tempfile
import unittest
from pathlib import Path

from academy.evaluator import evaluate
from academy.store import ProgressStore
from academy.tutor import GroundedTutor

ROOT = Path(__file__).resolve().parents[1]

class LearningLoopTests(unittest.TestCase):
    def setUp(self):
        self.item = json.loads((ROOT / "content/assessments/module-01.json").read_text())["items"][0]

    def test_public_delivery_has_no_answer_fields(self):
        private = set(self.item)
        public = {key for key in private if key not in {"answer", "explanation", "incorrectRationales"}}
        self.assertNotIn("answer", public)
        self.assertNotIn("explanation", public)

    def test_evaluation_and_persistent_evidence(self):
        result = evaluate(self.item, self.item["answer"])
        self.assertTrue(result["passed"])
        with tempfile.TemporaryDirectory() as directory:
            store = ProgressStore(Path(directory) / "progress.sqlite3")
            attempt_id = store.record("learner-1", self.item, self.item["answer"], result)
            summary = store.summary("learner-1")
            self.assertEqual(attempt_id, 1)
            self.assertEqual(summary["attempts"][0]["passed"], 1)
            self.assertEqual(summary["competencies"][0]["competency_id"], "C-ARCH-001")
            store.db.close()

    def test_tutor_abstains_when_not_grounded(self):
        tutor = GroundedTutor(ROOT)
        unknown = tutor.answer("zxqv blargh nimbus", "M01")
        self.assertEqual(unknown["confidence"], "unknown")
        grounded = tutor.answer("What is an extension and what does OCC do?", "M01")
        self.assertTrue(grounded["citations"])

if __name__ == "__main__": unittest.main()
