# Commercial quality gates

Release labels are evidence summaries, not declarations of expert approval. Automated checks are identified as machine validation. No independent human technical/editorial review has yet occurred.

| Gate | Acceptance criteria | Current evidence | Result |
| --- | --- | --- | --- |
| A Technical accuracy | Versioned SAP claims, three applicable official sources per completed module, contradiction register | Source registry, coverage matrix, research validator | PARTIAL PASS: M01–M05 only |
| B Educational quality | Objectives, worked examples, exercises, rubrics and remediation align | M01–M05 content and 24 items | PARTIAL; expert curriculum review missing |
| C Content completeness | Substantial lessons, labs, assessments, source coverage | 5 of 24 modules complete under current minimum checks | FAIL for academy release |
| D Software correctness | Unit, persistence, assessment, tutor and learner-flow tests | Automated suite plus HTTP smoke evidence | PARTIAL PASS; broader API/E2E tests required |
| E Security and privacy | Protected answers, validated inputs, learner-data policy, provider-secret handling | Answers withheld until submission; local SQLite separation | FAIL: authentication, authorization and security test suite incomplete |
| F Editorial/publication | Structural, accessibility, visual and technical editorial review | Five PDFs generated; automated existence/page QA | FAIL: visual/editorial review not complete |
| G Operational readiness | install/configure/diagnose/recover/support | README local run instructions | FAIL |
| H Product acceptance | representative learners complete and evaluate meaningful journeys | no independent learner study | FAIL |

## Reference-module promotion criteria

M01 may be promoted to the commercial reference module only when it has a full technical review, editorial review, rendered-page inspection, verified runnable examples or explicit runtime gaps, a complete exercise family, security/performance coverage, and end-to-end learner evidence. Its current metadata remains an implementation milestone, not commercial publication approval.
