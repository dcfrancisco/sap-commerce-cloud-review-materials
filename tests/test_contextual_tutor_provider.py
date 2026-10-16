import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from academy.contextual_tutor import ContextualTutor


class ProviderHandler(BaseHTTPRequestHandler):
    received = None

    def do_POST(self):
        ProviderHandler.received = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        payload = {"response":"Use the disclosed pool evidence and test the competing hypothesis.","citations":["RS-SAP-DYNATRACE-DB-POOL"],"confidence":"advisory"}
        body = json.dumps(payload).encode(); self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)

    def log_message(self, *_):
        return


class ContextualTutorProviderTests(unittest.TestCase):
    def test_configured_provider_receives_context_without_solution(self):
        server = HTTPServer(("127.0.0.1", 0), ProviderHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            context = {"scenario":{"id":"OPS-INC-002","title":"Pool incident","topics":["JDBC"],"sourceIds":["RS-SAP-DYNATRACE-DB-POOL"],"reasoningModel":{"preferredPrimary":"secret"},"referenceRootCause":"secret"},"state":{"status":"active","actions":["declare-incident"]},"message":"What next?","mode":"tutoring","revealedEvidence":[{"id":"inspect-db-pool","evidence":{"finding":"wait"}}],"availableInvestigations":[],"availableActions":[],"priorAttempts":[]}
            result = ContextualTutor(provider=f"http://127.0.0.1:{server.server_port}").answer(context)
            self.assertEqual(result["provider"], "configured-http")
            self.assertNotIn("secret", json.dumps(ProviderHandler.received))
            self.assertEqual(result["citations"], ["RS-SAP-DYNATRACE-DB-POOL"])
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)

    def test_provider_failure_falls_back_to_local_contextual_coaching(self):
        context = {"scenario":{"id":"OPS-INC-002","title":"Pool incident","topics":["JDBC"],"sourceIds":[]},"state":{"status":"active","actions":[]},"message":"What should I investigate next?","mode":"examination","revealedEvidence":[],"availableInvestigations":[{"id":"inspect-db-pool","label":"Inspect pool"}],"availableActions":[],"priorAttempts":[]}
        result = ContextualTutor(provider="http://127.0.0.1:1/unavailable").answer(context)
        self.assertEqual(result["provider"], "local-fallback")
        self.assertTrue(result["fallback"])
        self.assertEqual(result["mode"], "examination-coaching")
