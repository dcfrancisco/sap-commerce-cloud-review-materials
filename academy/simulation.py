from datetime import datetime, timedelta, timezone
from uuid import uuid4


class CatalogSimulation:
    """Deterministic practice state machine; it is not the SAP Commerce runtime."""

    def __init__(self):
        self.reset()

    def reset(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        self.source = {"code": "P100", "name": "Athena Trail Backpack", "price": 89.0, "currency": "USD", "updatedAt": now.isoformat()}
        self.projection = dict(self.source)

    def stale(self):
        source_time = datetime.fromisoformat(self.source["updatedAt"])
        self.projection["name"] = "Legacy Trail Backpack"
        self.projection["updatedAt"] = (source_time - timedelta(minutes=7)).isoformat()

    def product(self, code):
        correlation_id = str(uuid4())
        if code != self.source["code"]:
            return {"status": 404, "correlationId": correlation_id, "error": "PRODUCT_NOT_FOUND", "code": code}
        source_time = datetime.fromisoformat(self.source["updatedAt"])
        projection_time = datetime.fromisoformat(self.projection["updatedAt"])
        diagnostics = []
        if projection_time < source_time:
            diagnostics.append("PROJECTION_STALE: sourceUpdatedAt is newer than projectionUpdatedAt")
        return {"status": 200, "correlationId": correlation_id, "product": self.projection, "sourceUpdatedAt": self.source["updatedAt"], "projectionUpdatedAt": self.projection["updatedAt"], "diagnostics": diagnostics}
