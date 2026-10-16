"""Typed assessment evaluation.

Complex free text is never accepted by generic token overlap.  Published items
may provide an ``evaluationSpec`` with explicit criteria and evidence rules.
Unstructured complex responses are escalated for guarded semantic review.
"""

import re

from .semantic_assessment import GuardedSemanticAssessor


OBJECTIVE_TYPES = {"single-choice", "multiple-response", "true-false"}
STRUCTURED_TYPES = {
    "api-design", "architecture-decision", "configuration-diagnosis",
    "data-modeling", "debugging", "incident-investigation", "security-review",
    "test-case-design", "case-study", "performance-diagnosis", "short-answer",
}
EXECUTABLE_TYPES = {"code-completion", "programming", "hands-on-practical-challenge", "executable-test"}
COMPLEX_TYPES = STRUCTURED_TYPES | EXECUTABLE_TYPES | {"code-interpretation"}
UNSAFE_MARKERS = (
    "ignore authorization", "disable security", "log the password", "log the authorization header",
    "delete the database", "kill database sessions", "restart everything", "just increase the pool",
)


def _normalise(value):
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _result(item, score, passed, *, strategy, status, details=None, semantic=None):
    return {
        "score": round(max(0.0, min(1.0, float(score))), 2),
        "passed": bool(passed),
        "explanation": item["explanation"],
        "correctAnswer": item["answer"],
        "incorrectRationales": item.get("incorrectRationales", {}),
        "status": status,
        "strategy": strategy,
        "details": details or {},
        "semanticFeedback": semantic or {"status": "not-needed"},
    }


def _objective(item, response):
    expected = item["answer"]
    if item["type"] == "multiple-response":
        actual = response if isinstance(response, list) else []
        score = 1.0 if set(actual) == set(expected) else 0.0
        details = {"expectedCount": len(expected), "receivedCount": len(actual)}
    elif item["type"] == "true-false":
        score = 1.0 if isinstance(response, bool) and response is bool(expected) else 0.0
        details = {"typeChecked": isinstance(response, bool)}
    else:
        score = 1.0 if _normalise(response) == _normalise(expected) else 0.0
        details = {"exactCanonicalMatch": bool(score)}
    return _result(item, score, score == 1.0, strategy="deterministic-objective", status="passed" if score == 1.0 else "needs-remediation", details=details)


def _criteria_spec(item):
    spec = item.get("evaluationSpec")
    if not isinstance(spec, dict):
        return None
    criteria = spec.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        return None
    return spec


def _structured(item, response, spec):
    if not isinstance(response, dict):
        return _result(item, 0.0, False, strategy="deterministic-structured-rubric", status="human-review-required", details={"reason": "STRUCTURED_RESPONSE_REQUIRED", "requiredCriteria": [c.get("id") for c in spec["criteria"]]})
    criteria_results = {}
    total_weight = sum(float(c.get("weight", 0)) for c in spec["criteria"]) or 1.0
    weighted = 0.0
    invalid = []
    for criterion in spec["criteria"]:
        criterion_id = criterion["id"]
        value = response.get("criteria", {}).get(criterion_id)
        required = set(criterion.get("requiredEvidence", []))
        received = set(response.get("evidence", {}).get(criterion_id, []))
        valid_evidence = required <= received
        score = 1.0 if value is True and valid_evidence else 0.0
        if value not in (True, False):
            invalid.append(criterion_id)
        criteria_results[criterion_id] = {"score": score, "requiredEvidence": sorted(required), "receivedEvidence": sorted(received)}
        weighted += float(criterion.get("weight", 0)) * score
    claims = response.get("claims", [])
    claim_text = _normalise(claims)
    unsafe = [marker for marker in UNSAFE_MARKERS if marker in claim_text]
    contradictions = response.get("contradictions", [])
    score = weighted / total_weight
    passed = score >= float(spec.get("passThreshold", 0.8)) and not unsafe and not contradictions and not invalid
    details = {"criteria": criteria_results, "unsafeClaims": unsafe, "contradictions": contradictions, "invalidCriteria": invalid}
    return _result(item, score, passed, strategy="deterministic-structured-rubric", status="passed" if passed else "needs-remediation", details=details)


def evaluate(item, response, *, semantic_assessor=None):
    """Evaluate one item without accepting generic keyword overlap.

    The evaluator returns a review-required result for complex text unless the
    item publishes an explicit structured evaluation specification. An optional
    guarded semantic assessor may add advisory feedback, but cannot change a
    deterministic score or disclose the answer to an external provider.
    """
    if item["type"] in OBJECTIVE_TYPES:
        return _objective(item, response)
    spec = _criteria_spec(item)
    if spec and item["type"] in STRUCTURED_TYPES:
        return _structured(item, response, spec)
    if item["type"] in EXECUTABLE_TYPES:
        return _result(item, 0.0, False, strategy="isolated-executable-test", status="execution-required", details={"reason": "NO_EXECUTION_ARTIFACT"})
    if item["type"] in COMPLEX_TYPES or isinstance(response, str):
        assessor = semantic_assessor or GuardedSemanticAssessor()
        feedback = assessor.review(item, response)
        return _result(item, 0.0, False, strategy="guarded-semantic-escalation", status="human-review-required", details={"reason": "UNSTRUCTURED_COMPLEX_RESPONSE", "reviewStatus": feedback.get("status")}, semantic=feedback)
    return _result(item, 0.0, False, strategy="unsupported-item-type", status="human-review-required", details={"reason": "UNSUPPORTED_ITEM_TYPE"})
