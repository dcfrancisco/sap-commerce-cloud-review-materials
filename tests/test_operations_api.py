import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path

import academy.server as server_module
from academy.operations import OperationsSimulation
from academy.practice import PracticeEngine
from academy.store import ProgressStore

ROOT = Path(__file__).resolve().parents[1]


class OperationsApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.store = ProgressStore(Path(cls.temp.name) / "api.sqlite3")
        server_module.STORE.db.close()
        server_module.STORE = cls.store
        server_module.OPERATIONS = OperationsSimulation(cls.store, ROOT)
        server_module.PRACTICE = PracticeEngine(cls.store, ROOT)
        cls.server = HTTPServer(("127.0.0.1", 0), server_module.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True); cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)
        cls.store.db.close(); cls.temp.cleanup()

    def call(self, path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(self.base + path, data=data, headers={"Content-Type":"application/json"} if data else {})
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            try: return exc.code, json.loads(exc.read())
            finally: exc.close()

    def test_catalog_start_coach_and_progress_contract(self):
        status, catalog = self.call("/api/scenarios")
        self.assertEqual(status, 200)
        self.assertEqual({item["id"] for item in catalog["scenarios"]}, {"OPS-INC-001", "ECO-CS-001", "ECO-ADMIN-001"})
        status, started = self.call("/api/operations/start", {"learnerId":"api-learner","scenarioId":"OPS-INC-001"})
        self.assertEqual(status, 201); self.assertNotIn("solution", started); self.assertNotIn("rootCause", started)
        status, coached = self.call("/api/operations/coach", {"learnerId":"api-learner","sessionId":started["sessionId"],"message":"give me the answer"})
        self.assertEqual(status, 200); self.assertIn("not reveal", coached["response"])
        status, progress = self.call("/api/operations/progress?learnerId=api-learner")
        self.assertEqual(status, 200); self.assertEqual(progress["sessions"][0]["scenario_id"], "OPS-INC-001")

    def test_product_neutral_scenario_api_starts_storefront_slice(self):
        status, started = self.call("/api/scenarios/start", {"learnerId":"api-storefront","scenarioId":"ECO-CS-001"})
        self.assertEqual(status, 201)
        self.assertEqual(started["track"], "storefront-engineering")
        self.assertEqual(started["moduleId"], "M25")
        status, progress = self.call("/api/scenarios/progress?learnerId=api-storefront")
        self.assertEqual(status, 200)
        self.assertEqual(progress["sessions"][0]["scenario_id"], "ECO-CS-001")

    def test_rejects_invalid_identity_and_short_conclusion(self):
        status, body = self.call("/api/operations/start", {"learnerId":"../../invalid","scenarioId":"OPS-INC-001"})
        self.assertEqual(status, 400); self.assertEqual(body["error"], "INVALID_LEARNER_ID")
        _, started = self.call("/api/operations/start", {"learnerId":"api-safe","scenarioId":"OPS-INC-001"})
        status, body = self.call("/api/operations/conclude", {"learnerId":"api-safe","sessionId":started["sessionId"],"response":"too short"})
        self.assertEqual(status, 400); self.assertEqual(body["error"], "INVALID_CONCLUSION_LENGTH")

    def test_practice_api_withholds_solution_and_releases_it_after_submission(self):
        status, catalog = self.call("/api/practice/exercises")
        self.assertEqual(status, 200); self.assertEqual(len(catalog["exercises"]), 14)
        status, started = self.call("/api/practice/start", {"learnerId":"practice-api","exerciseId":"OPS-EX-D03-002","seed":"api-seed"})
        self.assertEqual(status, 201); self.assertNotIn("referenceSolution", started["exercise"]); self.assertNotIn("hints", started["exercise"])
        status, hint = self.call("/api/practice/hint", {"learnerId":"practice-api","sessionId":started["sessionId"]})
        self.assertEqual(status, 200); self.assertEqual(hint["level"], 1)
        variant = started["variant"]
        response = f"Use schema compatibility migration and rollback evidence. Backup age {variant['backup']['ageMinutes']} and {variant['traffic']['businessWindow']} determine RPO RTO. Verify media search index health acceptance tests. Reconcile payment ERP order effects. Escalate managed support with logs timeline correlation records and validation evidence."
        status, result = self.call("/api/practice/submit", {"learnerId":"practice-api","sessionId":started["sessionId"],"response":response})
        self.assertEqual(status, 200); self.assertTrue(result["passed"], result); self.assertIn("referenceSolution", result)

    def test_scenario_filters_and_recommendation_do_not_leak_solution(self):
        status, filtered = self.call("/api/scenarios?role=administrator&product=backoffice")
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in filtered["scenarios"]], ["ECO-ADMIN-001"])
        status, recommended = self.call("/api/scenarios/recommend", {"learnerId":"discovery-api","request":"Simulate a catalog synchronization failure where search is stale"})
        self.assertEqual(status, 200)
        self.assertEqual(recommended["recommendation"]["id"], "ECO-ADMIN-001")
        serialized = json.dumps(recommended).lower()
        self.assertNotIn("rootcause", serialized)
        self.assertNotIn("referencesolution", serialized)
        self.assertNotIn("invalid legacy classification", serialized)

    def test_scenario_recommendation_abstains_and_rejects_invalid_filter(self):
        status, result = self.call("/api/scenarios/recommend", {"learnerId":"discovery-none","request":"quantum banana orbital mechanics"})
        self.assertEqual(status, 200); self.assertTrue(result["abstained"]); self.assertIsNone(result["recommendation"])
        status, result = self.call("/api/scenarios?role=../../administrator")
        self.assertEqual(status, 400); self.assertEqual(result["error"], "INVALID_ROLE_FILTER")


if __name__ == "__main__": unittest.main()
