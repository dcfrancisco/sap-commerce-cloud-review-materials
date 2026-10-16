# OPS-D04-M05: Alert Engineering and Evidence Preservation

## Purpose and scope

An alert is an operational decision contract. It should identify meaningful customer or business risk early enough to act, avoid paging on noise, and direct the responder to evidence that can distinguish likely causes. This module teaches alert engineering for SAP Commerce Cloud operations: service indicators, thresholds, multi-window logic, change correlation, maintenance handling, ownership, runbooks, alert testing, evidence retention, and post-incident review.

The module is intentionally conservative about SAP-specific claims. SAP Commerce Cloud public-cloud 2211 and its documented observability integrations provide monitoring surfaces, but exact metrics, query fields, retention, alert APIs, role permissions, and subscription features must be verified for the target environment. The local alert fixtures and incident outcomes are simulations. They do not create real Cloud Portal alerts, Dynatrace problems, OpenSearch rules, or production changes.

## Learning outcomes

Learners can:

1. Write an alert contract with signal, denominator, window, threshold policy, owner, severity, and runbook.
2. Choose customer-impact and dependency indicators without treating a technical symptom as universal truth.
3. Use multi-window and multi-signal reasoning to reduce alert fatigue while retaining fast detection.
4. Correlate alerts with deployments, catalog/index jobs, external dependencies, JVM/resource signals, and business ambiguity.
5. Design maintenance, suppression, deduplication, escalation, and evidence-preservation behavior.
6. Test positive, negative, delayed, missing, sampled, and adversarial alert inputs.
7. Evaluate whether an alert is actionable, safe, privacy-preserving, and supported by the target deployment model.

## Prerequisites and responsibility boundaries

The learner should understand OpenSearch investigation, dashboards, structured correlation, SLO concepts, incident command, and SAP Commerce request and background-processing paths. The Dynatrace feature guide for SAP Commerce documents service, transaction, database, and performance monitoring concepts [RS-SAP-DYNATRACE]. The troubleshooting guide describes problems, events, logs, hosts, processes, and relationships [RS-SAP-DYNATRACE-TROUBLESHOOT]. Cloud Portal environment logging is documented separately [RS-SAP-ENV-LOGS]. Use the documented surfaces and supported administration available to the customer's role. Do not teach direct changes to managed infrastructure or database sessions as customer alert remediation.

## The alert contract

Every alert should answer:

- What changed?
- Why does it matter to customers or a protected business process?
- How is the signal calculated?
- What is the denominator and time window?
- What evidence is attached for diagnosis?
- Who owns the response?
- What action is permitted, and what action requires SAP Support?
- When does the alert resolve?
- What evidence must be retained?

Example contract:

```text
Name: checkout-impact
Signal: eligible checkout success and tail latency
Window: traffic-aware rolling windows; UTC
Trigger: sustained business impact with corroborating error/latency signal
Context: release, access/application records, service flow, pool/JVM/dependency panels
Owner: commerce operations
Severity: based on customer and order impact, not latency alone
Runbook: bounded evidence, safe containment, reconciliation, recovery verification
Resolution: sustained success under representative traffic plus business-state checks
```

This is an engineering contract, not a claim that SAP exposes these exact names or thresholds. Store the contract with version, owner, review date, and target environment.

## Signal selection

Page on impact where possible. For checkout, a success ratio, failed submission rate, ambiguous payment/order count, and tail latency are stronger primary signals than heap or CPU alone. Use technical signals as diagnosis and corroboration. For catalog/search, freshness lag, rejected index input, search visibility, and product-detail/search disagreement may matter more than raw request count. For background jobs, age of oldest work, failure/retry rate, checkpoint progress, and interactive traffic interference are useful.

An alert must account for denominator. Zero checkout attempts may produce no errors and should not be marked healthy without a traffic or synthetic-transaction check. A small denominator may require a minimum volume guard. A high-traffic flash sale may change expected latency and error patterns; compare against a workload baseline rather than a static universal threshold.

## Thresholds and windows

Use environment-specific baselines and document the calculation. A single threshold is easy to understand but can be noisy. A multi-window policy can require a fast-burn and slow-burn condition, or a short impact window corroborated by a longer trend. The precise formula should be simple enough to test and explain.

Avoid alerting on every transient exception. Group duplicate events by incident key, preserve counts, and do not hide a second independent failure under the first. Alert suppression during a planned deployment should still retain unexpected business impact. Maintenance context is a hypothesis filter, not permission to ignore all errors.

## Evidence attached to an alert

An alert should link or attach a bounded evidence bundle:

1. UTC trigger and observation times.
2. Environment, aspect, release/build, and change markers.
3. Business indicator and denominator.
4. Representative success and failure samples.
5. Correlation/trace IDs or safe tokens.
6. Service-flow and dependency context.
7. JVM, worker, pool, database, search, or batch signals relevant to the hypothesis.
8. Logging query and tenant context, where permitted.
9. Current action history, risk, and unresolved business state.
10. Runbook version and responder ownership.

