import json
import re
from pathlib import Path


class IncidentTutor:
    """Deterministic staged-incident tutor; evidence and grading remain auditable."""

    CONCEPTS = {
        "LAB-M25-STOREFRONT-STALE-PRICE": [
            {"occ", "fresh", "response"}, {"ssr", "cache", "stale"},
            {"site", "currency", "context"}, {"verify", "hydration", "navigation"}
        ],
        "LAB-M26-SYNC-STALE": [
            {"synchronization", "success"}, {"index", "solr", "failed"},
            {"preserve", "evidence"}, {"verify", "search", "detail"}
        ],
        "LAB-M27-FAILED-DEPLOYMENT": [
            {"timeline", "build", "deployment"}, {"schema", "migration", "compatibility"},
            {"backup", "restore", "redeploy"}, {"acceptance", "reconcile", "verify"}
        ]
    }
    UNSAFE = {"initialize production", "delete database", "clear every cache", "ignore backup", "force commit"}

    def __init__(self, root=None):
        root = Path(root or Path(__file__).resolve().parents[1])
        docs = json.loads((root / "content/labs/ecosystem-vertical-slices.json").read_text())
        self.labs = {lab["id"]: lab for lab in docs["labs"]}

    def start(self, lab_id):
        lab = self.labs.get(lab_id)
        if not lab: return None
        return {"labId":lab_id,"title":lab["title"],"simulationLabel":lab["simulationLabel"],"initialSituation":lab["initialSituation"],"objectives":lab["objectives"],"constraints":lab["constraints"],"availableEvidence":lab["evidenceStages"][0],"nextStage":2}

    def catalog(self):
        return [{"id": lab["id"], "moduleId": lab["moduleId"], "title": lab["title"], "simulationLabel": lab["simulationLabel"]} for lab in self.labs.values()]

    def evidence(self, lab_id, stage):
        lab = self.labs.get(lab_id)
        if not lab: return None
        item = next((x for x in lab["evidenceStages"] if x["stage"] == stage), None)
        return {"labId":lab_id,"evidence":item,"nextStage":stage + 1 if item and stage < len(lab["evidenceStages"]) else None}

    def grade(self, lab_id, response):
        lab = self.labs.get(lab_id)
        if not lab: return None
        text = str(response).lower(); tokens = set(re.findall(r"[a-z0-9]+", text))
        groups = self.CONCEPTS[lab_id]
        covered = [sorted(group) for group in groups if len(group & tokens) >= 1]
        unsafe = sorted(phrase for phrase in self.UNSAFE if phrase in text)
        evidence_score = len(covered) / len(groups)
        safety_score = 0.0 if unsafe else 1.0
        score = round(evidence_score * 0.75 + safety_score * 0.25, 2)
        return {"labId":lab_id,"score":score,"passed":score >= 0.8,"coveredConceptGroups":covered,"missingConceptGroups":[sorted(group) for group in groups if sorted(group) not in covered],"unsafeActions":unsafe,"rubric":lab["rubric"],"referenceRootCause":lab["rootCause"] if score >= 0.8 else None,"feedback":"Proceed to root-cause and prevention review." if score >= 0.8 else "Use the disclosed evidence to identify the failing boundary, safe recovery, and independent verification. Avoid unsupported or destructive actions."}
