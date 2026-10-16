import json
import os
import urllib.request


class ContextualTutorProvider:
    """Provider-neutral contract for incident coaching adapters."""

    def answer(self, context):
        raise NotImplementedError


class HttpContextualTutor(ContextualTutorProvider):
    """Configurable model adapter; the local engine remains authoritative."""

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def answer(self, context):
        scenario = dict(context["scenario"])
        for hidden in ("reasoningModel", "referenceRootCause", "recommendedRecovery"):
            scenario.pop(hidden, None)
        payload = {
            "scenario": {"id": scenario.get("id"), "title": scenario.get("title"), "topics": scenario.get("topics", []), "sourceIds": scenario.get("sourceIds", [])},
            "mode": context.get("mode", "tutoring"),
            "question": str(context.get("message", ""))[:4000],
            "revealedEvidence": context.get("revealedEvidence", []),
            "actionsTaken": context.get("state", {}).get("actions", []),
            "availableInvestigations": context.get("availableInvestigations", []),
            "availableActions": context.get("availableActions", []),
            "priorAttempts": context.get("priorAttempts", []),
            "references": sorted(set(scenario.get("sourceIds", []) + context.get("references", []))),
            "instruction": "Answer as a tutor. Cite only supplied references. Never reveal an active assessment solution or invent SAP facts.",
        }
        request = urllib.request.Request(self.endpoint, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=10) as result:
            response = json.loads(result.read().decode())
        text = response.get("response") or response.get("answer")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("configured tutor returned no response")
        return {"response": text[:8000], "citations": response.get("citations", []), "confidence": response.get("confidence", "uncertain"), "provider": "configured-http", "uncertainty": response.get("uncertainty", "External provider response requires grounding review.")}


class LocalContextualTutor(ContextualTutorProvider):
    """Deterministic local adapter; it uses incident state, not a prompt script."""

    def answer(self, context):
        scenario = context["scenario"]
        state = context["state"]
        message = str(context.get("message", "")).strip()
        lowered = message.lower()
        examination = context.get("mode") == "examination"
        active = state.get("status") == "active"
        citations = sorted(set(scenario.get("sourceIds", []) + scenario.get("tutor", {}).get("citations", [])))

        if active and any(term in lowered for term in ("answer", "solution", "root cause", "what is the cause")):
            response = (
                "I will not reveal the reference solution while this incident is active. "
                "State your current hypothesis, cite the evidence you have actually revealed, "
                "name one alternative, and say what observation would falsify your hypothesis."
            )
            if examination:
                response += " Examination mode provides no additional investigative hint beyond the available evidence."
            return self._result(response, citations, "solution-withheld", context)

        if not message:
            response = "Ask a concrete question about the revealed evidence, current action risk, or the next hypothesis test."
            return self._result(response, citations, "grounded-context", context)

        revealed = context.get("revealedEvidence", [])
        available = context.get("availableInvestigations", [])
        actions = context.get("availableActions", [])
        if any(term in lowered for term in ("what do we know", "summarize", "current evidence")):
            labels = [item.get("id") for item in revealed]
            response = "Revealed evidence IDs: " + (", ".join(labels) if labels else "none yet") + ". I can summarize only evidence already disclosed."
        elif any(term in lowered for term in ("what next", "next step", "inspect", "investigate")):
            choices = [item.get("label") for item in available]
            response = "Choose the next evidence request from the available set: " + ("; ".join(choices) if choices else "no further evidence is currently available") + "."
        elif any(term in lowered for term in ("risk", "safe", "action")):
            choices = [f"{item.get('label')} (risk={item.get('risk')}, permitted={item.get('permitted')})" for item in actions]
            response = "Action context is limited to: " + ("; ".join(choices) if choices else "no action is currently available") + ". Explain the evidence and consequence before acting."
        elif any(term in lowered for term in ("why", "explain", "interpret")) and revealed:
            last = revealed[-1]
            evidence = last.get("evidence", {})
            response = "The latest disclosed record is " + str(last.get("id")) + ". Its observed interpretation is: " + str(evidence.get("interpretation", evidence.get("finding", evidence.get("observation", "No interpretation is published for this record."))))
        else:
            topics = [str(topic) for topic in scenario.get("topics", [])]
            domain_hint = "storefront site" if any(topic in topics for topic in ("spartacus", "ssr", "hydration")) else "catalog synchronized/search" if "catalog-synchronization" in topics else "the current commerce operation"
            response = (
                f"I have the active {domain_hint} scenario, revealed evidence, action history, and competency rubric in context. "
                "Relate your question to one observation, one competing hypothesis, and one falsification test."
            )
        return self._result(response, citations, "grounded-context", context)

    def _result(self, response, citations, confidence, context):
        return {
            "mode":"examination-coaching" if context.get("mode") == "examination" else "active-incident-coaching",
            "interactionMode":context.get("mode", "tutoring"),
            "response":response,
            "citations":citations,
            "confidence":confidence,
            "provider":"local-contextual",
            "context":{"scenarioId":context["scenario"]["id"],"revealedEvidenceCount":len(context.get("revealedEvidence", [])),"actionsTaken":context["state"].get("actions", []),"rubricDimensions":list(context.get("scenario", {}).get("scoring", {}).get("competencyDimensions", {}).keys())},
            "uncertainty":"The local adapter is grounded in the deterministic scenario and disclosed records. It does not infer undocumented SAP platform behavior."
        }


class ContextualTutor:
    """Stable integration boundary for local or future hosted model providers."""

    def __init__(self, root=None, provider=None):
        endpoint = provider or os.getenv("ACADEMY_TUTOR_ENDPOINT")
        self.provider_name = "configured-http" if endpoint else "local"
        self.provider = HttpContextualTutor(endpoint) if endpoint else LocalContextualTutor()

    def answer(self, context):
        try:
            result = self.provider.answer(context)
        except Exception as exc:
            result = LocalContextualTutor().answer(context)
            result["provider"] = "local-fallback"
            result["uncertainty"] = "Configured AI provider unavailable; deterministic local coaching was used. " + str(exc)[:160]
            result["fallback"] = True
        # Guard provider output: active sessions may never receive stored solutions.
        if context["state"].get("status") == "active":
            forbidden = ("referenceRootCause", "recommendedRecovery", "preferred recovery")
            if any(token.lower() in str(result.get("response", "")).lower() for token in forbidden):
                return {"mode":result.get("mode"),"response":"I cannot disclose the active assessment solution.","citations":result.get("citations", []),"confidence":"solution-withheld","provider":result.get("provider"),"context":result.get("context"),"uncertainty":result.get("uncertainty")}
        return result
