import json
import re
from copy import deepcopy
from pathlib import Path


class OperationsSimulation:
    """Deterministic, stateful operations simulator backed by auditable event records."""

    def __init__(self, store, root=None):
        self.store = store
        root = Path(root or Path(__file__).resolve().parents[1])
        self.scenario_dir = root / "content" / "operations" / "scenarios"
        self.scenarios = {}
        for path in self.scenario_dir.glob("*.json"):
            scenario = json.loads(path.read_text()); self.scenarios[scenario["id"]] = scenario

    def catalog(self):
        return [{key: scenario[key] for key in ("id", "version", "title", "difficulty", "estimatedMinutes", "simulationLabel")} for scenario in self.scenarios.values()]

    def start(self, learner_id, scenario_id):
        scenario = self.scenarios.get(scenario_id)
        if not scenario: return None
        state = deepcopy(scenario["initialState"])
        state.update({"investigations":[], "actions":[], "unsafeActions":[], "elapsedMinutes":0, "status":"active"})
        session_id = self.store.create_incident_session(learner_id, scenario_id, scenario["version"], state)
        return {"sessionId":session_id, "scenarioId":scenario_id, "version":scenario["version"], "title":scenario["title"], "simulationLabel":scenario["simulationLabel"], "brief":scenario["brief"], "businessImpact":state["businessImpact"], "availableInvestigations":self._available(scenario, state, "investigations"), "availableActions":self._available(scenario, state, "actions")}

    def _available(self, scenario, state, section):
        done = set(state["investigations"] + state["actions"])
        return [{"id":item["id"], "label":item["label"], "risk":item.get("risk", "none"), "permitted":item.get("permitted", True)} for item in scenario[section] if item["id"] not in done and set(item.get("requires", [])) <= done]

    def _load(self, session_id, learner_id):
        session = self.store.incident_session(session_id, learner_id)
        if not session: return None, None
        return session, self.scenarios.get(session["scenario_id"])

    def investigate(self, learner_id, session_id, investigation_id):
        session, scenario = self._load(session_id, learner_id)
        if not session or session["status"] != "active": return {"error":"SESSION_NOT_ACTIVE"}
        state = session["state"]; item = next((x for x in scenario["investigations"] if x["id"] == investigation_id), None)
        available = {x["id"] for x in self._available(scenario, state, "investigations")}
        if not item: return {"error":"UNKNOWN_INVESTIGATION"}
        if investigation_id not in available: return {"error":"INVESTIGATION_NOT_AVAILABLE"}
        state["investigations"].append(investigation_id); state["elapsedMinutes"] += item["minutes"]
        result = {"investigationId":investigation_id, "evidence":item["evidence"], "elapsedMinutes":state["elapsedMinutes"], "businessImpact":state["businessImpact"], "availableInvestigations":self._available(scenario,state,"investigations"), "availableActions":self._available(scenario,state,"actions")}
        self.store.update_incident(session_id, state, "investigation", investigation_id, {}, result); return result

    def act(self, learner_id, session_id, action_id):
        session, scenario = self._load(session_id, learner_id)
        if not session or session["status"] != "active": return {"error":"SESSION_NOT_ACTIVE"}
        state = session["state"]; item = next((x for x in scenario["actions"] if x["id"] == action_id), None)
        available = {x["id"] for x in self._available(scenario, state, "actions")}
        if not item: return {"error":"UNKNOWN_ACTION"}
        if action_id not in available: return {"error":"ACTION_NOT_AVAILABLE"}
        state["actions"].append(action_id); state["elapsedMinutes"] += item["minutes"]
        if not item.get("permitted", True) or item.get("risk") == "critical": state["unsafeActions"].append(action_id)
        for key, value in item.get("stateChanges", {}).items(): state[key] = value
        result = {"actionId":action_id, "outcome":item["outcome"], "consequence":item["consequence"], "permitted":item.get("permitted",True), "risk":item.get("risk","none"), "elapsedMinutes":state["elapsedMinutes"], "businessImpact":state["businessImpact"], "serviceState":state["serviceState"], "availableInvestigations":self._available(scenario,state,"investigations"), "availableActions":self._available(scenario,state,"actions")}
        self.store.update_incident(session_id, state, "action", action_id, {}, result); return result

    def conclude(self, learner_id, session_id, response):
        session, scenario = self._load(session_id, learner_id)
        if not session or session["status"] != "active": return {"error":"SESSION_NOT_ACTIVE"}
        state = session["state"]; text = str(response).lower(); tokens = set(re.findall(r"[a-z0-9]+", text))
        required_evidence = set(scenario["scoring"]["requiredEvidence"]); evidence_ratio = len(required_evidence & set(state["investigations"])) / len(required_evidence)
        concept_hits = [group for group in scenario["scoring"]["conceptGroups"] if set(group) & tokens]
        diagnosis = len(concept_hits) / len(scenario["scoring"]["conceptGroups"])
        safe_recovery = scenario["scoring"]["preferredRecovery"] in state["actions"]
        verification = scenario["scoring"]["verificationAction"] in state["actions"]
        escalation = scenario["scoring"]["escalationAction"] in state["actions"]
        unsafe = bool(state["unsafeActions"])
        dimensions = {
            "triage": round(evidence_ratio,2), "diagnosis": round(diagnosis,2),
            "riskAssessment": 0.0 if unsafe else 1.0, "recoveryDecision": 1.0 if safe_recovery else 0.0,
            "dataIntegrity": 1.0 if {"inspect-backup","inspect-schema-diff"} <= set(state["investigations"]) else 0.0,
            "escalation": 1.0 if escalation else 0.5, "recoveryVerification": 1.0 if verification else 0.0,
            "communication": 1.0 if {"impact","timeline","owner"} & tokens else 0.5,
            "rootCause": round(diagnosis,2), "improvementPlanning": 1.0 if {"rehearsal","additive","gate","runbook","alert"} & tokens else 0.0
        }
        score = round(sum(dimensions.values()) / len(dimensions), 2)
        passed = score >= scenario["scoring"]["passThreshold"] and safe_recovery and verification and not unsafe
        state["status"] = "completed"; state["finalResponse"] = response
        result = {"sessionId":session_id, "score":score, "passed":passed, "dimensions":dimensions, "unsafeActions":state["unsafeActions"], "evidenceReviewed":state["investigations"], "actionsTaken":state["actions"], "referenceRootCause":scenario["solution"]["rootCause"], "recommendedRecovery":scenario["solution"]["recovery"], "feedback":"Expert pass requires evidence-led diagnosis, safe schema-compatible recovery, independent verification, and no prohibited action."}
        competency_scores = {competency:score for competency in scenario["competencyIds"]}
        self.store.update_incident(session_id, state, "conclusion", "submit-conclusion", {"response":response}, {"score":score,"passed":passed})
        self.store.complete_incident(session_id, competency_scores, result); return result

    def coach(self, learner_id, session_id, message):
        session, scenario = self._load(session_id, learner_id)
        if not session: return {"error":"SESSION_NOT_FOUND"}
        state = session["state"]; message_text = str(message).lower()
        if session["status"] == "completed":
            result = session["result"]
            return {"mode":"post-incident-review","response":"Compare your event stream with the scored dimensions. The reference root cause was: " + result["referenceRootCause"],"citations":scenario["sourceIds"],"confidence":"deterministic-scenario-result","remediation":[key for key,value in result["dimensions"].items() if value < 0.8]}
        if "root cause" in message_text or "answer" in message_text or "solution" in message_text:
            response = "I will not reveal the reference solution during an active incident. State your current hypothesis, the evidence supporting it, and the observation that would disprove it."
        elif "inspect-deployment-history" not in state["investigations"]:
            response = "Start by establishing chronology: which environment, deployment, build, commit, migration mode, start time, and failure time define this incident?"
        elif "inspect-error-logs" not in state["investigations"]:
            response = "You have a deployment boundary. Which time-bounded, correlated log evidence would distinguish the first migration failure from later startup symptoms?"
        elif "inspect-api-metrics" not in state["investigations"]:
            response = "Test competing causes with metrics. Did JVM, database, dependency, or API indicators deteriorate before the activation failure?"
        elif "inspect-schema-diff" not in state["investigations"]:
            response = "Before proposing rollback, identify which persistent changes completed and what evidence establishes old-build compatibility."
        elif "inspect-backup" not in state["investigations"] or "inspect-business-transactions" not in state["investigations"]:
            response = "Recovery affects more than application health. Establish backup scope and the external transaction divergence window."
        elif "freeze-deployments" not in state["actions"]:
            response = "Your evidence is sufficient to contain change risk. Who owns incident command, and should further deployments remain possible while recovery is selected?"
        elif "redeploy-corrected-migrate" not in state["actions"] and "restore-predeploy-backup" not in state["actions"]:
            response = "Defend a recovery choice against schema compatibility, RPO/RTO, media/search scope, and payment/order reconciliation."
        elif "validate-recovery" not in state["actions"]:
            response = "A started application is not yet a recovered commerce service. Define independent technical and business acceptance checks."
        else:
            response = "Prepare your conclusion: timeline, impact, cause with uncertainty, safe recovery rationale, integrity checks, escalation, and systemic prevention."
        result = {"mode":"active-incident-coaching","response":response,"citations":["RS-SAP-DEPLOY-ROLLBACK","RS-SAP-ENV-LOGS","lesson:OPS-D03-M01"],"confidence":"grounded-scenario-guidance","uncertainty":"Simulation coaching distinguishes documented product boundaries from synthetic scenario behavior."}
        self.store.update_incident(session_id, state, "tutor", "coach", {"message":str(message)[:2000]}, result); return result

    def reset(self, learner_id, session_id):
        return self.store.reset_incident(session_id, learner_id)
