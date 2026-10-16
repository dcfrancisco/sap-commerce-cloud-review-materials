# SAP Commerce Cloud AI-Native Engineering Academy

Standalone local-first foundation for a verified, competency-based SAP Commerce Cloud learning product.

This repository was created after an audit found no existing source tree, Athena Hub implementation, Forma application, publication pipeline, or tests in the supplied workspace. The current release is therefore an independently runnable vertical slice, not an integration claim.

## Run

```bash
python3 -m academy.server
```

Then open <http://127.0.0.1:8000>. The service uses only the Python standard library.

## Validate and publish

```bash
python3 scripts/validate_content.py
python3 scripts/validate_research.py
python3 scripts/validate_operations.py
python3 scripts/validate_developer_testing.py
python3 scripts/report_coverage.py
python3 scripts/build_publication.py
python3 scripts/validate_publication.py
python3 -m unittest discover -s tests -v
# with the local server running and Chrome/Playwright available:
ACADEMY_CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' NODE_PATH=/Users/dannyfrancisco/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules node scripts/browser_e2e.mjs
```

The validators report exact counts and refuse to call draft content validated. The publisher creates editable HTML and, when `pandoc` is available, PDF module manuals in `dist/`. Publication QA checks source depth, references, code fences, PDF readability metadata, page size, and page counts; visual review remains a release gate.

## Current vertical slice

- `content/course.json`: versioned catalog and 27-module roadmap.
- `content/modules/`: eight authored, review-required manuals (M01-M05 and M25-M27); none is marked commercially complete.
- `content/labs/catalog-foundation.json`: deterministic catalog lab with acceptance criteria.
- `content/assessments/module-01.json`: original assessment items with explanations, mappings, rubrics, and sources.
- `content/contracts/athena-learning-v1.json`: import/export and tutor boundary contract.
- `academy/server.py`: local learner flow and API endpoints. Assessment delivery omits answers; submission returns explanation and records evidence in SQLite.
- `academy/tutor.py`: provider-neutral grounded tutor MVP with local abstaining adapter.
- `academy/incidents.py`: deterministic, staged incident tutor for storefront, administration, and cloud-operations scenarios.
- `academy/operations.py`: shared stateful ecosystem simulation with progressive evidence, consequential actions, safety hard-fails, coaching, replay, and persisted competency evidence.
- `academy/practice.py`: seeded deep-practice sessions with protected solutions, progressive hints, deterministic rubric dimensions, assisted/independent evidence, and no variant-count inflation.
- `content/exercises/developer-testing-m02-m05.json`: four defect-driven M02–M05 exercises with separate implementation/testing scores, negative-path requirements, runtime boundaries, and an implementation-mastery cap when testing evidence fails.
- `academy/simulation.py`: clearly labeled SAP Commerce learning simulation.
- `scripts/validate_content.py`: content and assessment QA.

The Operations/SRE specialization adds a 12-domain, 60-module roadmap; nine role paths; a formal managed-platform responsibility matrix; six implemented-review-required modules; 27 deep-practice exercises; nine operations competencies; and 36 internally validated assessment records. The shared runtime contains four tested stateful incidents, including two Operations/SRE incidents, and supports filtered or natural-language scenario recommendation without exposing solutions. The observability slice derives separate competency evidence from different scoring dimensions and now evaluates structured incident reasoning rather than keyword-heavy free text. The evaluator uses typed objective, structured-rubric, executable-test, and guarded-review strategies. Four additional developer exercises make testing an independently scored competency across M02–M05. Seeded variants are deliberately excluded from asset counts. The Operations/SRE specialization's 2,500-item and 150-incident targets remain future work.

The simulations are not the SAP Commerce runtime. No Shopify, live SAP Commerce, Athena Hub, certification exam, or employer integration is claimed. The general corpus contains 36 validated assessment records and 24 competencies, including four testing-specific competencies; these are verified implementation counts, not acceptance of the 1,200-item target. Commercial maturity remains **Engineering Alpha**.
