import re


class ContextualTutorProvider:
    """Provider-neutral contract for incident coaching adapters."""

    def answer(self, context):
        raise NotImplementedError


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
        self.provider_name = provider or "local"
        self.provider = LocalContextualTutor()

    def answer(self, context):
        result = self.provider.answer(context)
        # Guard provider output: active sessions may never receive stored solutions.
        if context["state"].get("status") == "active":
            forbidden = ("referenceRootCause", "recommendedRecovery")
            if any(token.lower() in str(result.get("response", "")).lower() for token in forbidden):
                return {"mode":result.get("mode"),"response":"I cannot disclose the active assessment solution.","citations":result.get("citations", []),"confidence":"solution-withheld","provider":result.get("provider"),"context":result.get("context"),"uncertainty":result.get("uncertainty")}
        return result
