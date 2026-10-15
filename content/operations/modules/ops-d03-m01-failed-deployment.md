# OPS-D03-M01 — Failed Deployment Investigation and Safe Recovery

**Edition:** 0.2.0 Engineering Alpha  
**Applicability:** SAP Commerce Cloud, public cloud, 2211 documentation set verified 2026-10-16  
**Competencies:** OPS-DEP-004, OPS-OBS-004, OPS-REC-004, OPS-INC-004, OPS-LEAD-005  
**Review state:** implemented and automatically tested; independent SAP technical review and professional editorial review are pending

## Purpose and operational boundary

A failed deployment is not only a pipeline failure. It may be a partially completed change to an application, type-system metadata, database schema, media state, search projection, credentials, or external transaction flow. A responsible operator must first establish what changed and what did not. Only then can the team decide whether to cancel, roll forward, restore, or request managed-service assistance.

This chapter teaches investigation and recovery for SAP Commerce Cloud public cloud. It does not teach direct Kubernetes administration, host access, direct database modification, or infrastructure backup commands as customer capabilities. SAP states that it supports and maintains the database service and that only SAP support teams have direct database access. Customers can initiate supported backup and restore operations through Cloud Portal, subject to roles and production controls [RS-SAP-DATABASE-SERVICES]. SAP also performs managed Kubernetes upgrades; customer teams must plan for documented service effects but do not administer the control plane [RS-SAP-CLUSTER-UPGRADE].

The worked scenario is synthetic. Its chronology, logs, metrics, and actions are deterministic teaching fixtures. The operational principles are grounded in the cited public documentation, but the fixture does not claim to reproduce every internal implementation detail of SAP's managed service.

## Learning outcomes

After completing the reading, assessment, and incident, a learner can:

1. construct a defensible deployment timeline from Cloud Portal, application, monitoring, and business evidence;
2. distinguish deployment cancellation, application rollback, schema compatibility, and data restoration;
3. explain why a prior application build is not automatically safe against a changed database;
4. use logs and metrics to separate a failed activation from JVM, connection-pool, or dependency symptoms;
5. choose a supported recovery path while protecting orders, payments, media, and search consistency;
6. define recovery acceptance tests and cross-system reconciliation;
7. package evidence for SAP Support without claiming access to managed infrastructure; and
8. turn the incident into release-gate, rehearsal, observability, and runbook improvements.

Prerequisites are basic knowledge of Commerce extensions and `items.xml`, Cloud Portal concepts, HTTP/OCC health checks, structured logging, and transaction boundaries. A learner may bypass the reading only by passing the diagnostic and completing this incident without unsafe actions.

## 1. Four states, not one rollback button

Treat a deployment as coordinated state across at least four planes:

```text
Source and build       Application runtime       Persistent state       Projections/dependencies
commit + manifest  -> binaries + config     -> DB + media          -> search + ERP + payment
      |                    |                       |                         |
      +--------------------+--- deployment evidence ------------------------+
```

The planes can disagree. A build can compile while its system update fails. A database can contain an added column while no new application instances become ready. A restore can recover database and media while leaving the search index outside that recovery point. An external payment provider can authorize a request for which Commerce did not persist an order. “Deployment failed” therefore describes an outcome, not the recovery state.

SAP documents three broad data migration choices during deployment: leave data unchanged, migrate/update, or initialize depending on the workflow. Initialization destroys existing business data and is not a live-production rollback technique. The scenario never permits it as recovery.

### SAP-specific fact versus engineering interpretation

SAP's rollback guidance states that canceling during a deployment can optionally revert the database to its pre-deployment state, but after cancellation the application is not automatically reverted to a previous build; another successful deployment is required to recover fully. It also states that a failed `migrate data` deployment can leave the schema broken and that there is no automatic database rollback after deployment completion [RS-SAP-DEPLOY-ROLLBACK].

The four-plane model above is an original operational teaching model. It is not an SAP product object. It helps teams reason about the consequences described in the official material without inventing a universal internal architecture.

## 2. Schema compatibility is the rollback gate

An older build can be deployable as an artifact and still be incompatible with the current schema. SAP's rollback guidance warns that builds should reference the same database schema. It identifies additive customization as a possible way to retain backward compatibility, not a guarantee [RS-SAP-DEPLOY-ROLLBACK].

Additive changes generally reduce rollback risk because old code can ignore a new table or nullable column. They do not eliminate risk. Compatibility also depends on changed constraints, relation metadata, deployment mappings, defaults, interceptors, process definitions, serialized payloads, and application assumptions. A rename that is represented as “drop old plus create new” is materially different from an additive field. A default that is computed only by new code may leave older code reading incomplete records.

