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
        paths = list((root / "content" / "operations" / "exercises").glob("*.json")) + list((root / "content" / "exercises").glob("*.json"))
        for path in sorted(paths):
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
        evaluation = exercise["evaluation"]
        if evaluation.get("mode") == "dual-competency":
            return self._submit_dual_competency(session, exercise, state, text, lowered, tokens)
        groups = evaluation["conceptGroups"]
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

    def _submit_dual_competency(self, session, exercise, state, text, lowered, tokens):
        evaluation = exercise["evaluation"]
        implementation_groups = evaluation["implementationConceptGroups"]
        testing_groups = evaluation["testingConceptGroups"]
        implementation_covered = [group for group in implementation_groups if set(group) & tokens]
        testing_covered = [group for group in testing_groups if set(group) & tokens]
        unsafe = [phrase for phrase in evaluation.get("hardFailPhrases", []) if phrase in lowered]
        negative_path = all(set(group) & tokens for group in evaluation["negativePathGroups"])
        execution_evidence = all(set(group) & tokens for group in evaluation["executionEvidenceGroups"])
        implementation_score = round(len(implementation_covered) / len(implementation_groups), 2)
        testing_coverage = round(len(testing_covered) / len(testing_groups), 2)
        testing_score = round(testing_coverage * 0.6 + (0.2 if negative_path else 0.0) + (0.2 if execution_evidence else 0.0), 2)
        implementation_passed = implementation_score >= evaluation["implementationThreshold"]
        testing_passed = testing_score >= evaluation["testingThreshold"]
        score = round(implementation_score * 0.5 + testing_score * 0.5, 2)
        mastery_cap_applied = implementation_passed and not testing_passed
        if mastery_cap_applied: score = min(score, evaluation["untestedImplementationScoreCap"])
        passed = implementation_passed and testing_passed and not unsafe
        competency_scores = {}
        for competency_id in evaluation["competencyEvidenceMap"]["implementation"]: competency_scores[competency_id] = implementation_score
        for competency_id in evaluation["competencyEvidenceMap"]["testing"]: competency_scores[competency_id] = testing_score
        state["attempts"] += 1; state["status"] = "completed"
        result = {
            "sessionId":session["id"],"exerciseId":exercise["id"],"score":score,"passed":passed,
            "implementation":{"score":implementation_score,"passed":implementation_passed,"coveredConceptGroups":implementation_covered,"missingConceptGroups":[group for group in implementation_groups if group not in implementation_covered]},
            "testing":{"score":testing_score,"passed":testing_passed,"coveredConceptGroups":testing_covered,"missingConceptGroups":[group for group in testing_groups if group not in testing_covered],"negativePathEvidence":negative_path,"executionEvidence":execution_evidence},
            "masteryCapApplied":mastery_cap_applied,"unsafeFindings":unsafe,"competencyScores":competency_scores,
            "assisted":bool(state["hintsUsed"]),"independentEvidenceEligible":passed and not state["hintsUsed"],
            "feedback":"Implementation mastery is capped until independent testing evidence passes." if mastery_cap_applied else ("Implementation and testing evidence satisfied." if passed else "Revise the implementation diagnosis and the independent test evidence."),
            "referenceSolution":exercise["referenceSolution"],"sourceIds":exercise["sourceIds"],"executionBoundary":exercise["executionBoundary"]
        }
        self.store.update_practice(session["id"],state,"submission",{"response":text[:12000]},{key:value for key,value in result.items() if key != "referenceSolution"})
        self.store.complete_practice(session["id"],exercise["competencyIds"],result); return result
