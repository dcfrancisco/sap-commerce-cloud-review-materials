import re


def _tokens(value):
    return set(re.findall(r"[a-z0-9]+", str(value).lower()))


def evaluate(item, response):
    expected = item["answer"]
    if item["type"] == "multiple-response":
        score = 1.0 if set(response if isinstance(response, list) else []) == set(expected) else 0.0
    elif item["type"] == "true-false":
        score = 1.0 if bool(response) is bool(expected) else 0.0
    else:
        actual = _tokens(response)
        target = _tokens(expected)
        overlap = len(actual & target) / max(1, len(target))
        score = 1.0 if actual == target or overlap >= (0.55 if item["type"] in {"short-answer", "debugging", "case-study", "architecture-decision", "api-design", "security-review", "data-modeling", "test-case-design"} else 0.8) else round(overlap, 2)
    passed = score >= 0.8
    return {"score": round(score, 2), "passed": passed, "explanation": item["explanation"], "correctAnswer": expected, "incorrectRationales": item.get("incorrectRationales", {}), "status":"passed" if passed else "needs-remediation"}