Type-system versioning supports rolling or blue/green deployment patterns by creating version-specific copies of selected type metadata while application versions share main item tables. SAP warns that significant breaking schema changes are usually unsuitable for this technique and recommends rehearsing rollback procedures in lower environments [RS-SAP-TYPE-SYSTEM-VERSIONING]. The existence of versioning is therefore not evidence that any arbitrary old build is safe.

A release record should classify each persistent change:

| Change class | Example | Backward-compatibility question | Required evidence |
| --- | --- | --- | --- |
| Additive | nullable attribute and deployment column | Can old code ignore it safely? | old/new integration tests against migrated fixture |
| Constraint tightening | nullable becomes required | Can in-flight and historical rows satisfy it? | data profile and migration rehearsal |
| Semantic change | status meaning changes | Can old processes interpret new values? | mixed-version behavior test |
| Destructive | remove/rename table or attribute | What reads or writes still reference it? | staged deprecation, migration and restore test |
| Metadata mapping | typecode or deployment mapping changes | Do physical mappings remain unique and stable? | system update rehearsal and type-system inspection |

The compatibility declaration belongs to the release artifact. It should name both directions: whether new code runs on the old state during rollout, and whether old code runs on the new state during rollback.

## 3. Evidence before action

The first operational objective is to establish a shared clock and preserve evidence. Record the subscription/environment, deployment ID, build, source commit, migration mode, start and failure times, first error, endpoint health, business impact, operator actions, and current incident owner.

Cloud Portal exposes application logs through OpenSearch. SAP's documented workflow enters logging from the environment Monitoring panel, selects the appropriate tenant, uses the `logs-json-*` index pattern, and narrows the time range and platform aspect [RS-SAP-ENV-LOGS]. Queries shown in a runbook must be reviewed against the current index mappings; a copied query is not evidence until its environment, time range, and result set are recorded.

Start with the earliest causal error around the deployment correlation identifier. Cascading startup errors often dominate the final pages of a log stream. Reading backward from the last exception can lead to the wrong subsystem. A useful evidence record includes:

```text
environment: production-eu
deployment_id: dep-8841
build: 2026.10.16-rc3
commit: 7f31b2a
migration_mode: migrate-data
window_utc: 21:55..22:10
first_error_utc: 22:04:16.803
first_error_component: platform system update
customer_impact: OCC and checkout unavailable
operator_actions: none before evidence capture
```

Do not place access tokens, credentials, payment data, customer personal data, or unredacted request bodies into an incident note. Preserve correlation while minimizing sensitive content. Access to shared versus private OpenSearch tenants also affects who can see saved investigative artifacts.

## 4. Logs, metrics, and business state answer different questions

Logs establish discrete events: a migration step, exception, process exit, failed readiness check, or external response. Metrics show magnitude and timing: error rate, request latency, JVM heap, garbage collection, connection waits, or throughput. Business records establish transaction correctness: orders created, authorizations captured, reservations committed, messages acknowledged, and records awaiting reconciliation.

SAP's Dynatrace troubleshooting guidance describes topology, host/process health, JVM metrics, response times, and service relationships [RS-SAP-DYNATRACE-TROUBLESHOOT]. Operators use that telemetry to test hypotheses, not to infer a cause from one red chart. If OCC errors jump when the new application fails readiness while heap and database waits remain normal, memory pressure is not the leading hypothesis. Conversely, successful deployment status does not disprove a post-activation performance regression.

For the reference incident, the learner receives:

- a failed deployment after migration starts;
- a first error involving conflicting deployment metadata;
- OCC failures without preceding heap or connection-pool pressure;
- a schema-change declaration with an unproven rollback path;
- a valid pre-deployment backup that does not include the search index; and
- payment authorizations requiring reconciliation.

Each observation narrows a boundary. No single observation is the full root cause.

## 5. Choosing a recovery strategy

Four recovery families must be considered explicitly.

### Corrected roll-forward

Correct the migration or configuration, rehearse against a production-like copy of the prior state, and deploy a schema-compatible build. This usually preserves post-backup data and is preferred in the reference scenario because the mapping conflict is understood and repairable. It is not automatically fastest; a speculative fix can deepen the failure.

### Application rollback

Deploy an earlier build only when it is demonstrated compatible with the current database and configuration. Artifact availability is not compatibility evidence. In the simulator, immediate deployment of the prior build is a critical unsafe action because schema changes have begun and the team has no compatibility proof.

### Database/media/build restoration

