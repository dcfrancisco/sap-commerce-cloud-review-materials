import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []

def read_json(path):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        errors.append(f"{path}: invalid JSON: {exc}")
        return {}

course = read_json(ROOT / "content/course.json")
sources = read_json(ROOT / "content/sources.json")
competencies = read_json(ROOT / "content/competencies.json")
items_doc = read_json(ROOT / "content/assessments/module-01.json")
source_ids = {x.get("id") for x in sources.get("sources", [])}
competency_ids = {x.get("id") for x in competencies.get("competencies", [])}
ids, prompts, counts = set(), set(), {}
required = ["id","moduleId","competencyIds","type","difficulty","cognitiveSkill","prompt","answer","explanation","sourceIds","estimatedMinutes","prerequisites","tags","rubric","reviewStatus","version"]
for item in items_doc.get("items", []):
    missing = [key for key in required if key not in item]
    if missing: errors.append(f"{item.get('id', '<unknown>')}: missing {missing}")
    if item.get("id") in ids: errors.append(f"duplicate id: {item.get('id')}")
    if item.get("prompt") in prompts: errors.append(f"duplicate prompt: {item.get('id')}")
    ids.add(item.get("id")); prompts.add(item.get("prompt"))
    for cid in item.get("competencyIds", []):
        if cid not in competency_ids: errors.append(f"{item.get('id')}: unknown competency {cid}")
    for sid in item.get("sourceIds", []):
        if sid not in source_ids: errors.append(f"{item.get('id')}: unknown source {sid}")
    if item.get("reviewStatus") == "validated": counts[item.get("type")] = counts.get(item.get("type"), 0) + 1
module_text = (ROOT / "content/modules/01-architecture-fundamentals.md").read_text()
for section in ["Learning outcomes", "Guided practice", "Independent practice", "Diagnostic walkthrough", "References"]:
    if section.lower() not in module_text.lower(): errors.append(f"module missing section: {section}")
if len(module_text) < 5000: errors.append("module is too short for substantive content")
print(f"course modules: {len(course.get('modules', []))} (complete: {sum(x.get('status') == 'complete' for x in course.get('modules', []))})")
print(f"assessment items: {len(items_doc.get('items', []))} total; {sum(counts.values())} validated")
print("validated item types: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
print(f"source records: {len(sources.get('sources', []))}; verified={sum(x.get('status') == 'verified' for x in sources.get('sources', []))}; research-gap={sum(x.get('status') == 'research-gap' for x in sources.get('sources', []))}")
if errors:
    print("QA FAILED\n" + "\n".join(f"- {error}" for error in errors)); sys.exit(1)
print("QA PASSED: required fields, mappings, duplicate prompts, sources, and module depth checks passed")
