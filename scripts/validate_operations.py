import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []

def load(relative):
    path = ROOT / relative
    try: return json.loads(path.read_text())
    except Exception as exc: errors.append(f"{relative}: {exc}"); return {}

course = load("content/operations/course.json")
roles = load("content/operations/role-paths.json")
competencies = load("content/operations/competencies.json")
general_competencies = load("content/competencies.json")
general_roles = load("content/research/role-coverage-matrix.json")
product_matrix = load("content/research/product-version-matrix.json")
responsibilities = load("content/operations/responsibility-matrix.json")
dependencies = load("content/operations/module-dependencies.json")
publications = load("content/operations/publication-map.json")
gates = load("content/operations/release-gates.json")
coverage = load("content/operations/source-coverage.json")
scenarios = [load(str(path.relative_to(ROOT))) for path in sorted((ROOT / "content/operations/scenarios").glob("*.json"))]
assessment_files = sorted((ROOT / "content/operations/assessments").glob("*.json"))
assessments = [load(str(path.relative_to(ROOT))) for path in assessment_files]
exercise_families = [load(str(path.relative_to(ROOT))) for path in sorted((ROOT / "content/operations/exercises").glob("*.json"))]
sources = load("content/research/source-registry.json")
foundational_sources = load("content/sources.json")
exercise_schema = load("content/schemas/operations-exercise-family.schema.json")
reasoning_schema = load("content/schemas/incident-reasoning.schema.json")

domains = course.get("domains", []); modules = [module for domain in domains for module in domain.get("modules", [])]
module_ids = {module.get("id") for module in modules}; competency_ids = {item.get("id") for item in competencies.get("competencies", [])}; all_competency_ids = competency_ids | {item.get("id") for item in general_competencies.get("competencies", [])}; source_ids = {item.get("id") for item in sources.get("sources", []) + foundational_sources.get("sources", [])}
known_roles = {item.get("id") for item in roles.get("roles", [])} | {item.get("role") for item in general_roles.get("roles", [])}
known_products = {item.get("id") for item in product_matrix.get("products", [])}
if len(domains) != 12: errors.append(f"expected 12 domains, found {len(domains)}")
if len(modules) != 60: errors.append(f"expected 60 modules, found {len(modules)}")
if len(module_ids) != len(modules): errors.append("duplicate operations module IDs")
if len(roles.get("roles", [])) != 9: errors.append("expected nine role paths")
if len(publications.get("volumes", [])) != 12: errors.append("expected twelve publication volumes")
if len(responsibilities.get("categories", [])) != 7: errors.append("responsibility model must have seven categories")
for edge in dependencies.get("edges", []):
    if edge.get("from") not in module_ids or edge.get("to") not in module_ids: errors.append(f"invalid dependency edge {edge}")
for role in roles.get("roles", []):
    for domain_id in role.get("requiredDomains", []):
        if domain_id not in {domain.get("id") for domain in domains}: errors.append(f"{role.get('id')}: unknown domain {domain_id}")
covered_module_ids = []
for entry in coverage.get("domains", []):
    covered_module_ids.extend(entry.get("moduleIds", []))
    if not entry.get("gaps"): errors.append(f"{entry.get('domainId')}: source gaps must be explicit")
    for source_id in entry.get("sourceIds", []):
        if source_id not in source_ids: errors.append(f"{entry.get('domainId')}: unknown source {source_id}")
if set(covered_module_ids) != module_ids or len(covered_module_ids) != len(module_ids): errors.append("source coverage must map every module exactly once")
for competency in competencies.get("competencies", []):
    if not competency.get("evidence") or not competency.get("mastery"): errors.append(f"{competency.get('id')}: incomplete mastery evidence")

implemented_modules = [module for module in modules if module.get("status") == "implemented-review-required"]
for module in implemented_modules:
    manual_path = ROOT / module.get("manual", "")
    manual = manual_path.read_text() if manual_path.is_file() else ""
    if len(manual.split()) < 2500: errors.append(f"{module.get('id')}: reference manual too short: {len(manual.split())} words")
    for section in ("Learning outcomes","Security and privacy","Tutor behavior","References"):
        if section.lower() not in manual.lower(): errors.append(f"{module.get('id')}: manual missing {section}")
    for source_id in set(re.findall(r"\[(RS-[A-Z0-9-]+)\]", manual)):
        if source_id not in source_ids: errors.append(f"{module.get('id')}: manual unknown source {source_id}")

