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
responsibilities = load("content/operations/responsibility-matrix.json")
dependencies = load("content/operations/module-dependencies.json")
publications = load("content/operations/publication-map.json")
gates = load("content/operations/release-gates.json")
coverage = load("content/operations/source-coverage.json")
scenario = load("content/operations/scenarios/ops-inc-001.json")
assessment = load("content/operations/assessments/ops-d03-m01.json")
sources = load("content/research/source-registry.json")
foundational_sources = load("content/sources.json")

domains = course.get("domains", []); modules = [module for domain in domains for module in domain.get("modules", [])]
module_ids = {module.get("id") for module in modules}; competency_ids = {item.get("id") for item in competencies.get("competencies", [])}; source_ids = {item.get("id") for item in sources.get("sources", []) + foundational_sources.get("sources", [])}
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

manual_path = ROOT / "content/operations/modules/ops-d03-m01-failed-deployment.md"
manual = manual_path.read_text() if manual_path.exists() else ""
if len(manual.split()) < 2500: errors.append(f"reference manual too short: {len(manual.split())} words")
for section in ("Learning outcomes","Schema compatibility","Guided simulation","Security and privacy","Tutor behavior","References"):
    if section.lower() not in manual.lower(): errors.append(f"manual missing {section}")
for source_id in set(re.findall(r"\[(RS-[A-Z0-9-]+)\]", manual)):
    if source_id not in source_ids: errors.append(f"manual unknown source {source_id}")

if scenario.get("schemaVersion") != "operations-scenario.v1": errors.append("invalid scenario schema")
if len(scenario.get("investigations", [])) < 6 or len(scenario.get("actions", [])) < 6: errors.append("scenario lacks investigative/action depth")
action_ids = {item.get("id") for item in scenario.get("actions", [])}; investigation_ids = {item.get("id") for item in scenario.get("investigations", [])}
all_action_ids = action_ids | investigation_ids
for item in scenario.get("actions", []) + scenario.get("investigations", []):
    for requirement in item.get("requires", []):
        if requirement not in all_action_ids: errors.append(f"{item.get('id')}: unknown prerequisite {requirement}")
if not any(not item.get("permitted", True) for item in scenario.get("actions", [])): errors.append("scenario has no prohibited action")
for competency_id in scenario.get("competencyIds", []):
    if competency_id not in competency_ids: errors.append(f"scenario unknown competency {competency_id}")
for source_id in scenario.get("sourceIds", []):
    if source_id not in source_ids: errors.append(f"scenario unknown source {source_id}")

items = assessment.get("items", []); prompts = set(); item_ids = set()
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
if len(items) != 10: errors.append(f"expected 10 reference items, found {len(items)}")

gate_statuses = {gate.get("status") for gate in gates.get("gates", [])}
if gates.get("commercialReleaseEligible") is not False or "fail" not in gate_statuses: errors.append("alpha release gates must not imply commercial eligibility")
if gates.get("humanReviews", {}).get("sapTechnical") != "pending": errors.append("human SAP review must remain pending")

print(f"operations curriculum: {len(domains)} domains, {len(modules)} modules; implemented-review-required={sum(m.get('status') == 'implemented-review-required' for m in modules)}, complete={sum(m.get('status') == 'complete' for m in modules)}")
print(f"operations assets: roles={len(roles.get('roles', []))}, competencies={len(competency_ids)}, scenarios=1, assessment-items={len(items)}, publications-planned={len(publications.get('volumes', []))}")
print("commercial gates: " + ", ".join(f"{gate['id']}={gate['status']}" for gate in gates.get("gates", [])))
if errors:
    print("OPERATIONS QA FAILED\n" + "\n".join(f"- {error}" for error in errors)); sys.exit(1)
print("OPERATIONS QA PASSED: structure, mappings, scenario consistency, source traceability, assessment fields, and no-false-completion gates validated")
