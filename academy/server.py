import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SIMULATION = None


def load_json(relative):
    return json.loads((ROOT / relative).read_text())


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload, status=200, content_type="application/json"):
        body = payload.encode() if isinstance(payload, str) else json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        global SIMULATION
        if SIMULATION is None:
            from .simulation import CatalogSimulation
            SIMULATION = CatalogSimulation()
        path = urlparse(self.path).path
        if path == "/":
            return self._send((ROOT / "academy" / "index.html").read_text(), content_type="text/html; charset=utf-8")
        if path == "/api/course": return self._send(load_json("content/course.json"))
        if path == "/api/module/M01": return self._send({"id":"M01", "markdown":(ROOT / "content/modules/01-architecture-fundamentals.md").read_text(), "competencies":load_json("content/competencies.json"), "lab":load_json("content/labs/catalog-foundation.json")})
        if path == "/api/assessments/M01": return self._send(load_json("content/assessments/module-01.json"))
        if path.startswith("/api/simulation/products/"): return self._send(SIMULATION.product(path.rsplit("/", 1)[-1]))
        return self._send({"error":"NOT_FOUND"}, 404)

    def do_POST(self):
        global SIMULATION
        if SIMULATION is None:
            from .simulation import CatalogSimulation
            SIMULATION = CatalogSimulation()
        path = urlparse(self.path).path
        if path == "/api/simulation/scenarios/stale-projection":
            SIMULATION.stale(); return self._send({"status":"scenario-applied", "scenario":"stale-projection", "simulationOnly":True})
        if path == "/api/simulation/reset":
            SIMULATION.reset(); return self._send({"status":"reset", "simulationOnly":True})
        return self._send({"error":"NOT_FOUND"}, 404)

    def log_message(self, fmt, *args): return


def main():
    print("SAP Commerce Academy vertical slice: http://127.0.0.1:8000")
    HTTPServer(("127.0.0.1", 8000), Handler).serve_forever()


if __name__ == "__main__": main()
