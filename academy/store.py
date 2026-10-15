import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


class ProgressStore:
    """Local learner persistence. Learner data is separate from published content."""

    def __init__(self, path=None):
        self.path = Path(path or Path(__file__).resolve().parents[1] / "data" / "progress.sqlite3")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
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
        CREATE TABLE IF NOT EXISTS incident_sessions(
          id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, scenario_id TEXT NOT NULL,
          scenario_version TEXT NOT NULL, state_json TEXT NOT NULL, result_json TEXT,
          status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS incident_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, sequence INTEGER NOT NULL,
          event_type TEXT NOT NULL, action_id TEXT NOT NULL, payload_json TEXT NOT NULL,
          result_json TEXT NOT NULL, created_at TEXT NOT NULL,
          UNIQUE(session_id, sequence));
        CREATE TABLE IF NOT EXISTS incident_evidence(
          id INTEGER PRIMARY KEY AUTOINCREMENT, learner_id TEXT NOT NULL, competency_id TEXT NOT NULL,
          session_id TEXT NOT NULL, score REAL NOT NULL, passed INTEGER NOT NULL, created_at TEXT NOT NULL);
        """)
        self.db.commit()

    def create_incident_session(self, learner_id, scenario_id, scenario_version, state):
        now = datetime.now(timezone.utc).isoformat(); session_id = str(uuid.uuid4())
        self.db.execute("INSERT INTO incident_sessions(id,learner_id,scenario_id,scenario_version,state_json,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (session_id, learner_id, scenario_id, scenario_version, json.dumps(state), "active", now, now))
        self.db.commit(); return session_id

    def incident_session(self, session_id, learner_id=None):
        sql = "SELECT * FROM incident_sessions WHERE id=?"; params = [session_id]
        if learner_id is not None: sql += " AND learner_id=?"; params.append(learner_id)
        row = self.db.execute(sql, params).fetchone()
        if not row: return None
        result = dict(row); result["state"] = json.loads(result.pop("state_json")); result["result"] = json.loads(result.pop("result_json")) if result["result_json"] else None
        return result

    def update_incident(self, session_id, state, event_type, action_id, payload, result):
        now = datetime.now(timezone.utc).isoformat()
        sequence = self.db.execute("SELECT COUNT(*) FROM incident_events WHERE session_id=?", (session_id,)).fetchone()[0] + 1
        self.db.execute("INSERT INTO incident_events(session_id,sequence,event_type,action_id,payload_json,result_json,created_at) VALUES(?,?,?,?,?,?,?)", (session_id, sequence, event_type, action_id, json.dumps(payload), json.dumps(result), now))
        self.db.execute("UPDATE incident_sessions SET state_json=?,updated_at=? WHERE id=?", (json.dumps(state), now, session_id)); self.db.commit()

    def complete_incident(self, session_id, competencies, result):
        session = self.incident_session(session_id); now = datetime.now(timezone.utc).isoformat()
        self.db.execute("UPDATE incident_sessions SET status='completed',result_json=?,updated_at=? WHERE id=?", (json.dumps(result), now, session_id))
        for competency_id, score in competencies.items():
            self.db.execute("INSERT INTO incident_evidence(learner_id,competency_id,session_id,score,passed,created_at) VALUES(?,?,?,?,?,?)", (session["learner_id"], competency_id, session_id, score, int(score >= 0.8), now))
        self.db.commit()

    def incident_history(self, learner_id):
        sessions = self.db.execute("SELECT id,scenario_id,scenario_version,status,result_json,created_at,updated_at FROM incident_sessions WHERE learner_id=? ORDER BY created_at DESC", (learner_id,)).fetchall()
        evidence = self.db.execute("SELECT competency_id,MAX(score) score,MAX(passed) passed,COUNT(*) attempts FROM incident_evidence WHERE learner_id=? GROUP BY competency_id", (learner_id,)).fetchall()
        return {"sessions":[{**dict(row), "result":json.loads(row["result_json"]) if row["result_json"] else None} for row in sessions], "competencies":[dict(row) for row in evidence]}

    def reset_incident(self, session_id, learner_id):
        row = self.incident_session(session_id, learner_id)
        if not row: return False
        self.db.execute("DELETE FROM incident_events WHERE session_id=?", (session_id,)); self.db.execute("DELETE FROM incident_evidence WHERE session_id=?", (session_id,)); self.db.execute("DELETE FROM incident_sessions WHERE id=?", (session_id,)); self.db.commit(); return True

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
        return {"learnerId": learner_id, "attempts": [dict(x) for x in attempts], "competencies": [dict(x) for x in evidence], "incidents": self.incident_history(learner_id)}
