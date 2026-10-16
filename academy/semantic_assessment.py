"""Guarded semantic feedback for complex assessment responses.

This adapter is advisory only. It never receives the stored answer, never
assigns a score, and falls back to explicit human review when no configured
provider is available or the provider response is malformed.
"""

import json
import os
import urllib.request


class SemanticAssessor:
    def review(self, item, response):
        raise NotImplementedError


class LocalAssessmentReview(SemanticAssessor):
    def review(self, item, response):
        text = str(response).strip()
        return {
            "status": "human-review-required",
            "provider": "local-guarded",
            "notes": ["Complex free-text responses require structured evidence or qualified review; token overlap is not used."],
            "confidence": "uncertain" if text else "none",
            "affectsScore": False,
            "uncertainty": "No semantic model is configured. No technical correctness claim was made.",
        }


class HttpAssessmentReview(SemanticAssessor):
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def review(self, item, response):
        payload = {
            "itemId": item.get("id"),
            "itemType": item.get("type"),
            "prompt": item.get("prompt"),
            "rubric": item.get("rubric", {}),
            "response": str(response)[:10000],
            "instruction": "Return advisory observations only. Do not assign a score, infer an answer key, or invent SAP facts.",
        }
        request = urllib.request.Request(self.endpoint, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=8) as result:
            data = json.loads(result.read().decode())
        notes = data.get("notes", [])
        if not isinstance(notes, list) or any(not isinstance(note, str) for note in notes):
            raise ValueError("semantic provider returned invalid notes")
        return {"status": "advisory", "provider": "configured-http", "notes": notes[:5], "confidence": data.get("confidence", "uncertain"), "affectsScore": False, "uncertainty": "Provider feedback is advisory and requires deterministic or human validation."}


class GuardedSemanticAssessor(SemanticAssessor):
    def __init__(self, endpoint=None):
        configured = endpoint or os.getenv("ACADEMY_ASSESSMENT_SEMANTIC_ENDPOINT")
        self.provider = HttpAssessmentReview(configured) if configured else LocalAssessmentReview()

    def review(self, item, response):
        try:
            result = self.provider.review(item, response)
            result["affectsScore"] = False
            return result
        except Exception as exc:
            return {
                "status": "human-review-required",
                "provider": "guarded-fallback",
                "notes": ["Semantic provider unavailable; deterministic score remains unchanged."],
                "confidence": "unavailable",
                "affectsScore": False,
                "uncertainty": str(exc)[:200],
            }
