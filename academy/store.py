import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ProgressStore:
    """Local learner persistence. Learner data is separate from published content."""

    def __init__(self, path=None):
        self.path = Path(path or Path(__file__).resolve().parents[1] / "data" / "progress.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS attempts(
          id INTEGER PRIMARY KEY AUTOINCREMENT, learner_id TEXT NOT NULL, item_id TEXT NOT NULL,
          response_json TEXT NOT NULL, score REAL NOT NULL, passed INTEGER NOT NULL,
          feedback_json TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS evidence(
          id INTEGER PRIMARY KEY AUTOINCREMENT, learner_id TEXT NOT NULL, competency_id TEXT NOT NULL,
          attempt_id INTEGER NOT NULL, score REAL NOT NULL, passed INTEGER NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS progress(
          learner_id TEXT NOT NULL, module_id TEXT NOT NULL, last_item_id TEXT, updated_at TEXT NOT NULL,
          PRIMARY KEY(learner_id, module_id));
        """)
        self.db.commit()

    def record(self, learner_id, item, response, result):
        now = datetime.now(timezone.utc).isoformat()
        cur = self.db.execute("INSERT INTO attempts(learner_id,item_id,response_json,score,passed,feedback_json,created_at) VALUES(?,?,?,?,?,?,?)", (learner_id, item["id"], json.dumps(response), result["score"], int(result["passed"]), json.dumps(result), now))
        attempt_id = cur.lastrowid
        for competency_id in item["competencyIds"]:
            self.db.execute("INSERT INTO evidence(learner_id,competency_id,attempt_id,score,passed,created_at) VALUES(?,?,?,?,?,?)", (learner_id, competency_id, attempt_id, result["score"], int(result["passed"]), now))
        self.db.execute("INSERT INTO progress(learner_id,module_id,last_item_id,updated_at) VALUES(?,?,?,?) ON CONFLICT(learner_id,module_id) DO UPDATE SET last_item_id=excluded.last_item_id,updated_at=excluded.updated_at", (learner_id, item["moduleId"], item["id"], now))
        self.db.commit()
        return attempt_id

    def summary(self, learner_id):
        attempts = self.db.execute("SELECT item_id,score,passed,created_at FROM attempts WHERE learner_id=? ORDER BY id DESC", (learner_id,)).fetchall()
        evidence = self.db.execute("SELECT competency_id,MAX(score) score,MAX(passed) passed,COUNT(*) attempts FROM evidence WHERE learner_id=? GROUP BY competency_id", (learner_id,)).fetchall()
        return {"learnerId": learner_id, "attempts": [dict(x) for x in attempts], "competencies": [dict(x) for x in evidence]}
