# OPS-D04-M04: Metrics, Dashboards, and Service Health

## Purpose and scope

Dashboards should help an operator decide what to do next, not merely display every available metric. This module teaches service-health dashboard design for SAP Commerce Cloud operations: start with customer journeys, define measurable indicators, connect technical saturation to business impact, show dependencies and changes, and preserve the diagnostic window. It covers API latency and errors, traffic, JVM and worker signals, database/pool contribution, search and background processing, synthetic transactions, and dashboard failure modes.

The module uses SAP Commerce Cloud public-cloud 2211 documentation and Dynatrace documentation as the authority for documented monitoring surfaces. Exact metric names, retention, permissions, dashboards, and enabled capabilities depend on the update level and subscription. The local dashboard fixtures are simulated and do not prove that a live SAP environment exposes the same series. The customer designs application and journey instrumentation within supported boundaries; SAP manages underlying platform infrastructure and support-required controls.

## Learning outcomes

Learners can:

1. Define checkout, product retrieval, search, and order-submission service indicators from a user and business perspective.
2. Distinguish availability, latency, error, throughput, saturation, freshness, and correctness signals.
3. Design a layered dashboard with overview, diagnosis, dependency, change, and business-state panels.
4. Interpret p50, p95, p99, rate, count, and denominator changes without overclaiming.
5. Detect JVM pressure, worker exhaustion, JDBC wait, database latency, dependency delay, search staleness, and catalog lag using a shared timeline.
6. Test dashboard panels against positive, negative, delayed, missing, and contradictory fixtures.
7. Preserve evidence and state uncertainty when metrics are absent, sampled, delayed, or subscription-dependent.

## Prerequisites and source boundary

Learners should understand the OpenSearch investigation method, structured correlation, SAP Commerce request paths, catalogs, search, checkout, background processing, and basic statistics. SAP's Dynatrace feature guidance for SAP Commerce describes monitoring services, transactions, databases, and performance [RS-SAP-DYNATRACE]. Its troubleshooting guidance describes hosts, processes, problems, events, logs, and service relationships [RS-SAP-DYNATRACE-TROUBLESHOOT]. The storefront and database guidance provides specific investigation concepts for transaction flow and JDBC pool usage [RS-SAP-DYNATRACE-STOREFRONT][RS-SAP-DYNATRACE-DB-POOL]. These sources support the monitoring surfaces, not universal thresholds.

## Start with a journey

A service-health dashboard begins with a decision. For checkout, the decision may be “Can a customer submit an order safely right now, and if not, which dependency or workload should be contained?” A useful dashboard therefore begins with:

- successful checkout attempts divided by eligible attempts;
- tail latency for successful and failed attempts;
- error and timeout rate with a known denominator;
- traffic volume and request mix;
- ambiguous payment/order outcomes;
- dependency and resource evidence;
- current release, deployment, and configuration changes.

The dashboard does not need to display every JVM counter on the overview. It should link to a diagnostic view that explains why the journey indicator changed. A product-detail dashboard might use successful product retrieval, stale-price rate, catalog freshness, search visibility, cache or projection lag, and OCC latency. A batch dashboard might use completion rate, age of oldest item, checkpoint progress, retry count, cancellation status, and impact on interactive traffic.

## Indicator taxonomy

| Indicator | Question | Pitfall |
| --- | --- | --- |
| Availability | Did an eligible operation succeed? | dividing by changing or unknown denominator |
| Latency | How long did the user journey take? | using average only; hiding tail latency |
| Error rate | How often did an operation fail? | counting harmless retries as customer errors |
| Throughput | How much work or traffic is occurring? | treating high throughput as health |
| Saturation | Is a shared resource near a limit? | assuming platform limits without evidence |
| Freshness | How old is a projection or catalog view? | confusing freshness with correctness |
| Correctness | Did the business result match the contract? | declaring correctness from HTTP status |

Each indicator needs a definition, source, window, aggregation, denominator, owner, and known limitations. A threshold is a policy for a specific environment, not an SAP product default unless an official source says so. Begin with baseline and business impact. Review threshold changes after releases and major traffic events.

## Layered dashboard design

### Layer 1: business overview

Show customer success, impact, traffic, critical journey latency, and the active release/change marker. Use a time range that supports comparison with a healthy period. Include a clear “data unavailable” state. Do not show a green panel simply because its source stopped reporting.

### Layer 2: service flow

Show storefront/OCC/API transaction latency, status distribution, dependency contribution, request volume, and correlation links. Dynatrace service and transaction views can help connect a user journey to services and dependencies when enabled [RS-SAP-DYNATRACE-STOREFRONT]. Keep the journey name stable across releases or document the migration.

### Layer 3: resource diagnosis

