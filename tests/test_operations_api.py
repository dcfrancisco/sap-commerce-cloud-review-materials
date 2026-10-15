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
from academy.store import ProgressStore

ROOT = Path(__file__).resolve().parents[1]


class OperationsApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.store = ProgressStore(Path(cls.temp.name) / "api.sqlite3")
        server_module.STORE = cls.store
        server_module.OPERATIONS = OperationsSimulation(cls.store, ROOT)
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
        status, catalog = self.call("/api/operations/scenarios")
        self.assertEqual(status, 200); self.assertEqual(catalog["scenarios"][0]["id"], "OPS-INC-001")
        status, started = self.call("/api/operations/start", {"learnerId":"api-learner","scenarioId":"OPS-INC-001"})
        self.assertEqual(status, 201); self.assertNotIn("solution", started); self.assertNotIn("rootCause", started)
        status, coached = self.call("/api/operations/coach", {"learnerId":"api-learner","sessionId":started["sessionId"],"message":"give me the answer"})
        self.assertEqual(status, 200); self.assertIn("not reveal", coached["response"])
        status, progress = self.call("/api/operations/progress?learnerId=api-learner")
        self.assertEqual(status, 200); self.assertEqual(progress["sessions"][0]["scenario_id"], "OPS-INC-001")

    def test_rejects_invalid_identity_and_short_conclusion(self):
        status, body = self.call("/api/operations/start", {"learnerId":"../../invalid","scenarioId":"OPS-INC-001"})
        self.assertEqual(status, 400); self.assertEqual(body["error"], "INVALID_LEARNER_ID")
        _, started = self.call("/api/operations/start", {"learnerId":"api-safe","scenarioId":"OPS-INC-001"})
        status, body = self.call("/api/operations/conclude", {"learnerId":"api-safe","sessionId":started["sessionId"],"response":"too short"})
        self.assertEqual(status, 400); self.assertEqual(body["error"], "INVALID_CONCLUSION_LENGTH")


if __name__ == "__main__": unittest.main()
