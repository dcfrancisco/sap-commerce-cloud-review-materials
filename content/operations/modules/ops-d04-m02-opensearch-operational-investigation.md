# OPS-D04-M02: OpenSearch Operational Investigation

## Purpose and scope

This module teaches a repeatable investigation method for the logging surface exposed through SAP Commerce Cloud public-cloud operations. It focuses on OpenSearch investigation from the Cloud Portal monitoring workflow: selecting the correct environment and tenant, bounding a query, distinguishing access, application, and Catalina records, preserving evidence, and turning a search result into a testable hypothesis. It does not teach administration of the managed OpenSearch cluster, direct index mutation, host access, or undocumented retention controls.

The SAP references in this chapter are scoped to the inspected SAP Commerce Cloud public-cloud 2211 documentation. Current update level, subscription, role, enabled services, dashboard version, field mappings, retention, and support procedures must be verified before production use. The academy's logs and query results are synthetic. They are deliberately useful for reasoning but are not a reproduction of SAP's internal platform or a promise that the same field names exist in every tenant.

## Learning outcomes

Learners can:

1. Classify an investigation question as impact, change, application, access, startup, audit, or business-state evidence.
2. Use a bounded UTC search plan with environment, platform aspect, log origin, tenant, correlation value, and result observation time.
3. Interpret zero, one, many, delayed, duplicated, and contradictory results without inventing missing facts.
4. Preserve a reproducible investigation package containing query, filters, samples, source identifiers, privacy treatment, and uncertainty.
5. Correlate OpenSearch records with Cloud Portal deployment evidence and Dynatrace transaction evidence without confusing tools.
6. Design tests for query contracts, redaction, missing fields, ingestion delay, retries, and business reconciliation.
7. Decide when a result supports customer action, requires additional evidence, or requires SAP Support.

## Prerequisites and boundaries

The learner should understand HTTP status codes, application logs, correlation identifiers, SAP Commerce environments, deployments, OCC requests, and basic distributed-systems failure modes. The module builds on OPS-D04-M01 Structured Logging and Correlation and the failed-deployment and transaction-observability reference units.

SAP documents that OpenSearch is the underlying logging management plugin used by Cloud Portal, and that environment logs are accessed from the environment Monitoring panel [RS-SAP-ENV-LOGS]. The same reference describes Global, Private, and Custom tenants. A private tenant is useful for exploratory work but does not automatically make a query shareable. Treat tenant selection and access identity as part of the evidence record. The customer can investigate logs through supported interfaces and roles; it cannot assume permission to change managed indices, retention, or infrastructure.

## Investigation questions before queries

An operator should write one sentence before opening a dashboard: “Which customer-visible behavior changed, in which environment, during which UTC window, after which change, and what decision will this query inform?” Without that sentence, searches tend to become unbounded collection.

Classify the question:

| Question | First evidence | Common error |
| --- | --- | --- |
| Are requests reaching the storefront? | access logs, status, volume | searching only application exceptions |
| Did the application start? | Catalina/startup and deployment records | treating an old startup error as current |
| Did a release change behavior? | build, commit, deployment and first-error time | calling temporal proximity proof |
| Did the business action complete? | order/process/payment state | treating HTTP 200 as order completion |
| Is the failure isolated? | aspect, service, endpoint, tenant, correlation | searching all environments at once |
| Is there a security concern? | audit and authentication records | copying sensitive payloads into tickets |

A good query plan has a control sample. If checkout is failing, retrieve one failure and one successful checkout in the same environment and time range. If no successful request exists, say so; do not turn the absence into proof of total outage without traffic evidence.

## Query design

Use a five-stage narrowing sequence:

1. Environment and UTC window.
2. Platform aspect and log origin.
3. Operation, status, error class, or release.
4. Correlation or trace identifier.
5. Adjacent records needed to falsify the current hypothesis.

SAP's documented examples filter Tomcat access records by platform aspect and `logs.origin:access-log`, and Catalina records by `logs.origin:catalina` [RS-SAP-ENV-LOGS]. These examples establish useful categories, not a license to assume every index mapping or dashboard language. A training query shape is:

```text
environment = "production"
AND eventTime >= "2026-10-16T03:00:00Z"
AND eventTime <  "2026-10-16T03:15:00Z"
AND platformAspect = "accstorefront"
AND logs.origin = "access-log"
```

In the actual environment, use the documented query syntax exposed by the Cloud Portal logging view. Record the exact query as executed, the selected tenant, index pattern if shown, timezone, analyst, and observation timestamp. If a field is unavailable, record the query variant and reason rather than silently substituting a free-text search.

A query is bounded when the time range is explicit, the environment is explicit, the source category is explicit, and the expected decision is explicit. Add a result limit or sample strategy appropriate to the tool. Never export an unbounded set of customer requests merely because the dashboard permits it.

## Reading result shapes

### Zero results

