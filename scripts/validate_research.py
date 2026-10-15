import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []

def load(path):
    try: return json.loads(path.read_text())
    except Exception as exc: errors.append(f"{path}: {exc}"); return {}

legacy = load(ROOT / "content/sources.json").get("sources", [])
registry = load(ROOT / "content/research/source-registry.json")
governance = load(ROOT / "content/research/source-governance.json")
coverage = load(ROOT / "content/research/coverage-matrix.json")
contradictions = load(ROOT / "content/research/contradictions.json")
products = load(ROOT / "content/research/product-version-matrix.json")
roles = load(ROOT / "content/research/role-coverage-matrix.json")
publications = load(ROOT / "content/research/publication-plan.json")
course = load(ROOT / "content/course.json")
required = governance.get("requiredFields", [])
for source in registry.get("sources", []):
    missing = [field for field in required if field not in source or source[field] in (None, "", [])]
    if missing: errors.append(f"{source.get('id','<unknown>')}: missing research fields {missing}")
all_sources = {source["id"]: source for source in legacy + registry.get("sources", [])}
if len(all_sources) != len(legacy) + len(registry.get("sources", [])): errors.append("duplicate source IDs across registries")
course_ids = {module["id"] for module in course.get("modules", [])}
matrix = {module["moduleId"]: module for module in coverage.get("modules", [])}
if set(matrix) != course_ids: errors.append(f"coverage mismatch missing={sorted(course_ids-set(matrix))} extra={sorted(set(matrix)-course_ids)}")
for module in coverage.get("modules", []):
    for source_id in module.get("official", []) + module.get("supplementary", []):
        if source_id not in all_sources: errors.append(f"{module['moduleId']}: unknown source {source_id}")
    if not module.get("gaps"): errors.append(f"{module['moduleId']}: research gaps must be explicit")
for module in [item for item in course.get("modules", []) if item.get("status") != "planned"]:
    entry = matrix.get(module["id"], {})
    verified_official = 0
    for source_id in entry.get("official", []):
        source = all_sources.get(source_id, {})
        if source.get("status") == "verified" or (str(source.get("authorityTier", "")).startswith("official") and "failed" not in source.get("verificationStatus", "")):
            verified_official += 1
    if verified_official < 3: errors.append(f"{module['id']}: fewer than 3 applicable official references")
for item in contradictions.get("items", []):
    if not item.get("resolution") or not item.get("status"): errors.append(f"{item.get('id')}: unresolved contradiction record incomplete")
    for claim in item.get("claims", []):
        if claim.get("sourceId") not in all_sources: errors.append(f"{item.get('id')}: unknown claim source {claim.get('sourceId')}")
for product in products.get("products", []):
    for source_id in product.get("documentation", []):
        if source_id not in all_sources: errors.append(f"product {product.get('id')}: unknown source {source_id}")
    for module_id in product.get("trainingModules", []):
        if module_id not in course_ids: errors.append(f"product {product.get('id')}: unknown module {module_id}")
role_names = set()
for role in roles.get("roles", []):
    if role.get("role") in role_names: errors.append(f"duplicate role {role.get('role')}")
    role_names.add(role.get("role"))
    for module_id in role.get("modules", []):
        if module_id not in course_ids: errors.append(f"role {role.get('role')}: unknown module {module_id}")
for volume in publications.get("volumes", []):
    for module_id in volume.get("sourceModules", []):
        if module_id not in course_ids: errors.append(f"publication {volume.get('id')}: unknown module {module_id}")
tiers = {}
for source in registry.get("sources", []): tiers[source["authorityTier"]] = tiers.get(source["authorityTier"], 0) + 1
print(f"research sources: {len(registry.get('sources', []))} expanded + {len(legacy)} foundational = {len(all_sources)} total")
print(f"module coverage: {len(matrix)}/{len(course_ids)}; covered={sum(x['status'].startswith('covered') for x in matrix.values())}; gap={sum(x['status']=='gap' for x in matrix.values())}")
print(f"contradictions: {len(contradictions.get('items', []))}")
print(f"product matrix: {len(products.get('products', []))}; role tracks: {len(role_names)}; planned publications: {len(publications.get('volumes', []))}")
print("authority tiers: " + ", ".join(f"{key}={value}" for key,value in sorted(tiers.items())))
if errors:
    print("RESEARCH QA FAILED\n" + "\n".join(f"- {error}" for error in errors)); sys.exit(1)
print("RESEARCH QA PASSED: metadata, mappings, official minimums, gaps, and contradictions validated")
