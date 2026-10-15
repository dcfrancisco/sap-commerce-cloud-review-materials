import os
import re
from pathlib import Path


class GroundedTutor:
    """Provider-neutral tutor MVP with a deterministic local adapter.

    A remote provider can be added behind the same interface, but the local adapter
    never invents an answer: it returns matching source-backed excerpts or abstains.
    """

    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parents[1])
        self.provider = os.getenv("ACADEMY_TUTOR_PROVIDER", "local")

    def answer(self, question, module_id="M01"):
        prefix = module_id.lower().replace("m", "", 1).zfill(2)
        module_path = next(self.root.glob(f"content/modules/{prefix}-*.md"), None)
        if not module_path:
            return {"answer":"I do not have a grounded lesson for this module.","citations":[],"confidence":"unknown","abstainReason":"module content unavailable"}
        terms = set(re.findall(r"[a-z0-9]{4,}", question.lower()))
        paragraphs = module_path.read_text().split("\n\n")
        ranked = []
        for paragraph in paragraphs:
            base_score = len(terms & set(re.findall(r"[a-z0-9]{4,}", paragraph.lower())))
            ranked.append((base_score + (3 if base_score and "[SAP-" in paragraph else 0), paragraph))
        ranked.sort(reverse=True)
        matches = [p for score, p in ranked if score >= 2][:2]
        if not matches:
            return {"answer":"I cannot answer this reliably from the published lesson. Please provide a narrower question or consult the cited SAP documentation.","citations":[],"confidence":"unknown","abstainReason":"no matching grounded passage"}
        citations = sorted(set(re.findall(r"SAP-[A-Z0-9-]+", " ".join(matches))))
        citations.append("lesson:" + module_id)
        return {"answer":"Based on the published lesson:\n\n" + "\n\n".join(matches),"citations":citations,"confidence":"grounded-excerpt","provider":self.provider,"uncertainty":"The excerpt may combine SAP-specific facts and explicitly labeled engineering interpretation; check the cited source records before treating it as a platform requirement."}