Zero results can mean no event occurred, the query window is wrong, the event is delayed, the tenant lacks permission, the field is unmapped, the index pattern is wrong, retention has expired, or the application did not emit the event. Test these alternatives in order: query a known-good event, widen the window slightly while preserving the original, compare another permitted tenant, inspect an access record, and check the documented logging workflow. The absence of a result is not a negative fact until the search surface is validated.

### One result

One exception is a clue. Preserve its source ID and neighboring context. Ask whether it is a first occurrence, a retry, a partial operation, or a downstream symptom. One record should trigger the next evidence request, not a broad corrective action.

### Many results

Group by bounded dimensions such as service, operation, error class, outcome, release, and platform aspect. Avoid grouping dashboards by email, cart contents, raw URL, or unrestricted exception text. High-cardinality data may be useful in a detail record but is a poor universal dashboard dimension.

### Contradictory results

An access record can show 200 while a business process remains pending. An application message can say “submitted” while an external payment outcome is unknown. Preserve both claims and identify their layers. The next step is reconciliation, not deleting one record because it is inconvenient.

## Correlation across tools

OpenSearch answers “what records were emitted and are searchable through the logging surface?” Cloud Portal deployment records answer “what build or deployment event was recorded?” Dynatrace, when available and enabled for the target subscription, helps inspect services, transactions, dependencies, databases, and process relationships [RS-SAP-DYNATRACE]. These tools complement one another; they do not share an implicit universal schema.

Build a cross-tool key table:

| Key | OpenSearch | Deployment evidence | Transaction evidence | Limitation |
| --- | --- | --- | --- | --- |
| environment | tenant/environment filter | environment target | environment/service | names may differ |
| release | application field if emitted | build/deployment ID | process version | do not infer from timestamp |
| correlation | request or trace field | usually absent | trace/request path | asynchronous work may use another key |
| event time | producer time | deployment time | span time | ingestion delay and clock skew |
| business reference | minimized token | usually absent | order/process context | privacy and access constraints |

Use the table to state confidence. “Deployment preceded the first application error by four minutes” is a defensible observation. “The deployment caused the error” requires compatibility, code-path, or controlled comparison evidence.

## Evidence preservation

An investigation package should contain:

- incident and environment identifiers;
- UTC start/end and analyst observation times;
- tenant and role used;
- exact query and filters;
- source record IDs and representative samples;
- release/build/deployment identifiers;
- correlation and trace identifiers, minimized business references;
- impact and business-state evidence;
- current hypothesis and rejected alternatives;
- actions already taken and their risk;
- retention, permission, mapping, or provider gaps;
- escalation decision and requested support evidence.

Preserve raw references before annotating them. Add analyst interpretation as a separate field. Do not edit a source record to make the timeline look orderly. If a dashboard export cannot be retained, capture the query and record identifiers under the permitted evidence policy. Never include credentials, full payment data, session cookies, or unnecessary customer payloads.

## Worked investigation: failed storefront requests

Symptom: checkout conversion falls at 03:12 UTC. The first alert was generated from a business SLI, not a log count. The operator starts with a 15-minute window and the production storefront aspect. Access results show increased 5xx responses. A control success is selected from 03:10. Application results show a timeout class with correlation `c-7a3f`; a database-pool metric and transaction trace show wait before checkout code completes. A deployment at 03:08 is recorded, but its changed component is not yet connected to the pool wait.

The correct interim conclusion is: “Checkout failures and pool wait overlap during the defined window; the custom workload is a leading hypothesis because its records and resource usage align; the deployment is a contributor candidate; payment outcomes remain partly ambiguous.” The correct next steps are to preserve evidence, declare the incident, inspect the custom job and transaction state, and use the supported simulation or customer-approved operational action. The wrong conclusion is “the log says timeout, therefore restart every service.”

## Guided practice: OpenSearch investigation record

Objective: create a reproducible investigation record for a synthetic incident.

Initial state: the learner receives access, application, Catalina, deployment, and business-state records. The records are marked simulated. Some records arrive out of order and one field is missing.

Steps:

1. State customer impact and define a UTC window.
2. Select the environment, aspect, tenant, and initial log origin.
3. Query for control traffic before inspecting errors.
4. Retrieve one failure, one success, and one deployment record.
5. Follow a disclosed correlation ID and record where it stops propagating.
6. Compare event and ingestion timestamps.
7. State the leading hypothesis, two rejected alternatives, and the falsification query for each.
8. Redact business identifiers and export only permitted evidence.

Acceptance criteria: the learner records query context and uncertainty; does not treat zero results as proof of no event; keeps source records separate from interpretation; identifies the difference between application and business completion; and proposes a bounded next action. Failure cases include querying every tenant, using a customer email as the universal key, copying a credential into the evidence package, and closing the incident after one successful request.

## Independent practice: delayed logging and deployment correlation