SAP's data backup and restore capability captures time-related environment state. Database and media consistency matter, and restoration can overwrite the target environment. SAP documentation also notes operational roles for backup management [RS-SAP-DATA-BACKUP-RESTORE]. The rollback documentation describes backup records spanning database, media storage, and deployed application [RS-SAP-DEPLOY-ROLLBACK].

Recovery planning must also account for state outside the backup. Search indexes may require regeneration. ERP, identity, tax, payment, shipping, and messaging systems may have processed transactions after the recovery point. Restoring Commerce does not reverse those side effects. The incident commander must establish an RPO, identify the divergence window, and assign reconciliation ownership.

### Managed-service escalation

SAP Support is required for direct database access or managed infrastructure intervention [RS-SAP-DATABASE-SERVICES]. A useful escalation package includes business impact and severity, environment, deployment/build/commit, migration mode, UTC timeline, first error, backup identifier, actions already taken, schema compatibility analysis, and the precise assistance requested. “Production broken, please investigate” wastes both time and shared context.

## 6. Worked decision record

The reference team records this decision:

```text
Decision: corrected roll-forward with rc4
Reason: migration first error is localized to a conflicting custom deployment mapping;
        intended schema changes are otherwise additive; prior build compatibility is unproven.
Preconditions:
  - freeze production changes;
  - preserve deployment and OpenSearch evidence;
  - validate corrected mapping against pre-rc3 production-like snapshot;
  - retain usable pre-deployment backup;
  - engage SAP Support for managed recovery contingency.
Recovery checks:
  - platform readiness and endpoint health;
  - product detail and search consistency;
  - anonymous/authenticated cart and checkout;
  - order process and integration queues;
  - two payment authorization exceptions reconciled;
  - elevated monitoring through the agreed stability window.
Rejected: immediate previous-build deployment because database compatibility is not proved.
```

This decision separates fact, inference, risk, and acceptance. It also makes reversal conditions visible to approvers.

## 7. Recovery is not complete at HTTP 200

A health endpoint can be green while business state is wrong. Recovery acceptance needs independent checks across technical and transactional boundaries:

1. application instances are ready and stable without restart loops;
2. OCC health and representative authenticated/anonymous requests succeed;
3. product detail, category navigation, and search agree for known records;
4. price, currency, inventory, promotion, cart, and checkout behavior are correct;
5. an order traverses expected process states and reaches downstream integrations;
6. queues, CronJobs, and business processes do not accumulate new failures;
7. payment authorizations, orders, reservations, and ERP documents reconcile across the incident window;
8. error rate, latency, heap, garbage collection, threads, and database waits remain within the release baseline; and
9. monitoring remains elevated for an explicit stability period with a named owner.

These are engineering acceptance criteria. Exact checks depend on the deployed solution and contracts; they are not presented as a fixed SAP product checklist.

## 8. Guided simulation

### Objective

Recover `OPS-INC-001` without data loss, unsupported platform access, or an unverified rollback.

### Initial state

The rc3 `migrate-data` deployment failed. Checkout and order submission are unavailable. The schema state is unknown. No incident commander is assigned.

### Required work

1. Start the scenario and state an initial hypothesis without asserting a cause.
2. Request deployment history and time-bound metrics.
3. Request the earliest relevant error log, then the schema compatibility record.
4. Inspect backup coverage and business transactions around the failure.
5. Freeze further deployments and package evidence for SAP Support.
6. Choose and execute a safe recovery in the simulator.
7. Run independent recovery validation.
8. Submit a conclusion containing timeline, impact, diagnosis, recovery rationale, transaction reconciliation, and preventive controls.

### Acceptance criteria

- all required evidence groups are inspected;
- no critical prohibited action is attempted;
- the conclusion distinguishes symptom from cause;
- recovery is schema-compatible and uses supported boundaries;
- payment/order exceptions receive a reconciliation owner;
- technical and business checks verify recovery;
- the score is at least 0.80; and
- persisted evidence is created for all mapped competencies.

### Failure cases

- deploying the previous build merely because it is available;
- initializing production;
- treating deployment cancellation as complete rollback;
- restoring only one state component without consistency analysis;
- declaring recovery from an HTTP health check alone;
- retrying payment or order requests without idempotency and reconciliation evidence; or
- deleting or broadly clearing evidence before root-cause capture.

### Cleanup and replay

Use the simulation reset endpoint to remove the selected session and its event/evidence records. Reset never changes published content or another learner's session. Start a new session to compare a restore strategy with corrected roll-forward.

## 9. Independent practice

Write two alternative recovery decision records. The first assumes the corrected migration cannot be made safe within the business RTO. The second assumes the backup is older than an accepted payment batch. For each, identify RPO impact, required SAP Support action, media/search implications, cross-system reconciliation, validation, customer communication, and criteria for abandoning the strategy.

