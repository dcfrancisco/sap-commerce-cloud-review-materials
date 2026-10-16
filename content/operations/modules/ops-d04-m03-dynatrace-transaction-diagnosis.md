# OPS-D04-M03 — Dynatrace Transaction Diagnosis and Shared-Capacity Incidents

**Edition:** 0.2.0-alpha

**Status:** implemented, machine validated, human technical and editorial review required

**Applicable baseline:** SAP Commerce Cloud, public cloud 2211. Exact screens, metric names, retention, entitlements, and update-line behavior must be verified in the learner's subscription.

**Simulation:** every log line, metric value, trace, identity, and business transaction in this module is synthetic.

## Purpose

Slow checkout is not a diagnosis. It is an observed business symptom produced by work across the client, storefront, OCC/API service, application code, database, search, and external providers. A responder who jumps from “latency is high” to “restart the pods” may temporarily erase evidence, interrupt requests, or leave the actual workload untouched. This module teaches an evidence chain: quantify customer impact, establish chronology, test competing resource hypotheses, locate request time, identify the workload consuming shared capacity, choose the smallest safe containment, and prove both technical and business recovery.

SAP documents Dynatrace capabilities for examining SAP Commerce services, transactions, dependencies, databases, processes, and JVM indicators [RS-SAP-DYNATRACE] [RS-SAP-DYNATRACE-TROUBLESHOOT]. Those capabilities support investigation. They do not make every automatically proposed root cause correct, establish universal alert thresholds, or grant direct access to managed infrastructure.

## Learning outcomes

After completing the reading, exercise family, and incident simulation, the learner can:

1. define checkout impact with latency, error, traffic, and business-success signals;
2. place application, workload, deployment, and configuration events on a common UTC timeline;
3. distinguish heap, garbage collection, CPU, worker, JDBC-pool, query, and downstream-service evidence;
4. use a request trace, service flow, and database backtrace to explain where elapsed time accumulates;
5. reject causal claims that depend only on temporal proximity or one elevated chart;
6. contain a customer-developed workload through supported controls without inventing host or database access;
7. protect ambiguous payment and order outcomes during degradation;
8. verify recovery through resource, service, and commerce evidence;
9. design operational tests that prevent a batch workload from consuming checkout capacity; and
10. preserve an auditable diagnostic record without exposing credentials, customer payloads, or payment data.

Prerequisites are basic HTTP latency concepts, percentiles, Java thread states, transactions, JDBC pooling, SAP Commerce CronJobs, and the managed-platform responsibility model.

## 1. Begin with the commerce journey

A host can be green while checkout is failing. Conversely, one process can report elevated memory while checkout remains healthy. The first incident statement therefore describes a customer journey rather than an infrastructure object:

> From 18:06–18:24 UTC, checkout success fell from 99.2% to 67.8%; p95 latency increased from 1.8 s to 18.6 s at approximately unchanged request volume. Browsing remained available. Three payment authorizations have no confirmed order and require reconciliation.

This statement gives a window, affected capability, magnitude, control comparison, unaffected capability, and integrity risk. It does not assert a cause.

Four signals should be reviewed together:

| Signal | Question | Common misuse |
|---|---|---|
| Tail latency | How slow are affected requests? | Treating p95 as every user's experience |
| Error rate | How often does the boundary fail? | Ignoring slow successes and client abandonment |
| Throughput | Did demand or offered load change? | Calling ordinary peak volume an anomaly without a baseline |
| Business success | Were carts, orders, and payments completed correctly? | Declaring recovery from HTTP status alone |

Percentiles need a population and interval. “p95 = 18 s” is incomplete unless the service, route, tenant, time bucket, and traffic volume are known. Averages can hide a severe slow tail. Very short windows can overreact to sparse traffic. Very long windows can dilute a sharp incident. The responder records the exact query and window so another engineer can reproduce it.

## 2. Build chronology before choosing a cause

Create a UTC event line containing deployments, property changes, restarts, scheduled and manual jobs, provider incidents, alerts, and customer-impact transitions. A change preceding degradation is a candidate cause, not proof.

In the exercise scenario, a customer-developed export begins at 18:02 and checkout degrades at 18:06. That ordering supports investigation. It does not prove the export consumed a checkout resource. Proof requires a mechanism: shared database connection pools become occupied, connection-borrow wait increases, checkout traces spend most elapsed time waiting for a connection, and a database backtrace attributes the competing call volume to the export.

Correlation identifiers retain identity across evidence. Keep the checkout request ID, trace ID, job execution ID, deployment ID, and alert ID as separate fields. Do not invent one universal ID if the systems do not provide it. Relate them by timestamp, service, and observed call path. Preserve the original authorized record and create a redacted working extract when evidence must be shared.