Show JVM heap and garbage-collection behavior, worker/thread utilization, request queues, JDBC pool occupancy and borrow wait, database/query latency, and cache behavior as applicable. A rising heap percentage without GC or latency change is not automatically an incident cause. A pool wait increase that precedes checkout tail latency is more discriminating than a pool occupancy snapshot alone. The SAP JDBC pool guidance is a reference for investigation concepts, not a universal numeric target [RS-SAP-DYNATRACE-DB-POOL].

### Layer 4: data and background processing

Show catalog synchronization outcomes, index job state, product freshness, rejected records, batch backlog, retry counts, and overlap with interactive traffic. A successful synchronization job can still leave search stale if downstream indexing is delayed or rejected. Show source and projection timestamps separately.

### Layer 5: change and dependency context

Show deployment/build markers, configuration changes, external dependency health, payment/tax/shipping status, and planned maintenance. A change marker provides chronology, not causality. A dependency panel must state whether its data is direct, inferred, delayed, sampled, or unavailable.

## Statistical interpretation

Percentiles describe a distribution, not a promise to every request. p95 can improve while a small but business-critical cohort fails. Combine tail latency with success, error, and traffic. When traffic falls to zero, a latency panel may look healthy while availability is untested. When a denominator changes after a release, compare raw counts and rates.

Use a common time window. Metrics may be emitted at different intervals and aggregations. Align by UTC, record the sampling interval, and mark late data. Avoid mixing a five-minute rate with a one-hour average without labeling the difference. When the dashboard rolls up data, preserve the raw query or link that can reproduce the view.

## Failure patterns

### JVM pressure versus database delay

JVM pressure is supported by changes in allocation, heap occupancy, GC pause, CPU, thread or worker behavior, and request queuing. Database delay is supported by query or backtrace contribution, connection borrow wait, transaction duration, and a resource timeline. One graph is not enough. The learner must identify which signal leads and what evidence would falsify the hypothesis.

### False green after telemetry loss

A missing series must render unknown, not zero. Add freshness and ingestion-health indicators. Test dashboard behavior when the telemetry provider returns no data, partial data, stale data, or an authorization error.

### Search and catalog divergence

Product detail may read an authoritative or newer source while search reads an asynchronous projection. Show source update, synchronization completion, index update, and search visibility separately. A single “catalog healthy” tile hides the exact failure boundary.

### Batch overload

A batch can improve its own throughput while harming checkout. Place interactive SLI and batch resource contribution on the same time axis. Include concurrency, pool wait, query duration, and business impact. Do not solve a workload problem by blindly increasing a managed pool or adding workers.

## Guided practice: design the checkout dashboard

Objective: design a dashboard and diagnostic link for a synthetic checkout incident.

Initial state: the fixture contains traffic, success, latency, errors, pool wait, JVM, dependency, deployment, and payment ambiguity signals. Some series are delayed. The fixture is not a live SAP runtime.

Steps:

1. Define the checkout eligible denominator and success event.
2. Choose overview indicators and explain why each is actionable.
3. Create diagnostic panels for service flow, pool/JVM/database, dependency, deployment, and business state.
4. Mark the baseline period and current incident window.
5. Add a telemetry freshness indicator and an unknown state.
6. Correlate the panel values with the disclosed incident evidence.
7. Define recovery verification and an evidence package.

Acceptance criteria: the dashboard distinguishes customer impact from resource signals, uses a traffic-aware denominator, does not treat missing data as healthy, links to change and dependency context, preserves payment ambiguity, and names the subscription/runtime verification still required. Failure cases include a single fixed p95 threshold, average-only latency, a zero-filled missing series, and a green dashboard with no traffic.

## Independent practice: product freshness and search health

Design a dashboard for a product that appears in detail but not search. Include source catalog state, staged/online or publication context where applicable, synchronization status, index input/reject state, search visibility, time lag, and a controlled recovery verification. Identify which data is SAP-documented, which is a general projection pattern, and which is simulation-only. Add negative tests for a genuinely missing product, a permissions restriction, a stale index, a rejected classification record, and delayed telemetry.

## Testing requirements

Test dashboard calculations with zero traffic, denominator changes, partial failure, retries, delayed ingestion, missing series, duplicate events, clock skew, release markers, and contradictory business state. Test privacy and cardinality limits. Test that a service-health view does not expose payment payloads or customer identifiers. For a target SAP Commerce runtime, execute version-appropriate smoke and integration checks for the actual transaction, service, database, and log signals; local fixtures cannot validate Dynatrace subscription behavior.

## Tutor behavior

Athena should ask what decision a panel supports, which denominator is valid, which signal leads, and what a missing series means. It can challenge a learner who treats heap, p95, or a deployment marker as a root cause. In examination mode it can explain metric terminology and reveal permitted synthetic signals but not the reference diagnosis or preferred mitigation. Any external provider receives sanitized signal summaries and source IDs only; deterministic dashboard calculations remain authoritative.

## Security and privacy

