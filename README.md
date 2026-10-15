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
python3 scripts/build_publication.py
python3 -m unittest discover -s tests -v
```

The validator reports exact counts and refuses to call draft content validated. The publisher creates an editable HTML manual and, when `pandoc` is available, a PDF in `dist/`.

## Current vertical slice

- `content/course.json`: versioned catalog and 24-module roadmap.
- `content/modules/01-architecture-fundamentals.md`: complete reference module reading manual.
- `content/labs/catalog-foundation.json`: deterministic catalog lab with acceptance criteria.
- `content/assessments/module-01.json`: original assessment items with explanations, mappings, rubrics, and sources.
- `content/contracts/athena-learning-v1.json`: import/export and tutor boundary contract.
- `academy/server.py`: local learner flow and API endpoints.
- `academy/simulation.py`: clearly labeled SAP Commerce learning simulation.
- `scripts/validate_content.py`: content and assessment QA.

The simulation is not the SAP Commerce runtime. No Shopify, live SAP Commerce, Athena Hub, certification exam, or employer integration is claimed.