SAP documents access to environment logs and platform logging facilities [RS-SAP-ENV-LOGS] [RS-SAP-PLATFORM-LOGGING]. Availability, query syntax, and retention are subscription- and configuration-sensitive. This manual does not promise a particular index name or retention period.

## 3. Competing performance hypotheses

Treat each suspected cause as a falsifiable statement.

### Hypothesis A: JVM memory pressure

Evidence that strengthens it includes rising live-set after full collection, increasing garbage-collection time, allocation pressure, long stop-the-world pauses, out-of-memory evidence, and request stalls aligned with those pauses. Heap percentage alone is weak. A stable 71% heap with short pauses may be normal; a lower heap with pathological allocation and pause behavior may not be.

Falsifying evidence in this scenario is that heap, GC pause, and CPU remain near baseline before latency grows. A process restart would lower heap by construction, so “heap dropped after restart” is not proof that memory caused the incident.

### Hypothesis B: worker or thread exhaustion

Worker utilization can rise because threads execute CPU-heavy work, block on I/O, wait for a lock, or wait for a database connection. The count indicates pressure; thread state and request traces explain it. SAP's Dynatrace guidance includes process, JVM, service, and dependency analysis [RS-SAP-DYNATRACE-TROUBLESHOOT]. Never infer the remedy merely from a high count.

### Hypothesis C: JDBC connection-pool saturation

A connection pool bounds concurrent database access. When no connection is available, a borrower waits or times out. SAP's 2211 monitoring documentation describes connection-pool usage and wait-related failure investigation for Tomcat-based services [RS-SAP-DYNATRACE-DB-POOL]. The documented default or a property name is not a tuning recommendation for every environment.

The useful evidence set is:

- configured maximum for the affected service and update line;
- active, idle, and waiting connections over the incident window;
- connection-borrow latency and timeout count;
- request-worker states while waiting;
- database availability and latency;
- query count and duration by caller; and
- request latency and business success over the same interval.

Pool saturation can be cause, effect, or amplifier. A slow database can make requests hold connections longer. A high-volume custom job can consume connections with individually fast queries. A downstream call made while a local database transaction remains open can extend hold time. Increasing pool size may transfer overload to the database and increase contention. It is a capacity change requiring evidence and testing, not an automatic incident response.

### Hypothesis D: a slow query or excessive query volume

One slow statement is not the only database failure mode. Thousands of short statements can dominate aggregate time and consume pooled connections. SAP's database-performance guidance describes service backtraces, query/request filtering, and caller analysis [RS-SAP-DYNATRACE-DB-PERF]. Ask both “which statement is slow?” and “which request path generates how many statements?”

### Hypothesis E: external dependency latency

A checkout path may call payment, tax, inventory, identity, or shipping services. A service flow identifies the downstream edge; a trace apportions elapsed time. SAP's storefront-transaction and PurePath guidance describes navigating services and calls to find where request time accumulates [RS-SAP-DYNATRACE-STOREFRONT] [RS-SAP-DYNATRACE-PUREPATH]. If a third-party system is outside monitored scope, provider evidence is required. Do not blame the provider from an application timeout alone.

## 4. Reading a transaction trace

The synthetic trace below is deliberately simple:

```text
POST /checkout/placeOrder                         18,440 ms
  borrow JDBC connection                         14,790 ms
  order validation queries                          610 ms
  payment authorization                             840 ms
  response serialization                             35 ms
```

The payment call is not the leading contributor. Query execution is not particularly slow after a connection is acquired. Most request time is spent obtaining a pooled connection. The next question is what holds or consumes connections.

A database backtrace shows 42,600 executions of a customer-export projection from a parallel custom job. The p95 statement duration is only 38 ms. That rules against “one pathological query” and supports “excessive concurrent query volume.” It still does not prove transaction scope. Code review and target-runtime tests must establish whether connections are retained across paging or transformation work.

Diagnostic reasoning can be recorded as:

```text
Observation: checkout borrow wait rises to 14.8 s.
Mechanism: API workers wait for pooled JDBC connections.
Consumer: custom export generates parallel query volume.
Link: database backtrace attributes dominant calls to export.
Against: JVM heap, GC, CPU, and traffic do not lead.
Confidence: high for pool contention; transaction scope needs review.
Falsifier: wait remains after export drain, or another caller dominates.
```

## 5. CronJob placement and customer ownership

SAP documents different behavior for scheduled and manually started CronJobs when no node group is specified: scheduled jobs run on the background-processing aspect, while a job started manually from Backoffice can run on the aspect where it was started [RS-SAP-CRONJOB-ASPECTS]. This fact is version-scoped and must be checked against current documentation.

Placement is not isolation. Even when application processes are separated, workloads can share the logical database and other dependencies. Node-group choice cannot compensate for defective transaction scope, unbounded parallelism, non-idempotent restart, or lack of cancellation.