Dashboards should use bounded, privacy-safe dimensions. Do not expose customer email, payment tokens, raw addresses, or complete request payloads as labels. Restrict operational dashboards by role and environment. Treat screenshots, exported CSV, traces, and provider prompts as sensitive. Maintain a retention and access policy, and document whether a metric is sampled or aggregated.

## Worked example: a false recovery

At 14:00, checkout p95 returns to baseline after a custom batch is paused. The overview tile is green, but the success denominator is still falling and three payment outcomes remain ambiguous. The correct dashboard interpretation is partial recovery: the resource contention signal improved, but the business journey is not yet healthy. The operator keeps the incident open, verifies representative orders, and assigns reconciliation. A dashboard that collapses these states into one green tile creates a dangerous closure path.

## Operational handoff

Every panel should have a named owner and a source query version. During handoff, capture the selected time range, sampling interval, current release, last known good period, data freshness, and whether a value is direct or derived. The next operator should be able to reproduce the view and identify the next falsifier. If a panel is unavailable, write “unknown” and state the alternative evidence path. Do not make the dashboard itself the only copy of the incident record.

## Senior engineering insights

The most valuable dashboard is often the one that shows a business symptom next to the smallest set of discriminating technical signals. More panels do not automatically improve diagnosis. Dashboards should encode uncertainty: unavailable, stale, sampled, and not-applicable are different states. A service-health design is successful when two operators reach the same next evidence request and can explain why an apparent recovery is safe enough to verify.

## Assessment and competency evidence

This module evaluates OPS-OBS-005 and OPS-PERF-004 through indicator definitions, cross-signal interpretation, dashboard architecture, and test design. Structured submissions are scored by criteria and evidence. Open prose without a structured rubric is escalated for human or configured semantic review and cannot pass through keyword overlap.

## Dashboard review checklist

Before publishing a dashboard, ask whether every panel has an owner, a source, a unit, an aggregation, a time zone, a freshness expectation, a privacy classification, and a runbook link. Mark whether it is direct measurement, derived calculation, sampled observation, or simulation. Define the behavior when the source is unavailable. Confirm that a change marker cannot be edited by the same operator who is using it as causal evidence without an audit trail. Review the dashboard with a normal period, a known incident, a no-traffic period, and a telemetry outage.

For a release review, capture a baseline before deployment, a representative traffic window after deployment, business success and tail latency, dependency contribution, resource saturation, search/catalog freshness, and any ambiguous transaction count. Save the dashboard definition or query version where permitted. If the target platform does not expose a requested series, record the gap and use a supported proxy only when its limitations are explicit. Never invent a metric because a tile looks better with a number.

The synthetic academy dashboard implements only the evidence and state transitions described by its scenario fixtures. It is useful for testing the learner's reasoning and panel choices. It is not evidence that Dynatrace, OpenSearch, Cloud Portal, or an SAP Commerce update release will expose a particular metric name, retention period, or dashboard API.

## References

- [RS-SAP-DYNATRACE] SAP Help Portal, “Dynatrace Feature Guide for SAP Commerce.”
- [RS-SAP-DYNATRACE-TROUBLESHOOT] SAP Help Portal, “Troubleshooting with Dynatrace.”
- [RS-SAP-DYNATRACE-STOREFRONT] SAP Help Portal, “Analyzing Storefront Transactions.”
- [RS-SAP-DYNATRACE-DB-POOL] SAP Help Portal, “Database Connection Pool Usage.”
- [RS-SAP-DYNATRACE-DB-PERF] SAP Help Portal, “Analyzing Database Performance.”
- [RS-SAP-DYNATRACE-PUREPATH] SAP Help Portal, “PurePath Analysis.”
- [RS-SAP-ENV-LOGS] SAP Help Portal, “Accessing Environment Logs.”

## Release checklist

Before a dashboard is used for a release gate, verify the owner, source version, target environment, update line, time zone, units, aggregation, denominator, freshness, privacy classification, and fallback behavior. Run the dashboard against a known-good window and a seeded incident. Have an operator explain the next action from the overview without opening every panel. Record unresolved metric gaps instead of filling them with assumed defaults. This checklist is an academy teaching aid and requires adaptation to the customer's operational acceptance process. The reviewer should also record who can change the dashboard, how changes are audited, and how learners distinguish a dashboard calculation from an SAP-supported product behavior.

Source status: registered sources were inspected on 2026-10-16. Metric names, thresholds, retention, permissions, and feature availability must be verified for the target subscription and update line.

Dashboard evidence should be time-bounded, reproducible, and explainable to a second responder. Include the query version and the observation window whenever a panel contributes to a release or incident decision.

For learner evidence, record the panel selected, the value or unknown state observed, the competing hypothesis it supported or rejected, and the next action. This prevents a dashboard screenshot from becoming an answer key and makes the reasoning auditable. Keep the result reproducible.
