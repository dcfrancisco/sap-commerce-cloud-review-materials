import json
import re
from copy import deepcopy
from pathlib import Path

from .contextual_tutor import ContextualTutor
from .semantic_feedback import GuardedSemanticFeedback


class OperationsSimulation:
    """Deterministic, stateful operations simulator backed by auditable event records."""

    def __init__(self, store, root=None):
        self.store = store
        root = Path(root or Path(__file__).resolve().parents[1])
        self.scenario_dir = root / "content" / "operations" / "scenarios"
        self.scenarios = {}
        for path in self.scenario_dir.glob("*.json"):
            scenario = json.loads(path.read_text()); self.scenarios[scenario["id"]] = scenario
        self.contextual_tutor = ContextualTutor(root)
        self.semantic_feedback = GuardedSemanticFeedback()

    PUBLIC_KEYS = ("id", "version", "title", "difficulty", "estimatedMinutes", "simulationLabel", "track", "moduleId", "products", "roles", "topics", "competencyIds")
    FILTER_FIELDS = {"role":"roles", "product":"products", "difficulty":"difficulty", "competency":"competencyIds", "track":"track", "topic":"topics"}

    def _public_scenario(self, scenario):
        return {key: scenario[key] for key in self.PUBLIC_KEYS if key in scenario}

    def catalog(self, filters=None):
        filters = {key:str(value).strip().lower() for key,value in (filters or {}).items() if value}
        scenarios = []
        for scenario in self.scenarios.values():
            matched = True
            for query_name, query_value in filters.items():
                field = self.FILTER_FIELDS.get(query_name)
                if not field: continue
                actual = scenario.get(field, [])
                values = actual if isinstance(actual, list) else [actual]
                if query_value not in {str(value).lower() for value in values}: matched = False; break
            if matched: scenarios.append(self._public_scenario(scenario))
        return sorted(scenarios, key=lambda item:item["id"])

    def facets(self):
        return {query_name:sorted({str(value) for scenario in self.scenarios.values() for value in (scenario.get(field, []) if isinstance(scenario.get(field, []), list) else [scenario.get(field)]) if value}) for query_name,field in self.FILTER_FIELDS.items()}

    def recommend(self, request, filters=None):
        request_text = str(request or "").strip().lower()[:2000]
        candidates = self.catalog(filters)
        if not candidates:
            return {"recommendation":None,"alternatives":[],"abstained":True,"reason":"No implemented scenario satisfies every requested filter.","filters":filters or {},"facets":self.facets()}
        request_tokens = set(re.findall(r"[a-z0-9]+", request_text))
        ranked = []
        for public in candidates:
            scenario = self.scenarios[public["id"]]
            fields = [scenario.get("title", ""), scenario.get("brief", ""), scenario.get("track", ""), *scenario.get("products", []), *scenario.get("roles", []), *scenario.get("topics", []), *scenario.get("competencyIds", []), *scenario.get("discoveryTerms", [])]
            searchable = " ".join(fields).lower()
            matched_tokens = sorted(request_tokens & set(re.findall(r"[a-z0-9]+", searchable)))
            phrase_hits = [term for term in scenario.get("discoveryTerms", []) if term in request_text]
            score = len(matched_tokens) + 3 * len(phrase_hits)
            ranked.append((score, len(phrase_hits), public["id"], public, matched_tokens, phrase_hits))
        ranked.sort(key=lambda item:(-item[0], -item[1], item[2]))
        best = ranked[0]
        if request_text and best[0] == 0 and not filters:
            return {"recommendation":None,"alternatives":[item[3] for item in ranked],"abstained":True,"reason":"The request does not match an implemented scenario. No new SAP behavior was invented.","filters":{},"facets":self.facets()}
        return {"recommendation":best[3],"alternatives":[item[3] for item in ranked[1:]],"abstained":False,"reason":"Selected from implemented synthetic scenarios using declared product, role, topic, competency, and difficulty metadata.","matchedTerms":sorted(set(best[4] + best[5])),"filters":filters or {}}

    def start(self, learner_id, scenario_id):
        scenario = self.scenarios.get(scenario_id)
        if not scenario: return None
        state = deepcopy(scenario["initialState"])
        state.update({"investigations":[], "actions":[], "unsafeActions":[], "elapsedMinutes":0, "status":"active"})
        session_id = self.store.create_incident_session(learner_id, scenario_id, scenario["version"], state)
        return self._session_view(session_id, scenario_id, scenario, state)

    def _session_view(self, session_id, scenario_id, scenario, state):
        return {"sessionId":session_id, "scenarioId":scenario_id, "version":scenario["version"], "title":scenario["title"], "track":scenario.get("track", "operations-sre"), "moduleId":scenario.get("moduleId"), "simulationLabel":scenario["simulationLabel"], "brief":scenario["brief"], "businessImpact":state["businessImpact"], "status":state.get("status", "active"), "investigationsCompleted":state.get("investigations", []), "actionsTaken":state.get("actions", []), "availableInvestigations":self._available(scenario, state, "investigations"), "availableActions":self._available(scenario, state, "actions")}

    def resume(self, learner_id, session_id):
        session, scenario = self._load(session_id, learner_id)
        if not session or not scenario: return None
        return self._session_view(session_id, session["scenario_id"], scenario, session["state"])

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
        if scenario.get("assessmentMode") == "structured-reasoning":
            return self._conclude_structured(learner_id, session_id, session, scenario, response)
        state = session["state"]; text = str(response).lower(); tokens = set(re.findall(r"[a-z0-9]+", text))
        scoring = scenario["scoring"]
        required_evidence = set(scoring["requiredEvidence"]); evidence_ratio = len(required_evidence & set(state["investigations"])) / len(required_evidence)
        concept_hits = [group for group in scoring["conceptGroups"] if set(group) & tokens]
        diagnosis = len(concept_hits) / len(scoring["conceptGroups"])
        accepted_recoveries = scoring.get("acceptedRecoveries", [scoring["preferredRecovery"]])
        safe_recovery = bool(set(accepted_recoveries) & set(state["actions"]))
        verification = scoring["verificationAction"] in state["actions"]
        escalation_action = scoring.get("escalationAction")
        escalation = not escalation_action or escalation_action in state["actions"]
        integrity_evidence = set(scoring.get("integrityEvidence", []))
        integrity_score = 1.0 if not integrity_evidence or integrity_evidence <= set(state["investigations"]) else 0.0
        communication_terms = set(scoring.get("communicationTerms", ["impact", "timeline", "owner"]))
        improvement_terms = set(scoring.get("improvementTerms", ["rehearsal", "additive", "gate", "runbook", "alert"]))
        unsafe = bool(state["unsafeActions"])
        dimensions = {
            "triage": round(evidence_ratio,2), "diagnosis": round(diagnosis,2),
            "riskAssessment": 0.0 if unsafe else 1.0, "recoveryDecision": 1.0 if safe_recovery else 0.0,
            "dataIntegrity": integrity_score,
            "escalation": 1.0 if escalation else 0.5, "recoveryVerification": 1.0 if verification else 0.0,
            "communication": 1.0 if communication_terms & tokens else 0.5,
            "rootCause": round(diagnosis,2), "improvementPlanning": 1.0 if improvement_terms & tokens else 0.0
        }
        score = round(sum(dimensions.values()) / len(dimensions), 2)
        passed = score >= scoring["passThreshold"] and safe_recovery and verification and not unsafe
        state["status"] = "completed"; state["finalResponse"] = response
        result = {"sessionId":session_id, "score":score, "passed":passed, "dimensions":dimensions, "unsafeActions":state["unsafeActions"], "evidenceReviewed":state["investigations"], "actionsTaken":state["actions"], "referenceRootCause":scenario["solution"]["rootCause"], "recommendedRecovery":scenario["solution"]["recovery"], "feedback":scenario.get("feedback", "An expert pass requires evidence-led diagnosis, a bounded safe recovery, independent verification, and no prohibited action.")}
        dimension_map = scoring.get("competencyDimensions", {})
        competency_scores = {}
        for competency in scenario["competencyIds"]:
            mapped = dimension_map.get(competency, [])
            competency_scores[competency] = round(
                sum(dimensions[name] for name in mapped) / len(mapped), 2
            ) if mapped else score
        result["competencyScores"] = competency_scores
        self.store.update_incident(session_id, state, "conclusion", "submit-conclusion", {"response":response}, {"score":score,"passed":passed})
        self.store.complete_incident(session_id, competency_scores, result); return result

    def _conclude_structured(self, learner_id, session_id, session, scenario, response):
        """Grade structured reasoning fields; prose is feedback, never the score."""
        if not isinstance(response, dict):
            return {"error":"STRUCTURED_REASONING_REQUIRED", "requiredFields":["hypothesis","containment","recovery","verification","prevention","communication"]}
        model = scenario.get("reasoningModel", {})
        state = session["state"]
        revealed = set(state["investigations"])
        taken = set(state["actions"])
        invalid = []
        contradictions = []
        missing = []

        def text_value(value):
            return isinstance(value, str) and bool(value.strip())

        def evidence_ids(value, path):
            if not isinstance(value, list) or not value:
                missing.append(path)
                return set()
            ids = set(value)
            invalid.extend(f"{path}:{item}" for item in ids - revealed)
            return ids & revealed

        hypothesis = response.get("hypothesis")
        if not isinstance(hypothesis, dict):
            missing.append("hypothesis")
            hypothesis = {}
        primary = hypothesis.get("primaryCauseCategory")
        if primary not in model.get("primaryCauseCategories", []):
            contradictions.append("primary cause category is not the governed scenario category")
        supporting = evidence_ids(hypothesis.get("supportingEvidence"), "hypothesis.supportingEvidence")
        if not text_value(hypothesis.get("statement")): missing.append("hypothesis.statement")
        alternatives = hypothesis.get("rejectedAlternatives")
        if not isinstance(alternatives, list) or len(alternatives) < model.get("minimumRejectedAlternatives", 2):
            missing.append("hypothesis.rejectedAlternatives")
            alternatives = []
        alternative_score = 0
        for index, alternative in enumerate(alternatives):
            path = f"hypothesis.rejectedAlternatives[{index}]"
            if not isinstance(alternative, dict):
                invalid.append(path); continue
            category = alternative.get("category")
            if category not in model.get("alternativeCategories", []):
                contradictions.append(f"{path} is not an allowed alternative")
            else:
                alternative_score += 1
            if not text_value(alternative.get("reason")): missing.append(path + ".reason")
            evidence_ids(alternative.get("evidence"), path + ".evidence")

        containment = response.get("containment")
        if not isinstance(containment, dict):
            missing.append("containment"); containment = {}
        containment_action = containment.get("actionId")
        if containment_action not in taken:
            invalid.append("containment.actionId:not-taken")
        if containment_action in state.get("unsafeActions", []) or containment_action in model.get("unsafeActions", []):
            contradictions.append("containment recommends an unsafe action")
        for field in ("rationale", "riskAccepted", "rollbackPlan"):
            if not text_value(containment.get(field)): missing.append("containment." + field)

        recovery = response.get("recovery")
        if not isinstance(recovery, dict):
            missing.append("recovery"); recovery = {}
        recovery_action = recovery.get("actionId")
        if recovery_action not in taken: invalid.append("recovery.actionId:not-taken")
        if recovery_action not in model.get("acceptedRecoveryActions", []): contradictions.append("recovery action is not accepted for this scenario")
        for field in ("rationale", "residualRisk"):
            if not text_value(recovery.get(field)): missing.append("recovery." + field)

        verification = response.get("verification")
        if not isinstance(verification, list) or len(verification) < model.get("minimumVerificationChecks", 3):
            missing.append("verification")
            verification = []
        valid_verification = 0
        for index, check in enumerate(verification):
            path = f"verification[{index}]"
            if not isinstance(check, dict): invalid.append(path); continue
            refs = evidence_ids(check.get("evidence"), path + ".evidence")
            if refs and text_value(check.get("expected")) and text_value(check.get("observed")): valid_verification += 1
            else:
                missing.extend(field for field in (path + ".expected", path + ".observed") if not text_value(check.get(field.rsplit(".", 1)[-1])))
        if model.get("verificationAction") not in taken: contradictions.append("required verification action was not taken")

        prevention = response.get("prevention")
        if not isinstance(prevention, list) or len(prevention) < model.get("minimumPreventionControls", 2):
            missing.append("prevention")
            prevention = []
        valid_prevention = 0
        for index, control in enumerate(prevention):
            path = f"prevention[{index}]"
            if not isinstance(control, dict): invalid.append(path); continue
            if all(text_value(control.get(field)) for field in ("control", "owner", "measure")): valid_prevention += 1
            else: missing.append(path)

        communication = response.get("communication")
        if not isinstance(communication, dict):
            missing.append("communication"); communication = {}
        for field in ("impact", "timeline", "owner", "nextUpdate"):
            if not text_value(communication.get(field)): missing.append("communication." + field)

        dimensions = {
            "hypothesis": 1.0 if primary == model.get("preferredPrimary") and len(supporting) >= model.get("minimumSupportingEvidence", 2) and text_value(hypothesis.get("statement")) else 0.0,
            "supportingEvidence": round(min(1.0, len(supporting) / max(1, model.get("minimumSupportingEvidence", 2))), 2),
            "rejectedAlternatives": round(min(1.0, alternative_score / max(1, model.get("minimumRejectedAlternatives", 2))), 2),
            "containment": 1.0 if containment_action == model.get("containmentAction") and not any(item.startswith("containment") for item in invalid) else 0.0,
            "recovery": 1.0 if recovery_action in model.get("acceptedRecoveryActions", []) and not any(item.startswith("recovery") for item in invalid) else 0.0,
            "verification": round(min(1.0, valid_verification / max(1, model.get("minimumVerificationChecks", 3))), 2),
            "prevention": round(min(1.0, valid_prevention / max(1, model.get("minimumPreventionControls", 2))), 2),
            "communication": 1.0 if not any(item.startswith("communication") for item in missing) else 0.0,
        }
        if contradictions or invalid or state.get("unsafeActions"):
            dimensions["safetyAndConsistency"] = 0.0
        else:
            dimensions["safetyAndConsistency"] = 1.0
        dimensions["riskAssessment"] = dimensions["safetyAndConsistency"]
        score = round(sum(dimensions.values()) / len(dimensions), 2)
        core = ("hypothesis", "rejectedAlternatives", "containment", "recovery", "verification", "prevention", "communication")
        passed = not missing and not invalid and not contradictions and dimensions["safetyAndConsistency"] >= 0.8 and all(dimensions[key] >= 0.8 for key in core) and score >= model.get("passThreshold", 0.8)
        state["status"] = "completed"; state["finalResponse"] = response
        result = {
            "sessionId":session_id, "assessmentMode":"structured-reasoning", "score":score, "passed":passed,
            "dimensions":dimensions, "unsafeActions":state.get("unsafeActions", []), "missingFields":sorted(set(missing)), "invalidReferences":sorted(set(invalid)),
            "contradictions":sorted(set(contradictions)), "evidenceReviewed":state["investigations"], "actionsTaken":state["actions"],
            "referenceRootCause":scenario["solution"]["rootCause"], "recommendedRecovery":scenario["solution"]["recovery"],
            "feedback":"Deterministic scoring uses selected evidence, governed action IDs, verification records, and prevention structure. Prose is retained for guarded semantic feedback and does not substitute for missing evidence."
        }
        dimension_map = scenario["scoring"].get("competencyDimensions", {})
        result["competencyScores"] = {
            competency: round(sum(dimensions[name] for name in names if name in dimensions) / len([name for name in names if name in dimensions]), 2) if [name for name in names if name in dimensions] else score
            for competency, names in dimension_map.items()
        }
        result["semanticFeedback"] = self.semantic_feedback.review(response, result, scenario)
        self.store.update_incident(session_id, state, "conclusion", "submit-structured-conclusion", {"response":response}, {"score":score,"passed":passed,"dimensions":dimensions})
        self.store.complete_incident(session_id, result["competencyScores"], result)
        return result

    def coach(self, learner_id, session_id, message, mode="tutoring"):
        session, scenario = self._load(session_id, learner_id)
        if not session: return {"error":"SESSION_NOT_FOUND"}
        state = session["state"]; message_text = str(message).lower()
        if session["status"] == "completed":
            result = session["result"]
            return {"mode":"post-incident-review","response":"Compare your event stream with the scored dimensions. The reference root cause was: " + result["referenceRootCause"],"citations":scenario["sourceIds"],"confidence":"deterministic-scenario-result","remediation":[key for key,value in result["dimensions"].items() if value < 0.8]}
        revealed = []
        for item_id in state.get("investigations", []):
            item = next((candidate for candidate in scenario.get("investigations", []) if candidate["id"] == item_id), None)
            if item: revealed.append({"id":item_id,"evidence":item.get("evidence", {})})
        prior_attempts = self.store.incident_history(learner_id).get("sessions", [])[-3:]
        result = self.contextual_tutor.answer({"scenario":scenario,"state":state,"message":message,"mode":mode,"revealedEvidence":revealed,"availableInvestigations":self._available(scenario,state,"investigations"),"availableActions":self._available(scenario,state,"actions"),"priorAttempts":prior_attempts,"references":scenario.get("sourceIds", [])})
        self.store.update_incident(session_id, state, "tutor", "coach", {"message":str(message)[:2000]}, result); return result

    def reset(self, learner_id, session_id):
        return self.store.reset_incident(session_id, learner_id)