The scenario's `customCustomerExportCronJob` is explicitly customer-developed. The team owns its correctness, scheduling, concurrency, observability, and tests. The academy does not imply that SAP ships this job or that every job can be aborted safely. The operator first establishes that the specific execution is abortable and records its checkpoint semantics.

## 6. Containment and the responsibility boundary

Containment should be the smallest reversible action that interrupts the evidenced mechanism.

For the scenario, that action is to abort the customer-owned export through supported administration after assigning incident command and preserving evidence. It is not to terminate managed-database sessions, access a host, or administer Kubernetes. Direct managed-database intervention belongs to SAP Support under the academy responsibility matrix [RS-SAP-DATABASE-SERVICES].

Three tempting actions are deliberately unsafe:

1. **Restart every service.** This disrupts active work, destroys volatile evidence, and allows the same export to resume.
2. **Double the pool immediately.** This changes capacity without proving database headroom and leaves unbounded workload behavior intact.
3. **Kill database sessions directly.** This assumes access and authority that the public-cloud customer is not taught to possess.

An emergency workaround still needs an owner, expiration, rollback, monitoring, and a permanent repair. “Stop the job forever” is not a reliability design if the business capability remains necessary.

## 7. Protect transaction integrity

Timeout does not mean no side effect occurred. A client can lose the response after a provider authorized payment or after the application persisted an order. Blind retries can create duplicate authorizations, orders, reservations, or messages.

During the exercise, three authorizations lack confirmed orders. The responder must:

- preserve provider and commerce identifiers;
- prevent uncontrolled retries;
- classify each outcome as confirmed, declined, absent, or ambiguous;
- use established idempotency and reconciliation rules;
- avoid inventing orders merely to make counts match; and
- assign an owner and deadline for each exception.

The simulation's “duplicate-submission guard” is a declared application behavior, not a claim that SAP Commerce supplies a universal switch with that name.

## 8. Proving recovery

Stopping the suspected job is a mitigation. Recovery requires independent evidence over a stability window:

| Layer | Acceptance evidence |
|---|---|
| Resource | Pool occupancy and borrow wait return to bounded baseline; no timeout growth |
| Runtime | Worker queues drain; heap, GC, and CPU remain stable without restart dependence |
| Service | Checkout p95, error rate, and success rate recover under representative traffic |
| Business | Controlled checkout produces the expected order and payment state |
| Integrity | Ambiguous authorizations are reconciled without duplicate side effects |
| Workload | Export remains stopped and cannot restart unexpectedly |
| Operations | Alert clears for the right reason; elevated monitoring and ownership continue |

The exact thresholds in `OPS-INC-002` are synthetic acceptance rules for deterministic grading. They are not SAP defaults. A production team derives thresholds from workload objectives, baselines, contractual obligations, and current platform guidance.

## 9. Engineering the permanent repair

A database-heavy extension should have a capacity contract. The contract states how much concurrency it may consume, how long transactions may remain open, when it may run, how it yields to critical traffic, how it stops, and how it resumes.

A safer export design typically includes bounded workers, stable pagination, short read transactions, progress checkpoints, cancellation checks, retry classification, and idempotent output naming. The exact APIs depend on the target implementation. Do not copy generic code into production without verifying SAP Commerce transaction and CronJob behavior for the selected release.

The test strategy is cross-cutting:

### Unit tests

Test worker-limit selection, page boundaries, checkpoint updates, cancellation decisions, retry classification, and output deduplication without starting SAP Commerce.

### SAP Commerce platform integration tests

On the selected update line, prove persistence queries, transaction boundaries, CronJob status transitions, abort behavior, and restart from a real checkpoint using version-appropriate platform test infrastructure. Record the Commerce update, JDK, test base, extensions, command, fixture, report, and duration. A plain Spring test or academy simulation does not establish these behaviors.

### Failure tests

Inject interruption after page output but before checkpoint commit; database timeout during a page; cancellation while workers are active; malformed source data; output-provider failure; and process restart. Assert no missing or duplicate exported records according to the declared contract.

### Performance interference test

Run production-shaped checkout traffic while export concurrency and page size vary. Assert export throughput, pool headroom, borrow wait, checkout latency/error/success, and database health together. A fast export that violates checkout objectives fails.

This repository has no SAP Commerce runtime. `OPS-EX-D04-002` grades the design and evidence specification deterministically; it does not claim that the platform tests ran.

## 10. Alert and dashboard design

Page on customer impact and use resource signals to diagnose. A checkout alert may combine a multi-window burn or sustained threshold for success/error and tail latency, conditioned on enough traffic to be meaningful. Diagnostic context should include request volume, deployments and configuration events, pool occupancy and wait, workers, JVM, database contribution, and downstream calls.