Do not claim one universally correct answer. The rubric rewards explicit evidence, safe boundaries, data-integrity reasoning, and reversible decisions.

## 10. Diagnostic review and common mistakes

**Mistake: latest error equals root cause.** Startup and health failures often cascade. Find the first error associated with the deployment phase and test it against the timeline.

**Mistake: normal heap proves the application is healthy.** It only weakens a memory-pressure hypothesis. The application can fail because of schema, configuration, credentials, or dependency errors.

**Mistake: additive means reversible.** Additive schema is one compatibility condition. Semantic and metadata changes can still break old code.

**Mistake: backup exists, therefore recovery is safe.** Verify status, scope, age, application build relationship, environment compatibility, restore authorization, and external divergence.

**Mistake: speed is the expert metric.** A fast action that risks data loss or extends the outage cannot earn an expert pass. The simulator gives risk, integrity, and verification explicit weight.

## 11. Security and privacy

Production investigation has privileged data. Apply least privilege to Cloud Portal, OpenSearch, Dynatrace, backups, and deployment actions. Preserve audit records. Redact tokens, cookies, personal data, payment details, and secrets before attaching evidence. Do not paste unrestricted production logs into an AI provider. The local simulator contains synthetic records and does not execute learner code or connect to SAP systems.

The current local academy has no production authentication or tenant isolation. It is suitable for a single-user engineering environment only. Hosted or multi-user deployment is blocked until identity, authorization, CSRF protections, rate limits, tenant isolation, data retention, and audit controls are implemented and tested.

## 12. Reliability improvements after recovery

A defensible post-incident program changes the system that produced the failure:

- require a machine-readable compatibility declaration for every persistent change;
- rehearse migration and selected recovery against a current production-like snapshot;
- retain immutable build, commit, manifest, migration mode, and approval evidence;
- fail release gates when rollback/roll-forward evidence is absent;
- correlate deployment identifiers through logs and monitoring;
- maintain transaction-reconciliation queries that do not mutate data;
- test backup restoration and search rebuild in approved environments;
- define SAP Support escalation packages and ownership;
- monitor recovery acceptance, not only deployment status; and
- review repeated operational toil for safe automation.

Corrective actions must have owners, due dates, verification methods, and risk acceptance when deferred. “Be more careful” is not a control.

## 13. Tutor behavior

Before scenario completion, the tutor should ask for a hypothesis, recommend the next discriminating evidence, challenge unsupported rollback assumptions, and refuse requests for the hidden root cause. It may explain documented concepts with citations. After completion, it may reveal the reference root cause, compare the learner's decision with the rubric, and assign remediation on schema compatibility, observability, recovery, or incident command.

Deterministic engine results govern score and pass status. AI feedback cannot silently change evidence, authoritative answers, or competency records.

## Summary

Safe deployment recovery is a state-reconciliation problem. A build, runtime, database, media set, search projection, and external transaction flow can occupy different points in time. Expert operators preserve evidence, establish schema compatibility, respect managed-service boundaries, choose a recovery that protects business data, validate technical and transactional behavior, and improve the release system afterward. Rollback is a hypothesis that must be proved, not a reflex.

## Review questions

1. Why can a previous build fail after an apparently additive schema update?
2. What does deployment cancellation restore, and what work can remain?
3. Which observations distinguish failed activation from JVM pressure?
4. Why are payment and order reconciliation separate from application health?
5. When is SAP Support required rather than direct operator action?
6. What evidence makes a rollback or roll-forward decision defensible?

## References

- [RS-SAP-CLOUD-PORTAL] SAP Help Portal, *Cloud Portal*.
- [RS-SAP-DEPLOY-ROLLBACK] SAP Help Portal, *Deployment Rollback*.
- [RS-SAP-DATABASE-SERVICES] SAP Help Portal, *Database Services*.
- [RS-SAP-TYPE-SYSTEM-VERSIONING] SAP Help Portal, *Type System and Versioning*.
- [RS-SAP-ENV-LOGS] SAP Help Portal, *Accessing Environment Logs*.
- [RS-SAP-DYNATRACE-TROUBLESHOOT] SAP Help Portal, *Troubleshooting with Dynatrace*.
- [RS-SAP-DATA-BACKUP-RESTORE] SAP Help Portal, *Managing Data Backups and Restore Guidance*.
- [RS-SAP-CLUSTER-UPGRADE] SAP Help Portal, *Kubernetes Cluster Upgrade*.

All SAP-specific procedures must be rechecked against the active subscription, release, current documentation, and SAP Support guidance before production use.
