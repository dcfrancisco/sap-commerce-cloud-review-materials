import json
import unittest
from pathlib import Path

from academy.incidents import IncidentTutor
from academy.tutor import GroundedTutor

ROOT = Path(__file__).resolve().parents[1]

class EcosystemSliceTests(unittest.TestCase):
    def test_all_three_slices_have_content_assessments_and_labs(self):
        labs = json.loads((ROOT / "content/labs/ecosystem-vertical-slices.json").read_text())["labs"]
        self.assertEqual({x["moduleId"] for x in labs}, {"M25", "M26", "M27"})
        for number in (25, 26, 27):
            self.assertTrue(list((ROOT / "content/modules").glob(f"{number}-*.md")))
            items = json.loads((ROOT / f"content/assessments/module-{number}.json").read_text())["items"]
            self.assertGreaterEqual(len(items), 4)

    def test_incident_tutor_stages_evidence_and_penalizes_unsafe_action(self):
        tutor = IncidentTutor(ROOT)
        started = tutor.start("LAB-M27-FAILED-DEPLOYMENT")
        self.assertEqual(started["availableEvidence"]["stage"], 1)
        safe = tutor.grade("LAB-M27-FAILED-DEPLOYMENT", "Build a deployment timeline, inspect schema migration compatibility, evaluate backup restore or corrected redeploy, then verify and reconcile acceptance results.")
        self.assertTrue(safe["passed"])
        unsafe = tutor.grade("LAB-M27-FAILED-DEPLOYMENT", "initialize production and delete database")
        self.assertFalse(unsafe["passed"])
        self.assertTrue(unsafe["unsafeActions"])

    def test_grounded_tutor_covers_each_new_slice(self):
        tutor = GroundedTutor(ROOT)
        for module, question in [("M25","storefront Angular Node compatibility"),("M26","Backoffice synchronization search indexing"),("M27","deployment rollback schema recovery")]:
            result = tutor.answer(question, module)
            self.assertEqual(result["confidence"], "grounded-excerpt")
            self.assertTrue(result["citations"])

if __name__ == "__main__": unittest.main()
