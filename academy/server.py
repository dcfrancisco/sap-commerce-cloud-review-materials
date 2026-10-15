import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .evaluator import evaluate
from .incidents import IncidentTutor
from .operations import OperationsSimulation
from .store import ProgressStore
from .tutor import GroundedTutor

ROOT = Path(__file__).resolve().parents[1]
STORE = ProgressStore()
TUTOR = GroundedTutor(ROOT)
INCIDENTS = IncidentTutor(ROOT)
OPERATIONS = OperationsSimulation(STORE, ROOT)
SIMULATION = None


def load_json(relative): return json.loads((ROOT / relative).read_text())


def assessment_items(module_id):
    path = ROOT / "content" / "assessments" / f"module-{module_id[1:].zfill(2)}.json"
    if not path.exists(): return []
    return load_json(path.relative_to(ROOT))["items"]


def module_document(module_id):
    prefix = module_id.lower().replace("m", "", 1).zfill(2)
    path = next(ROOT.glob(f"content/modules/{prefix}-*.md"), None)
    return path


def public_item(item):
    return {key: item[key] for key in item if key not in {"answer", "explanation", "incorrectRationales"}}


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload, status=200, content_type="application/json"):
        body = payload.encode() if isinstance(payload, str) else json.dumps(payload, indent=2).encode()
        self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 65536: raise ValueError("REQUEST_TOO_LARGE")
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        global SIMULATION
        if SIMULATION is None:
            from .simulation import CatalogSimulation
            SIMULATION = CatalogSimulation()
        parsed = urlparse(self.path); path = parsed.path; query = parse_qs(parsed.query)
        if path == "/": return self._send((ROOT / "academy" / "index.html").read_text(), content_type="text/html; charset=utf-8")
        if path == "/api/course": return self._send(load_json("content/course.json"))
        if path == "/api/incidents": return self._send({"labs": INCIDENTS.catalog()})
        if path == "/api/operations/scenarios": return self._send({"scenarios": OPERATIONS.catalog()})
        if path == "/api/operations/progress": return self._send(OPERATIONS.store.incident_history(query.get("learnerId", ["local"])[0]))
        if path.startswith("/api/module/"):
            module_id = path.rsplit("/", 1)[-1].upper(); document = module_document(module_id)
            if not document: return self._send({"error":"MODULE_NOT_FOUND"}, 404)
            return self._send({"id":module_id, "markdown":document.read_text(), "competencies":load_json("content/competencies.json")})
        if path.startswith("/api/assessment/items/"):
            module_id = path.rsplit("/", 1)[-1].upper(); return self._send({"moduleId":module_id, "items":[public_item(i) for i in assessment_items(module_id)]})
        if path == "/api/progress": return self._send(STORE.summary(query.get("learnerId", ["local"])[0]))
        if path.startswith("/api/simulation/products/"): return self._send(SIMULATION.product(path.rsplit("/", 1)[-1]))
        return self._send({"error":"NOT_FOUND"}, 404)

    def do_POST(self):
        global SIMULATION
        if SIMULATION is None:
            from .simulation import CatalogSimulation
            SIMULATION = CatalogSimulation()
        path = urlparse(self.path).path
        try: body = self._body()
        except (ValueError, json.JSONDecodeError) as exc: return self._send({"error":"INVALID_REQUEST","detail":str(exc)}, 400)
        learner_id = str(body.get("learnerId", "local"))
        if len(learner_id) > 80 or not all(character.isalnum() or character in "-_.@" for character in learner_id): return self._send({"error":"INVALID_LEARNER_ID"}, 400)
        if path == "/api/assessment/submit":
            item_id = body.get("itemId"); item = next((x for x in assessment_items(body.get("moduleId", "M01")) if x["id"] == item_id), None)
            if not item: return self._send({"error":"ITEM_NOT_FOUND"}, 404)
            result = evaluate(item, body.get("response")); attempt_id = STORE.record(body.get("learnerId", "local"), item, body.get("response"), result)
            return self._send({"attemptId":attempt_id, "itemId":item_id, "competencyIds":item["competencyIds"], **result})
        if path == "/api/tutor/ask": return self._send(TUTOR.answer(body.get("question", ""), body.get("moduleId", "M01")))
        if path == "/api/incidents/start":
            result = INCIDENTS.start(body.get("labId")); return self._send(result or {"error":"LAB_NOT_FOUND"}, 200 if result else 404)
        if path == "/api/incidents/evidence":
            result = INCIDENTS.evidence(body.get("labId"), int(body.get("stage", 1))); return self._send(result or {"error":"LAB_NOT_FOUND"}, 200 if result else 404)
        if path == "/api/incidents/submit":
            result = INCIDENTS.grade(body.get("labId"), body.get("response", "")); return self._send(result or {"error":"LAB_NOT_FOUND"}, 200 if result else 404)
        if path == "/api/operations/start":
            result = OPERATIONS.start(learner_id, body.get("scenarioId")); return self._send(result or {"error":"SCENARIO_NOT_FOUND"}, 201 if result else 404)
        if path == "/api/operations/investigate":
            result = OPERATIONS.investigate(learner_id, body.get("sessionId"), body.get("investigationId")); return self._send(result, 400 if result.get("error") else 200)
        if path == "/api/operations/action":
            result = OPERATIONS.act(learner_id, body.get("sessionId"), body.get("actionId")); return self._send(result, 400 if result.get("error") else 200)
        if path == "/api/operations/conclude":
            response = str(body.get("response", ""))
            if len(response) < 80 or len(response) > 12000: return self._send({"error":"INVALID_CONCLUSION_LENGTH"}, 400)
            result = OPERATIONS.conclude(learner_id, body.get("sessionId"), response); return self._send(result, 400 if result.get("error") else 200)
        if path == "/api/operations/coach":
            result = OPERATIONS.coach(learner_id, body.get("sessionId"), body.get("message", "")); return self._send(result, 400 if result.get("error") else 200)
        if path == "/api/operations/reset":
            deleted = OPERATIONS.reset(learner_id, body.get("sessionId")); return self._send({"reset":deleted}, 200 if deleted else 404)
        if path == "/api/simulation/scenarios/stale-projection": SIMULATION.stale(); return self._send({"status":"scenario-applied", "scenario":"stale-projection", "simulationOnly":True})
        if path == "/api/simulation/reset": SIMULATION.reset(); return self._send({"status":"reset", "simulationOnly":True})
        return self._send({"error":"NOT_FOUND"}, 404)

    def log_message(self, fmt, *args): return


def main():
    print("SAP Commerce Academy vertical slice: http://127.0.0.1:8000")
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()


if __name__ == "__main__": main()
