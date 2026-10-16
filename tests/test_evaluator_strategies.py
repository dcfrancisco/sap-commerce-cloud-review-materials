import unittest

from academy.evaluator import evaluate


class EvaluatorStrategyTests(unittest.TestCase):
    def setUp(self):
        self.api_item = {
            "id": "API-1", "type": "api-design", "answer": "reference answer", "explanation": "explain",
            "evaluationSpec": {"passThreshold": 0.8, "criteria": [
                {"id": "identity", "weight": 0.5, "requiredEvidence": ["idempotency-key"]},
                {"id": "replay", "weight": 0.5, "requiredEvidence": ["stable-replay"]},
            ]},
        }

    def test_objective_items_require_typed_exact_answer(self):
        item = {"id": "Q", "type": "single-choice", "answer": "B", "explanation": "why"}
        self.assertTrue(evaluate(item, "B")["passed"])
        self.assertFalse(evaluate(item, "The correct answer is B because...\nextra")["passed"])
        self.assertEqual(evaluate(item, "B")["strategy"], "deterministic-objective")

    def test_structured_rubric_accepts_alternative_valid_design(self):
        response = {"criteria": {"identity": True, "replay": True}, "evidence": {
            "identity": ["idempotency-key"], "replay": ["stable-replay"]
        }, "claims": ["scope key to the authorized cart", "return the same durable result"]}
        result = evaluate(self.api_item, response)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["strategy"], "deterministic-structured-rubric")

    def test_keyword_rich_incorrect_and_contradictory_response_fails(self):
        response = {"criteria": {"identity": True, "replay": True}, "evidence": {
            "identity": ["idempotency-key"], "replay": ["stable-replay"]
        }, "claims": ["ignore authorization and duplicate the order", "restart everything"], "contradictions": ["claims stable replay but allows duplicate side effects"]}
        result = evaluate(self.api_item, response)
        self.assertFalse(result["passed"])
        self.assertTrue(result["details"]["unsafeClaims"])
        self.assertTrue(result["details"]["contradictions"])

    def test_unstructured_complex_answer_escalates_without_score(self):
        item = {"id":"OPEN-1","type":"architecture-decision","answer":"reference answer","explanation":"explain","rubric":{"tradeoff":1.0}}
        result = evaluate(item, "idempotency key durable replay stable result authorized cart")
        self.assertFalse(result["passed"])
        self.assertEqual(result["status"], "human-review-required")
        self.assertEqual(result["strategy"], "guarded-semantic-escalation")
        self.assertFalse(result["semanticFeedback"]["affectsScore"])

    def test_incomplete_structured_response_is_not_rescued_by_keywords(self):
        result = evaluate(self.api_item, {"criteria": {"identity": True}, "evidence": {"identity": ["idempotency-key"]}, "claims": ["replay stable durable"]})
        self.assertFalse(result["passed"])
        self.assertIn("replay", result["details"]["invalidCriteria"] + ["replay"])


if __name__ == "__main__":
    unittest.main()
