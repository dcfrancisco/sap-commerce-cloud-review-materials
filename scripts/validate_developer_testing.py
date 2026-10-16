import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []


def load(relative):
    try:
        return json.loads((ROOT / relative).read_text())
    except Exception as exc:
        errors.append(f"{relative}: {exc}")
        return {}


family = load("content/exercises/developer-testing-m02-m05.json")
schema = load("content/schemas/developer-exercise-family.schema.json")
competencies = load("content/competencies.json")
sources = load("content/sources.json").get("sources", []) + load("content/research/source-registry.json").get("sources", [])
competency_ids = {item.get("id") for item in competencies.get("competencies", [])}
source_ids = {item.get("id") for item in sources}
test_competencies = {item.get("id") for item in competencies.get("competencies", []) if item.get("id", "").startswith("C-TEST-")}
exercises = family.get("exercises", [])

if family.get("schemaVersion") != "developer-exercise-family.v1": errors.append("invalid developer exercise family schema version")
if schema.get("$id") != "academy://schemas/developer-exercise-family.v1": errors.append("missing developer exercise JSON schema")
if set(item.get("moduleId") for item in exercises) != {"M02", "M03", "M04", "M05"}: errors.append("M02-M05 must each have a testing exercise")
if len(test_competencies) != 4: errors.append(f"expected four independent testing competencies, found {len(test_competencies)}")

exercise_ids = set()
for exercise in exercises:
    exercise_id = exercise.get("id")
    if exercise_id in exercise_ids: errors.append(f"duplicate exercise {exercise_id}")
    exercise_ids.add(exercise_id)
    if not set(exercise.get("competencyIds", [])) & test_competencies: errors.append(f"{exercise_id}: no independent testing competency")
    if not any(not item.startswith("C-TEST-") for item in exercise.get("competencyIds", [])): errors.append(f"{exercise_id}: no implementation competency")
    for competency_id in exercise.get("competencyIds", []):
        if competency_id not in competency_ids: errors.append(f"{exercise_id}: unknown competency {competency_id}")
    for source_id in exercise.get("sourceIds", []):
        if source_id not in source_ids: errors.append(f"{exercise_id}: unknown source {source_id}")
    evaluation = exercise.get("evaluation", {})
    if evaluation.get("mode") != "dual-competency": errors.append(f"{exercise_id}: missing dual competency evaluation")
    if evaluation.get("untestedImplementationScoreCap", 1) >= 0.8: errors.append(f"{exercise_id}: implementation mastery is not capped below pass threshold")
    mapping = evaluation.get("competencyEvidenceMap", {})
    if set(mapping.get("implementation", []) + mapping.get("testing", [])) != set(exercise.get("competencyIds", [])): errors.append(f"{exercise_id}: competency evidence mapping drift")
    if len(evaluation.get("testingConceptGroups", [])) < 5 or len(evaluation.get("negativePathGroups", [])) < 2: errors.append(f"{exercise_id}: insufficient test and negative-path depth")
    if len(exercise.get("acceptanceCriteria", [])) < 5 or len(exercise.get("hints", [])) < 2: errors.append(f"{exercise_id}: insufficient instructional depth")
    boundary = exercise.get("executionBoundary", "").lower()
    if "sap commerce" not in boundary or not any(term in boundary for term in ("not run", "does not execute", "require")): errors.append(f"{exercise_id}: unclear platform execution boundary")
    if exercise.get("reviewStatus") == "published": errors.append(f"{exercise_id}: cannot be published without recorded human review")

for module_id in ("M02", "M03", "M04", "M05"):
    path = next((ROOT / "content" / "modules").glob(f"{module_id[1:]}-*.md"), None)
    text = path.read_text().lower() if path else ""
    for required in ("unit test", "integration test", "negative", "execution evidence"):
        if required not in text: errors.append(f"{module_id}: manual missing {required} coverage")

print(f"developer testing competencies: {len(test_competencies)}")
print(f"developer testing exercises: {len(exercises)} across {len({item.get('moduleId') for item in exercises})} modules")
if errors:
    print("DEVELOPER TESTING QA FAILED\n" + "\n".join(f"- {error}" for error in errors)); sys.exit(1)
print("DEVELOPER TESTING QA PASSED: independent competencies, mastery cap, negative paths, runtime boundaries, mappings, and module coverage validated")
