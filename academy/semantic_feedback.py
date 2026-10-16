import json
import os
import urllib.request


class SemanticFeedbackProvider:
    def review(self, response, deterministic_result, scenario):
        raise NotImplementedError


class LocalSemanticFeedback(SemanticFeedbackProvider):
    """Safe local adapter. It comments on structure and clarity, never on correctness."""

    def review(self, response, deterministic_result, scenario):
        notes = []
        hypothesis = response.get("hypothesis", {}) if isinstance(response, dict) else {}
        if len(str(hypothesis.get("statement", "")).split()) < 6:
            notes.append("Expand the hypothesis statement with mechanism and affected journey.")
        if deterministic_result.get("contradictions"):
            notes.append("Resolve the deterministic contradictions before treating the explanation as defensible.")
        if deterministic_result.get("missingFields"):
            notes.append("Complete the missing structured evidence or decision fields.")
        if not notes:
            notes.append("The explanation is sufficiently explicit for human review; deterministic evidence and safety scores remain authoritative.")
        return {"provider":"local-guarded","confidence":"feedback-only","affectsDeterministicScore":False,"notes":notes,"uncertainty":"This adapter does not verify SAP facts, infer hidden evidence, or change the assessment result."}


class HttpSemanticFeedback(SemanticFeedbackProvider):
    """Optional provider-neutral JSON adapter; never receives the stored solution."""

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def review(self, response, deterministic_result, scenario):
        payload = {"response":response,"deterministicResult":{key:deterministic_result.get(key) for key in ("dimensions","missingFields","invalidReferences","contradictions")},"scenarioId":scenario.get("id"),"instruction":"Return feedback only. Do not provide a solution or alter deterministic scores."}
        request = urllib.request.Request(self.endpoint, data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=4) as result:
            body = json.loads(result.read())
        notes = body.get("notes", []) if isinstance(body, dict) else []
        if not isinstance(notes, list): notes = []
        return {"provider":"configured-http","confidence":"provider-feedback","affectsDeterministicScore":False,"notes":[str(item)[:500] for item in notes[:5]],"uncertainty":"External semantic feedback is advisory and requires human review."}


class GuardedSemanticFeedback:
    def __init__(self):
        endpoint = os.getenv("ACADEMY_SEMANTIC_ENDPOINT")
        self.provider = HttpSemanticFeedback(endpoint) if endpoint else LocalSemanticFeedback()

    def review(self, response, deterministic_result, scenario):
        try:
            result = self.provider.review(response, deterministic_result, scenario)
        except Exception as exc:
            result = {"provider":"guarded-fallback","confidence":"unavailable","affectsDeterministicScore":False,"notes":["Semantic feedback provider unavailable; deterministic evaluation remains authoritative."],"uncertainty":str(exc)[:200]}
        result["affectsDeterministicScore"] = False
        return result
