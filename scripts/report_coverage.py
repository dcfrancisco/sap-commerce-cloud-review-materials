import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
load = lambda path: json.loads((ROOT / path).read_text())

general_course = load("content/course.json")
operations_course = load("content/operations/course.json")
operations_modules = [module for domain in operations_course["domains"] for module in domain["modules"]]
exercise_files = sorted((ROOT / "content/operations/exercises").glob("*.json"))
exercises = [exercise for path in exercise_files for exercise in json.loads(path.read_text())["exercises"]]
operations_items = load("content/operations/assessments/ops-d03-m01.json")["items"]
general_items = [item for path in sorted((ROOT / "content/assessments").glob("module-*.json")) for item in json.loads(path.read_text())["items"]]
sources = load("content/sources.json")["sources"] + load("content/research/source-registry.json")["sources"]
scenario_files = sorted((ROOT / "content/operations/scenarios").glob("*.json"))
operations_scenarios = [json.loads(path.read_text()) for path in scenario_files]
manual_sources = sorted((ROOT / "content/modules").glob("*.md")) + sorted((ROOT / "content/operations/modules").glob("*.md"))
machine_validated_pdfs = sum((ROOT / "dist" / f"{path.stem}.pdf").exists() for path in manual_sources)

report = {
    "measurementPolicy":"Counts are derived from canonical source metadata. Seeded variants are excluded from asset totals. Machine validation is not human technical or editorial review.",
    "curriculum":{"generalDeclaredModules":len(general_course["modules"]),"operationsDeclaredModules":len(operations_modules),"authoredReviewRequiredModules":sum(module["status"] == "implemented-review-required" for module in general_course["modules"] + operations_modules),"completedModules":sum(module["status"] == "complete" for module in general_course["modules"] + operations_modules),"completedLessons":0},
    "examples":{"technicallyHumanReviewed":0,"executableDeterministicScenarios":len(operations_scenarios)},
    "exercises":{"authored":len(exercises),"machineValidated":sum(exercise["reviewStatus"] == "implemented-machine-validated" for exercise in exercises),"humanReviewed":sum(exercise["reviewStatus"] in {"human-reviewed","published"} for exercise in exercises),"seededVariantsCountedAsAssets":0},
    "assessments":{"generalValidated":sum(item.get("reviewStatus") == "validated" for item in general_items),"operationsInternallyValidated":sum(item.get("reviewStatus") == "validated-internal" for item in operations_items),"operationsPublished":sum(item.get("reviewStatus") == "published" for item in operations_items)},
    "scenarios":{"implementedMachineValidated":sum(item.get("reviewStatus") == "implemented-machine-validated" for item in operations_scenarios),"humanReviewed":sum(item.get("reviewStatus") in {"human-reviewed","published"} for item in operations_scenarios)},
    "publications":{"modulePdfsMachineValidated":machine_validated_pdfs,"commerciallyValidatedBooks":0},
    "platformVersions":{"declaredSupported":["SAP Commerce Cloud public cloud 2211"],"liveRuntimeVerified":[]},
    "sources":{"registered":len({source["id"] for source in sources}),"officialAuthoritativeExpanded":sum(source.get("authorityTier") == "official-authoritative" for source in sources)}
}
print(json.dumps(report, indent=2))