Do not place raw customer or payment payloads in alert labels. Use bounded dimensions and links to access-controlled detail. The alert should remain useful if the log provider is delayed or unavailable; include telemetry freshness and fallback evidence.

## Deduplication and escalation

Choose an incident key that groups the same failure without merging unrelated failures. Environment, journey, aspect, and failure class may be appropriate; customer ID or raw exception text is usually unsafe and high-cardinality. Preserve the first occurrence, latest occurrence, count, and representative samples. When severity changes, record the business reason and the operator.

Escalation should be explicit. Customer-owned extension behavior, supported job controls, and evidence collection may be operator actions. A managed database, platform infrastructure, or unsupported host operation may require SAP Support. The alert runbook must state the boundary and the evidence package. Do not let an automated alert trigger a destructive operation without authorization, compatibility checks, and a tested rollback or recovery path.

## Failure patterns

### Alert fatigue

If a page is repeatedly ignored, measure the false-positive cause: threshold, denominator, duplicate grouping, maintenance handling, or missing context. Do not simply increase the threshold. A less sensitive alert may miss a smaller but important business impact.

### Alert blindness during deployment

A deployment marker can explain chronology but cannot silence all impact. Compare control traffic, release applicability, error class, dependency behavior, and rollback compatibility. Preserve evidence before a change.

### Healthy technical signal, unhealthy business state

Checkout latency may recover while payment authorization remains ambiguous. Search may respond quickly while the index is stale. Alert resolution requires technical and business verification appropriate to the journey.

### Provider or telemetry failure

If Dynatrace, OpenSearch, or another signal provider fails, raise observability degradation when it affects detection confidence. Do not convert absent metrics into green. Use synthetic transactions, access records, Cloud Portal evidence, and customer reports while documenting uncertainty.

## Guided practice: build a checkout alert

Objective: design and test an actionable checkout alert from a synthetic incident.

Initial state: the fixture includes success, latency, traffic, errors, pool wait, deployment, dependency, and ambiguous order state. The fixture is simulation-only.

Steps:

1. Define eligible checkout and successful completion.
2. Choose a primary impact signal and two corroborating signals.
3. Set workload-aware trigger policy and minimum volume guard.
4. Define deduplication key, severity, owner, and maintenance behavior.
5. Attach bounded diagnostic evidence and freshness state.
6. Define safe containment, escalation, recovery, and closure checks.
7. Test the alert against a real impact fixture, harmless traffic spike, telemetry outage, deployment window, and ambiguous payment state.

Acceptance criteria: the alert pages on meaningful business impact, provides discriminating evidence, preserves privacy, does not silently suppress unexpected failures, distinguishes telemetry loss, and requires independent technical/business recovery. Failure cases include paging on heap alone, suppressing every deployment-window alert, using email as an incident key, and closing after latency alone improves.

## Independent practice: alert review and redesign

Review an alert that fires on fixed checkout p95, has no success denominator, groups by full URL, and pages during all deployments. Produce a revised contract, test matrix, runbook link, owner matrix, maintenance rule, and post-incident metrics. Explain which choices are engineering recommendations, which require target SAP verification, and which are simulation behavior.

## Diagnostic exercise

During a flash sale, checkout p95 rises but success remains within baseline. A second alert reports pool wait and a third reports delayed logs. The deployment marker is active. Decide whether to page, investigate, or suppress each signal. State the evidence that would change your decision and how you communicate uncertainty. A strong response avoids both automatic suppression and automatic rollback; it requests business impact, denominator, resource, dependency, change, and telemetry-freshness evidence.

## Testing requirements

Test alert calculation with normal traffic, zero traffic, low denominator, flash-sale load, transient error, sustained impact, duplicate event, delayed ingestion, missing signal, permission failure, deployment window, dependency outage, ambiguous payment state, and privacy violation. Test deduplication, resolution, escalation, maintenance expiry, replay, and runbook version changes. Use seeded synthetic fixtures and assert the alert state and evidence package. Actual Dynatrace/Cloud Portal alert execution requires the selected SAP Commerce update line, subscription, roles, and supported integration; local tests do not prove it.

## Tutor behavior

Athena should ask what business decision the alert protects, what evidence corroborates it, and what unsafe action the runbook must prevent. It may challenge thresholds, denominator errors, suppression, and missing-data assumptions. In examination mode, it can explain terminology and show the synthetic signals requested but cannot reveal the preferred alert design before submission. A configured provider receives the alert contract, disclosed synthetic evidence, learner question, prior attempts, and source IDs; the deterministic rubric controls published assessment outcomes.

## Security and privacy

Alert payloads and labels are operational data. Avoid customer identifiers, payment details, secrets, and full request payloads. Restrict alert routing and dashboards by role. Validate that escalation integrations do not copy sensitive logs to unapproved systems. Treat learner and provider content as untrusted. Keep audit records for changes to trigger policy, routing, suppression, and ownership.

## Worked example: deployment-window suppression

