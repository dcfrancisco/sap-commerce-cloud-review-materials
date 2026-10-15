import hashlib
import json
import re
from pathlib import Path


class PracticeEngine:
    """Seeded exercise delivery with progressive hints and auditable deterministic grading."""

    PRIVATE_FIELDS = {"hints", "evaluation", "referenceSolution"}

    def __init__(self, store, root=None):
        self.store = store; root = Path(root or Path(__file__).resolve().parents[1])
        self.families = []
        for path in sorted((root / "content" / "operations" / "exercises").glob("*.json")):
            self.families.append(json.loads(path.read_text()))
        self.exercises = {exercise["id"]:(family,exercise) for family in self.families for exercise in family["exercises"]}

    def catalog(self):
        return [{"id":exercise["id"],"moduleId":exercise["moduleId"],"title":exercise["title"],"type":exercise["type"],"difficulty":exercise["difficulty"],"estimatedMinutes":exercise["estimatedMinutes"],"reviewStatus":exercise["reviewStatus"]} for _,exercise in self.exercises.values()]

    def _variant(self, family, exercise_id, seed):
        variant = {}
        for name, values in family["variantDimensions"].items():
            digest = hashlib.sha256(f"{family['id']}:{exercise_id}:{seed}:{name}".encode()).digest()
            options = list(values.values()) if isinstance(values, dict) else list(values)
            variant[name] = options[int.from_bytes(digest[:4], "big") % len(options)]
        signature = hashlib.sha256(json.dumps(variant, sort_keys=True).encode()).hexdigest()[:12]
        return {"signature":signature, **variant}

    def start(self, learner_id, exercise_id, seed="default"):
        entry = self.exercises.get(exercise_id)
        if not entry: return None
        family, exercise = entry; seed = str(seed)[:80] or "default"; variant = self._variant(family, exercise_id, seed)
        state = {"hintsUsed":[],"attempts":0,"status":"active"}
        session_id = self.store.create_practice_session(learner_id, exercise_id, exercise["version"], seed, variant, state)
        public = {key:value for key,value in exercise.items() if key not in self.PRIVATE_FIELDS}
        return {"sessionId":session_id,"familyId":family["id"],"exercise":public,"variant":variant,"hintCount":len(exercise["hints"]),"variantCountingPolicy":"Variants are replay aids and never count as additional published exercises or assessment items."}

    def hint(self, learner_id, session_id):
        session = self.store.practice_session(session_id, learner_id)
        if not session or session["status"] != "active": return {"error":"SESSION_NOT_ACTIVE"}
        _, exercise = self.exercises[session["exercise_id"]]; state = session["state"]; index = len(state["hintsUsed"])
        if index >= len(exercise["hints"]): return {"error":"NO_MORE_HINTS","hintsUsed":index}
        hint = exercise["hints"][index]; state["hintsUsed"].append(hint["level"])
        result = {"level":hint["level"],"hint":hint["text"],"hintsUsed":len(state["hintsUsed"]),"independentEvidenceEligible":False}
        self.store.update_practice(session_id,state,"hint",{},result); return result

    def submit(self, learner_id, session_id, response):
        session = self.store.practice_session(session_id, learner_id)
        if not session or session["status"] != "active": return {"error":"SESSION_NOT_ACTIVE"}
        _, exercise = self.exercises[session["exercise_id"]]; state = session["state"]; text = str(response); lowered = text.lower(); tokens = set(re.findall(r"[a-z0-9]+", lowered))
        evaluation = exercise["evaluation"]; groups = evaluation["conceptGroups"]
        covered = [group for group in groups if set(group) & tokens]; unsafe = [phrase for phrase in evaluation.get("hardFailPhrases",[]) if phrase in lowered]
        variant_terms = []
        for value in session["variant"].values():
            if isinstance(value, dict): variant_terms.extend(str(item).lower() for item in value.values())
            elif not isinstance(value, list): variant_terms.append(str(value).lower())
        variant_used = any(term in lowered for term in variant_terms if len(term) >= 2)
        evidence_terms = {"evidence","timeline","correlation","verify","validation","test","metric","log","record"}
        dimensions = {
            "criteriaCoverage":round(len(covered)/len(groups),2),
            "safety":0.0 if unsafe else 1.0,
            "variantReasoning":1.0 if variant_used else 0.0,
            "verificationEvidence":1.0 if evidence_terms & tokens else 0.0
        }
        weights = evaluation["weights"]; score = round(sum(dimensions[key]*weights[key] for key in dimensions),2)
        passed = score >= evaluation["passThreshold"] and not unsafe
        state["attempts"] += 1; state["status"] = "completed"
        result = {"sessionId":session_id,"exerciseId":exercise["id"],"score":score,"passed":passed,"dimensions":dimensions,"coveredConceptGroups":covered,"missingConceptGroups":[group for group in groups if group not in covered],"unsafeFindings":unsafe,"assisted":bool(state["hintsUsed"]),"independentEvidenceEligible":passed and not state["hintsUsed"],"feedback":"Retest without hints for independent mastery evidence." if passed and state["hintsUsed"] else ("Acceptance evidence satisfied." if passed else "Revise against the missing rubric groups and safety constraints."),"referenceSolution":exercise["referenceSolution"],"sourceIds":exercise["sourceIds"]}
        self.store.update_practice(session_id,state,"submission",{"response":text[:12000]},{key:value for key,value in result.items() if key != "referenceSolution"})
        self.store.complete_practice(session_id,exercise["competencyIds"],result); return result
