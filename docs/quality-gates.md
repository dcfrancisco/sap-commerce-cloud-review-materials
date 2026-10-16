# Commercial quality gates — Engineering Alpha

Release labels are evidence summaries, not declarations of expert approval. Automated checks are machine validation only. Independent SAP technical, security, professional editorial, and learner-acceptance reviews remain pending.

| Gate | Current evidence | Result |
| --- | --- | --- |
| A Technical accuracy | 60 governed sources; versioned operational and testing claims; 27/27 general mappings; 60/60 Operations/SRE roadmap mappings; contradiction register | PARTIAL: independent SAP SME and live-runtime validation absent |
| B Educational quality | Outcomes, expanded readings, four stateful incidents, 15 operations exercises, four developer testing exercises, progressive hints, separate competency evidence, assessments, and deterministic remediation dimensions | PARTIAL: instructional-design and learner reviews absent |
| C Content completeness | Eight general modules and one Operations/SRE module authored | FAIL: 59 Operations/SRE modules and most academy modules remain |
| D Software correctness | Unit/integration coverage includes scenario recommendation/no-leakage, product-neutral APIs, seeded reproducibility, testing-mastery caps, persistence, state transitions, scenario-specific coaching, and unsafe-action hard-fails | PARTIAL: browser, load, concurrency, actual SAP platform test execution and wider contract coverage absent |
| E Security and privacy | Answers withheld; request size/identifier checks; synthetic fixtures; no learner-code execution | FAIL: authentication, authorization, CSRF, rate limiting, tenant isolation and security review absent |
| F Editorial/publication | Nine reproducible module PDFs; structure/page metadata checks; representative render inspection | PARTIAL: PDF is untagged; professional editorial/accessibility review and final visual identity absent |
| G Operational readiness | Local setup, reset, deterministic replay, source and gate validators | FAIL: production packaging, observability, upgrade support and support runbooks absent |
| H Product acceptance | Automated end-to-end API learning-cycle evidence | FAIL: no observed representative learner acceptance or human sign-off |

The machine-readable Operations/SRE result is maintained in `content/operations/release-gates.json`. Commercial release is prohibited while any required gate is partial or failed.

## Reference-unit promotion criteria

OPS-D03-M01 and OPS-D04-M03 may become specialization reference modules only after independent SAP technical review, professional editorial review, accessibility review, live-version verification or explicit unexecuted boundaries, observed learner completion, and remediation of material findings. Their current status is `implemented-review-required`.