scenario_ids = set()
for scenario in scenarios:
    scenario_id = scenario.get("id")
    if scenario_id in scenario_ids: errors.append(f"duplicate scenario {scenario_id}")
    scenario_ids.add(scenario_id)
    if scenario.get("schemaVersion") != "operations-scenario.v1": errors.append(f"{scenario_id}: invalid scenario schema")
    if len(scenario.get("investigations", [])) < 6 or len(scenario.get("actions", [])) < 6: errors.append(f"{scenario_id}: lacks investigative/action depth")
    if not scenario.get("roles") or not scenario.get("products") or not scenario.get("topics") or not scenario.get("discoveryTerms"): errors.append(f"{scenario_id}: incomplete discovery metadata")
    for role_id in scenario.get("roles", []):
        if role_id not in known_roles: errors.append(f"{scenario_id}: unknown role {role_id}")
    for product_id in scenario.get("products", []):
        if product_id not in known_products: errors.append(f"{scenario_id}: unknown product {product_id}")
    action_ids = {item.get("id") for item in scenario.get("actions", [])}; investigation_ids = {item.get("id") for item in scenario.get("investigations", [])}
    all_action_ids = action_ids | investigation_ids
    for item in scenario.get("actions", []) + scenario.get("investigations", []):
        for requirement in item.get("requires", []):
            if requirement not in all_action_ids: errors.append(f"{scenario_id}/{item.get('id')}: unknown prerequisite {requirement}")
    if not any(not item.get("permitted", True) for item in scenario.get("actions", [])): errors.append(f"{scenario_id}: has no prohibited action")
    scoring = scenario.get("scoring", {})
    if scoring.get("preferredRecovery") not in action_ids or scoring.get("verificationAction") not in action_ids: errors.append(f"{scenario_id}: invalid recovery or verification action")
    if not scoring.get("integrityEvidence") or not set(scoring.get("integrityEvidence", [])) <= investigation_ids: errors.append(f"{scenario_id}: invalid integrity evidence")
    tutor = scenario.get("tutor", {})
    if len(tutor.get("sequence", [])) < 5 or not tutor.get("citations") or not tutor.get("uncertainty"): errors.append(f"{scenario_id}: incomplete grounded tutor sequence")
    for prompt in tutor.get("sequence", []):
        if prompt.get("until") not in all_action_ids: errors.append(f"{scenario_id}: tutor references unknown step {prompt.get('until')}")
    for competency_id in scenario.get("competencyIds", []):
        if competency_id not in all_competency_ids: errors.append(f"{scenario_id}: unknown competency {competency_id}")
    for source_id in scenario.get("sourceIds", []):
        if source_id not in source_ids: errors.append(f"{scenario_id}: unknown source {source_id}")
    if scenario.get("assessmentMode") == "structured-reasoning":
        model = scenario.get("reasoningModel", {})
        for field in ("preferredPrimary", "containmentAction", "verificationAction", "acceptedRecoveryActions", "minimumSupportingEvidence", "minimumRejectedAlternatives", "minimumVerificationChecks", "minimumPreventionControls"):
            if field not in model: errors.append(f"{scenario_id}: structured reasoning model missing {field}")
        action_ids = {item.get("id") for item in scenario.get("actions", [])}
        if model.get("containmentAction") not in action_ids or model.get("verificationAction") not in action_ids: errors.append(f"{scenario_id}: reasoning model action mapping invalid")
        if not set(model.get("acceptedRecoveryActions", [])) <= action_ids: errors.append(f"{scenario_id}: reasoning recovery mapping invalid")

items = [item for assessment in assessments for item in assessment.get("items", [])]; prompts = set(); item_ids = set()
required_fields = {"id","moduleId","competencyIds","type","difficulty","scenario","prompt","answer","explanation","rubric","applicableVersion","sourceIds","evaluationEvidence","reviewStatus","version"}
for item in items:
    missing = required_fields - set(item)
    if missing: errors.append(f"{item.get('id')}: missing {sorted(missing)}")
    if item.get("id") in item_ids: errors.append(f"duplicate item {item.get('id')}")
    if item.get("prompt") in prompts: errors.append(f"duplicate prompt {item.get('id')}")
    item_ids.add(item.get("id")); prompts.add(item.get("prompt"))
    if item.get("moduleId") not in module_ids: errors.append(f"{item.get('id')}: unknown module")
    for competency_id in item.get("competencyIds", []):
        if competency_id not in competency_ids: errors.append(f"{item.get('id')}: unknown competency {competency_id}")
    for source_id in item.get("sourceIds", []):
        if source_id not in source_ids: errors.append(f"{item.get('id')}: unknown source {source_id}")