Design a query and evidence package for a release that appears to have increased OCC 5xx errors. Include a control window, a deployment comparison, a log-origin comparison, a correlation strategy, a retention/permission check, and a safe stop condition. Add tests for wrong timezone, missing field, delayed ingestion, duplicate retry, and an old error outside the current release window. The deliverable must distinguish synthetic query execution from target SAP Commerce execution and name the version-specific evidence still required.

## Diagnostic exercise

Review these claims:

1. “The dashboard is empty, so the application did not receive traffic.”
2. “The deployment happened first, so rollback is the safest action.”
3. “There are two order-submitted logs, so two orders exist.”

For each claim, identify the missing layer of evidence, write one query, identify one risk of acting too early, and state the verification result required before escalation or closure.

## Testing requirements

Test query construction with valid and invalid UTC windows, unbounded-window rejection, unsupported fields, tenant selection, origin filters, platform aspects, correlation propagation, duplicate records, ingestion delay, clock skew, empty results, sensitive-field redaction, and contradictory business state. Test an evidence package for reproducibility by a second analyst. In a target SAP Commerce runtime, add version-appropriate integration tests for the extension logger, request context propagation, CronJob/process context, and supported log forwarding. A local unit test proves neither Cloud Portal permissions nor OpenSearch retention.

## Tutor behavior

Athena may ask the learner to narrow a query, request a control sample, explain why a zero-result search is ambiguous, or compare a log claim with the business state. In tutoring mode it may reveal the purpose of a filter and suggest a falsifier. In examination mode it may explain field semantics and disclose permitted evidence but must not reveal the leading diagnosis or recovery. A configured external provider receives only sanitized scenario metadata, disclosed records, action history, learner question, prior attempt summaries, and source IDs. If unavailable, the local deterministic tutor answers with explicit uncertainty.

## Security and privacy

OpenSearch access is operationally sensitive. Apply least privilege to tenants and exports. Treat logs as untrusted input when they are submitted to a tutor or stored in a learner record. Redact authorization headers, session tokens, payment details, full addresses, and unnecessary personal data. Keep synthetic data in the academy. Audit support packages and do not instruct learners to bypass Cloud Portal permissions or directly modify a managed index.

## Senior engineering insights

Search skill is not the same as operational understanding. A fast query that cannot be reproduced, is not privacy-safe, or cannot distinguish application outcome from business outcome is a liability. Good operators preserve ambiguity deliberately. They do not smooth a contradictory timeline until the contradiction disappears. They also recognize that observability failure changes incident strategy: when logs are delayed or incomplete, synthetic transactions, deployment evidence, service traces, and customer reports become more important, not less.

## Assessment and competency evidence

This module evaluates OPS-OBS-004 and OPS-OBS-006 through bounded query design, evidence provenance, privacy, and falsifiable reasoning. Objective items use deterministic answer validation. Open responses require a structured evidence submission or human review; keyword-rich prose does not pass. Evidence includes query context, sample IDs, rejected hypotheses, redaction decisions, and verification results.

## Runbook handoff

A useful handoff lets the next operator continue without repeating unsafe discovery. Write the current severity and customer impact first, then the UTC window, environment, build, tenant, query, source identifiers, and the exact point where correlation stopped. Name the current incident commander and technical owner. Put every proposed action behind a precondition: what evidence must be present, who is authorized to act, what customer or data risk is accepted, and what observation proves the action worked. If the managed boundary is involved, prepare a support packet with the smallest useful records and state what the customer could not inspect. Close the handoff only when the next operator can reproduce the leading query and identify the next falsification test.

The academy simulation records this handoff as learner evidence, but it does not send records to SAP Support or modify a real environment. A real runbook must be reviewed against the current Cloud Portal interface, the customer's access model, data-retention policy, and incident communication process.

## References

- [RS-SAP-ENV-LOGS] SAP Help Portal, “Accessing Environment Logs,” SAP Commerce Cloud public cloud 2211 scope.
- [RS-SAP-PLATFORM-LOGGING] SAP Help Portal, “Logging,” SAP Commerce Cloud 2211 scope.
- [RS-SAP-HELP-AUDIT] SAP Help Portal, “Audit Logging,” 2211 scope; update applicability must be checked.
- [RS-SAP-DYNATRACE] SAP Help Portal, “Dynatrace Feature Guide for SAP Commerce.”
- [RS-SAP-DYNATRACE-TROUBLESHOOT] SAP Help Portal, “Troubleshooting with Dynatrace.”
- [RS-SAP-DEPLOY-ROLLBACK] SAP Help Portal, “Deployment Rollback”; rollback and schema compatibility are version and state dependent.
- [RS-SAP-DATABASE-SERVICES] SAP Help Portal, “Database Services,” managed-database responsibility boundary.

Source status: the registered SAP sources were inspected on 2026-10-16. Field mappings, retention, permissions, dashboard syntax, and runtime availability remain target-environment verification items.