A release begins at 02:00 and a checkout alert fires at 02:04. The maintenance record explains chronology but does not make impact safe to ignore. The responder compares success and eligible attempts, error class, traffic, dependency contribution, and the changed aspect. If customer impact is real, the alert remains actionable and the runbook directs evidence preservation and release evaluation. If the alert is only a known test signal, the suppression record must include scope, owner, expiry, and expected end state. A permanent mute is not maintenance; it is loss of detection.

## Operational handoff

The alert handoff records the trigger version, rule expression, incident key, deduplication count, maintenance state, notification route, owner, severity, runbook version, evidence links, and unresolved risks. It also states whether the alert was generated from live provider data or the academy simulation. When a provider is unavailable, the handoff names alternate signals and lowers confidence rather than declaring green. After recovery, preserve the trigger, acknowledgement, action, verification, and resolution timeline so the alert can be improved rather than merely closed.

## Senior engineering insights

Alert quality is measured by decisions, not alert count. A useful page reduces time to understand impact and choose a safe next action. A perfect threshold cannot compensate for missing business context, poor evidence preservation, or unsafe runbooks. Review alert performance after every material incident: detection delay, false-positive rate, missed impact, evidence usefulness, operator toil, and corrective action effectiveness. Reliability improves when alerts, dashboards, runbooks, tests, and ownership evolve together.

## Assessment and competency evidence

This module evaluates OPS-OBS-005 and OPS-INC-004 through alert contracts, multi-signal reasoning, safety, privacy, evidence preservation, and test design. Structured responses are scored by explicit criteria. Unstructured prose receives guarded feedback and human-review escalation; keyword overlap cannot confer mastery. Expert qualification also requires successful investigation and safe recovery across incidents, not alert vocabulary.

## Alert review worksheet

Review every production alert at least on a defined cadence and after a material incident. Record trigger count, page count, false-positive count, missed or late impacts, median acknowledgement, evidence-link success, ownership changes, suppression intervals, and runbook completion. Segment these measures by journey and environment; an aggregate rate can hide that checkout is noisy while order reconciliation is silent. Inspect whether the alert's denominator remained valid after a release, traffic change, catalog migration, or dependency contract change.

When a policy changes, retain the old version and reason for change. Test the new policy against historical or seeded windows before enabling it. Verify that a maintenance rule expires and that a suppressed alert can still create an audit record. Review routing failure as a first-class case: if the page channel is unavailable, the operational design needs a documented alternate path. This is a customer reliability responsibility, not an assumption that a managed provider will always deliver a notification.

The academy simulator evaluates alert decisions from deterministic fixtures and records the learner's selected evidence, severity, suppression, action risk, and closure checks. It does not deliver notifications, alter a Cloud Portal policy, or contact an incident-management service. A live implementation requires explicit provider configuration, authentication, authorization, delivery testing, and security review.

## References

- [RS-SAP-DYNATRACE] SAP Help Portal, “Dynatrace Feature Guide for SAP Commerce.”
- [RS-SAP-DYNATRACE-TROUBLESHOOT] SAP Help Portal, “Troubleshooting with Dynatrace.”
- [RS-SAP-DYNATRACE-STOREFRONT] SAP Help Portal, “Analyzing Storefront Transactions.”
- [RS-SAP-DYNATRACE-DB-POOL] SAP Help Portal, “Database Connection Pool Usage.”
- [RS-SAP-ENV-LOGS] SAP Help Portal, “Accessing Environment Logs.”
- [RS-SAP-PLATFORM-LOGGING] SAP Help Portal, “Logging.”
- [RS-SAP-CRONJOB-ASPECTS] SAP Help Portal, “Scheduled and Manually Run Cron Jobs.”

## Release checklist

Before enabling an alert, review the contract with operations, application, security, and business owners. Verify trigger and resolution with deterministic fixtures, delivery with the actual provider, maintenance expiry, duplicate grouping, telemetry loss, privacy redaction, and runbook permissions. Record the target update line, subscription dependencies, and rollback for the policy itself. A machine-passing test suite is evidence of implementation behavior; it is not independent SAP expertise or commercial approval. Keep the alert policy source, test report, provider delivery evidence, and reviewer decision together as one release record.

Source status: registered SAP sources were inspected on 2026-10-16. Alert APIs, metric names, thresholds, retention, permissions, and routing integrations remain target-environment verification items.

These limitations remain explicit release evidence for every future alert implementation.

An alert that cannot be tested, owned, or explained is not ready for production paging. Preserve its limitations as part of the release record. This discipline keeps machine validation, provider verification, and expert approval visibly separate.

For learner evidence, record the trigger, selected severity, suppression or escalation choice, supporting signals, rejected alternative, and verification result. The simulator can score those decisions deterministically, but it cannot certify delivery through a real monitoring provider or prove a production response policy.

When an alert is wrong, the remediation should identify whether detection, diagnosis, routing, authorization, or recovery verification failed. A threshold increase without this analysis may reduce pages while increasing hidden customer impact. A runbook update should have a test fixture, an owner, a review date, and a measurable outcome. This creates a feedback loop between incidents and reliability engineering rather than a static collection of notification rules. Review the evidence at the next release and record the decision with the responsible owner.