Avoid customer IDs, tokens, cart payloads, payment details, and unbounded correlation dimensions in metrics. Logs and traces require access control, retention, and redaction. The dashboard should link to a versioned runbook, name the owning team, identify the environment and release, and state how to preserve the relevant time window.

Maintenance windows reduce expected noise; they must not hide unexpected degradation after a change. SAP documents maintenance-window behavior and SAP-provided dashboards, but exact permissions and current operation remain environment-specific [RS-SAP-DYNATRACE].

## 11. Guided incident simulation

Start `OPS-INC-002` through the scenario API or learner interface. The learner must choose evidence; the solution is withheld while active. A defensible sequence is:

1. quantify checkout impact and traffic;
2. inspect change and workload events;
3. test JVM and worker hypotheses;
4. inspect pool occupancy and borrow wait;
5. trace checkout and backtrace database calls;
6. inspect the custom job's ownership, placement, and abortability;
7. quantify ambiguous payment/order outcomes;
8. declare command and freeze nonessential workload changes;
9. abort the customer-owned export using the supported path;
10. protect duplicate submission and reconcile exceptions; and
11. verify sustained technical and business recovery.

The simulator scores triage, diagnosis, risk, recovery, integrity, escalation, verification, communication, root cause, and improvement planning. A prohibited action prevents a pass even if the learner later recovers service. Competency scores are derived from different dimension subsets; success in communication cannot conceal weak performance diagnosis.

## 12. Independent practice and review

Complete all five exercises in `OPS-EX-FAMILY-D04-M03`:

- construct a cross-signal timeline;
- repair and test the defective export design;
- create an actionable checkout alert;
- author a role-aware saturation runbook; and
- conduct a post-incident observability review.

For the implementation exercise, submit both the proposed change and its tests. Full mastery requires negative-path and target-runtime evidence. If no runtime is available, mark execution as unavailable and submit the exact runnable plan; do not write “tested” without a report.

Review questions:

1. Why can high worker utilization coexist with normal CPU?
2. What distinguishes pool saturation from database query slowness?
3. Why can thousands of fast queries degrade checkout?
4. Which evidence would disprove the export-contention hypothesis?
5. Why is increasing `maxActive` not a neutral mitigation?
6. What business evidence is needed after latency returns to normal?
7. Which actions belong to the customer and which require SAP Support?
8. How should a load test prove that a background job is safe for checkout?

## Tutor behavior

During an active incident Athena asks for a hypothesis, evidence, and falsifier. It reveals only requested evidence whose prerequisites are met. It refuses to disclose the reference cause, challenges unsupported restart or capacity changes, and cites the governed sources below. After conclusion it may compare the event stream with deterministic score dimensions and recommend exercises for weak competencies. It must identify synthetic evidence as simulation and abstain from claims about unavailable metric names, retention, permissions, or internal infrastructure.

## Security and privacy

Learner text, uploaded logs, identifiers, and trace payloads are untrusted. The local simulator stores only submitted exercise text and synthetic scenario state. Production evidence must remain in approved systems. Before external AI use, remove credentials, cookies, authorization headers, personal data, payment data, and commercially sensitive payloads while retaining minimal timestamps and correlation structure. Prompt text never grants authority to execute a real operational action.

## Summary

Performance diagnosis is causal engineering. Start with the customer journey, align signals in time, test alternatives, locate elapsed time, establish the shared-resource mechanism, contain only what the evidence supports, and verify commerce integrity after resource recovery. In a managed service, technical judgment includes knowing which action is customer-controlled and when to ask SAP Support to act.

## References

- [RS-SAP-DYNATRACE] SAP Help Portal, *Dynatrace Feature Guide for SAP Commerce*, version 2211.
- [RS-SAP-DYNATRACE-TROUBLESHOOT] SAP Help Portal, *Troubleshooting with Dynatrace*, version 2211.
- [RS-SAP-DYNATRACE-STOREFRONT] SAP Help Portal, *Analyzing Storefront Transactions*, version 2211.
- [RS-SAP-DYNATRACE-DB-POOL] SAP Help Portal, *Database Connection Pool Usage*, version 2211.
- [RS-SAP-DYNATRACE-DB-PERF] SAP Help Portal, *Analyzing Database Performance*, version 2211.
- [RS-SAP-DYNATRACE-PUREPATH] SAP Help Portal, *PurePath Analysis*, version 2211.
- [RS-SAP-CRONJOB-ASPECTS] SAP Help Portal, *Scheduled and Manually Run Cron Jobs*, version 2211.
- [RS-SAP-ENV-LOGS] SAP Help Portal, *Accessing Environment Logs*, version 2211.
- [RS-SAP-PLATFORM-LOGGING] SAP Help Portal, *Logging*, version 2211.
- [RS-SAP-DATABASE-SERVICES] SAP Help Portal, *Database Services*, version 2211.