for module in implemented_modules:
    if sum(item.get("moduleId") == module.get("id") for item in items) < 5: errors.append(f"{module.get('id')}: fewer than five substantive assessment items")

exercise_ids = set(); exercise_prompts = []; exercises = []
exercise_required = {"id","moduleId","version","title","type","difficulty","estimatedMinutes","competencyIds","objective","initialState","prompt","constraints","deliverable","acceptanceCriteria","hints","evaluation","referenceSolution","sourceIds","reviewStatus"}
for family in exercise_families:
    if family.get("schemaVersion") != "operations-exercise-family.v1": errors.append(f"{family.get('id')}: invalid exercise-family schema")
    if len(family.get("variantDimensions", {})) < 2: errors.append(f"{family.get('id')}: insufficient variant dimensions")
    if "not independent published assets" not in family.get("variantPolicy", ""): errors.append(f"{family.get('id')}: variant counting policy missing")
    for exercise in family.get("exercises", []):
        exercises.append(exercise); missing = exercise_required - set(exercise)
        if missing: errors.append(f"{exercise.get('id')}: missing {sorted(missing)}")
        if exercise.get("id") in exercise_ids: errors.append(f"duplicate exercise {exercise.get('id')}")
        exercise_ids.add(exercise.get("id")); exercise_prompts.append((exercise.get("id"), set(re.findall(r"[a-z0-9]+", exercise.get("prompt", "").lower()))))
        if exercise.get("moduleId") not in module_ids: errors.append(f"{exercise.get('id')}: unknown module")
        if len(exercise.get("acceptanceCriteria", [])) < 4 or len(exercise.get("hints", [])) < 2: errors.append(f"{exercise.get('id')}: exercise depth insufficient")
        if exercise.get("reviewStatus") == "published": errors.append(f"{exercise.get('id')}: cannot be published without recorded human review")
        for competency_id in exercise.get("competencyIds", []):
            if competency_id not in competency_ids: errors.append(f"{exercise.get('id')}: unknown competency {competency_id}")
        for source_id in exercise.get("sourceIds", []):
            if source_id not in source_ids: errors.append(f"{exercise.get('id')}: unknown source {source_id}")
for index,(left_id,left) in enumerate(exercise_prompts):
    for right_id,right in exercise_prompts[index+1:]:
        similarity = len(left & right) / max(1, len(left | right))
        if similarity >= 0.8: errors.append(f"near-duplicate exercise prompts: {left_id}, {right_id} ({similarity:.2f})")
if exercise_schema.get("$id") != "academy://schemas/operations-exercise-family.v1": errors.append("exercise-family JSON schema missing or invalid")
if reasoning_schema.get("$id") != "academy://schemas/incident-reasoning.v1": errors.append("incident-reasoning JSON schema missing or invalid")
if course.get("actual", {}).get("machineValidatedExercises") != len([item for item in exercises if item.get("reviewStatus") == "implemented-machine-validated"]): errors.append("course actual exercise count drift")

gate_statuses = {gate.get("status") for gate in gates.get("gates", [])}
if gates.get("commercialReleaseEligible") is not False or "fail" not in gate_statuses: errors.append("alpha release gates must not imply commercial eligibility")
if gates.get("humanReviews", {}).get("sapTechnical") != "pending": errors.append("human SAP review must remain pending")

print(f"operations curriculum: {len(domains)} domains, {len(modules)} modules; implemented-review-required={sum(m.get('status') == 'implemented-review-required' for m in modules)}, complete={sum(m.get('status') == 'complete' for m in modules)}")
print(f"operations assets: roles={len(roles.get('roles', []))}, competencies={len(competency_ids)}, scenarios={len(scenarios)}, exercises={len(exercises)}, assessment-items={len(items)}, publications-planned={len(publications.get('volumes', []))}")
print("commercial gates: " + ", ".join(f"{gate['id']}={gate['status']}" for gate in gates.get("gates", [])))
if errors:
    print("OPERATIONS QA FAILED\n" + "\n".join(f"- {error}" for error in errors)); sys.exit(1)
print("OPERATIONS QA PASSED: structure, mappings, scenario consistency, source traceability, assessment fields, and no-false-completion gates validated")
