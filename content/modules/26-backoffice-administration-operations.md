# M26 — Backoffice and Administration Operations

**Release:** 0.2.0 research milestone · **Status:** implemented, technical/editorial/runtime review required · **Competencies:** C-ADMIN-001, C-ADMIN-002, C-ADMIN-003

## Purpose and safety boundary

This module teaches evidence-driven administration across Backoffice and the Administration Console/HAC. No live SAP Commerce tenant is available. All administrative practice is design- or simulation-based; learners must never run destructive ImpEx, scripting, initialization, cache, or data operations against production without approved authorization, backups, peer review, and a tested runbook.

## Outcomes

Learners can distinguish Backoffice from HAC responsibilities, apply least privilege, prepare a safe change, investigate catalog synchronization, review CronJob evidence, and construct rollback and audit records.

## 1. Tool responsibilities

SAP describes Backoffice as a browser-based interface for viewing, creating, and manipulating Commerce data, organized through widgets and perspectives. It can manage catalog/product data, users, roles, permissions, prices, internationalization, and system data [RS-SAP-BACKOFFICE]. SAP’s backend-administration index distinguishes the Administration Console from Backoffice and notes that backend endpoints are configured through Cloud Portal [RS-SAP-BACKEND-ADMIN].

Use Backoffice for governed business and platform administration exposed through configured types and workflows. Use HAC for narrowly authorized platform diagnostics and operations. Neither tool is a shortcut around change control.

## 2. Administrative risk classes

| Class | Examples | Required safeguards |
| --- | --- | --- |
| Read-only | inspect item, query, log, CronJob status | scoped account, query limits, evidence retention |
| Reversible configuration | change scheduled trigger, feature configuration | peer review, before/after export, rollback |
| Data mutation | ImpEx import, bulk edit, sync | validated input, backup, dry run/lower environment, reconciliation |
| High-impact platform | initialization, scripts, cache/system operations | explicit production approval, maintenance plan, recovery evidence |

This risk model is academy guidance. Exact permissions and operational procedures depend on the customer’s controls and SAP service boundary.

## 3. FlexibleSearch and ImpEx safety

Start with a bounded read query and explicit result limit. Confirm catalog version, site, language, and tenant. Avoid selecting broad object graphs merely to inspect one invariant. For an import, validate headers, unique keys, reference resolution, locale, update semantics, and expected rejects. Preserve the source file, validation report, operator, timestamp, and affected identifiers.

Never enable code execution in an ImpEx or scripting console merely because a community article uses it. Community cleanup recipes are scenario ideas only and are explicitly non-authoritative [RS-SAP-COMM-CLEANUP].

## 4. Catalog synchronization investigation

SAP defines synchronization as transferring items between catalog versions and documents Staged/Online administration through Backoffice [RS-SAP-HELP-SYNC]. A “successful” synchronization job does not prove storefront correctness. Investigate:

1. source and target catalog versions;
2. item approval/visibility state;
3. sync job result and unresolved dependencies;
4. target item timestamps and relations;
5. search indexing after synchronization;
6. OCC/site context;
7. storefront or CDN/browser caches.

The diagnostic chain prevents an administrator from repeatedly rerunning sync when the stale layer is actually search or storefront state.

## 5. CronJobs and processes

SAP documents business process management as using task, CronJob, and process-engine services [RS-SAP-HELP-PLATFORM]. For a repeatedly failing job, record job definition, trigger, node group, last result/status, retry count, logs, input batch, and downstream dependency health. Pausing a trigger may stop further damage, but it does not repair partially processed data.

## 6. Permissions and audit

Separate product editors, catalog managers, order-support users, security administrators, and platform operators. Test denial as well as success. A role should not receive HAC/script capability solely because it needs Backoffice catalog access. Audit records should identify who changed what, when, under which approved request, and how the result was verified.

## 7. Backoffice customization boundary

Custom widgets and editor configuration can improve workflows but add upgrade and authorization responsibilities. Validate widget visibility, type permissions, action permissions, localization, input validation, and behavior with large result sets. A hidden button is not authorization; enforce access below the UI.

## Guided practice — synchronization completed, storefront stale

Use `LAB-M26-SYNC-STALE`. The evidence includes a completed sync result, target item timestamp, missing index update, OCC response, and storefront cache state. Identify the stale boundary and sequence safe corrective actions. Acceptance requires preserving evidence, avoiding blind re-sync/cache flush, and verifying Backoffice, search, OCC, and storefront independently.

## Independent practice — production ImpEx review

Review a proposed bulk price import. Produce a risk classification, unique-key validation plan, lower-environment evidence, backup/rollback plan, reject handling, operator permissions, and post-import reconciliation. Do not execute it.

## Assessment and remediation

Assessment items test tool selection, least privilege, sync diagnosis, CronJob recovery, and dangerous-operation review. Failed evidence assigns targeted rereading and a new scenario with changed catalog/search conditions.

## 8. Administration is a chain of state transitions

An administrator should never collapse “saved,” “synchronized,” “indexed,” “returned by an API,” and “rendered by the storefront” into one success state. They are separate transitions with distinct evidence:

```text
Staged item approved
  -> synchronization job selects and copies data
  -> Online item and relations are valid
  -> index job selects Online data
  -> value resolvers create a search document
  -> active index exposes that document
  -> OCC search applies site, catalog, language, currency, and permissions
  -> storefront renders and caches the response
```

SAP documents Staged-to-Online synchronization and Backoffice process visibility [RS-SAP-HELP-SYNC]. SAP also documents Backoffice editors for Solr server, indexer, and search configuration [RS-SAP-HELP-SOLR-CONFIG]. These facts support the boundaries. The exact project job names, custom resolvers, data values, and log messages in the academy are simulated.

### Boundary evidence table

| Claim | Minimum evidence | What it does not prove |
| --- | --- | --- |
| Item saved | identifier, catalog version, modified time, validation state | synchronization completed |
| Sync succeeded | job, source/target, scope, result, unresolved items | search index contains the item |
| Online item exists | attributes and required relations in target version | visibility or index document correctness |
| Index succeeded | job result, counts, failed identifiers, active index | every user may see the item |
| Search returns item | exact query and user/site context | direct-detail authorization is correct |
| Storefront displays item | response and render evidence | all locales, users, and cache paths are correct |

This table is also an audit template. Each operational conclusion should name the strongest proven boundary and the next unproven boundary.

## 9. HAC safety and bounded diagnostics

HAC is a high-impact administration and diagnostic surface. Access must be separated from ordinary catalog administration. The academy does not execute HAC scripts, FlexibleSearch mutations, imports, initialization, or cache operations.

A safe read-only diagnostic request should specify:

- authorized operator and change/incident record;
- business question and expected result shape;
- exact tenant and environment;
- catalog version and language where applicable;
- bounded predicate and result limit;
- execution-time and database-load guardrails;
- treatment of customer or credential data in outputs;
- evidence retention and deletion policy.

For example, “find product ACME-200 in Online” is a bounded question. “Select all products and all relations so we can inspect them” is not. FlexibleSearch is translated to database queries by the platform; it does not remove the need to reason about cardinality and indexes.

Initialization is a lifecycle operation, not a troubleshooting shortcut. It must never appear in a production recovery runbook for a missing product, failed CronJob, stale cache, or indexing defect.

## 10. ImpEx and mass-change control

ImpEx can express powerful, repeatable data changes, but textual repeatability does not imply business idempotency. A production review should answer:

1. Which header mode and unique keys determine insert/update behavior?
2. Which catalog version, locale, currency, and units are explicit?
3. How are unresolved references and rejected lines handled?
4. Could concurrent edits or jobs race with the import?
5. What exact records change, and how is that count predicted?
6. What backup or compensating change restores the prior business state?
7. Which downstream sync, index, cache, or integration steps follow?
8. Which independent queries and user journeys prove success?

A suitable dry-run artifact contains sanitized input, expected affected keys, validation output, rejection expectations, duration, resource observations, and reconciliation queries. Do not place real secrets or customer data in academy submissions.

The `ECO-ADMIN-001` scenario includes a failed classification-unit migration. Its lesson is not that one particular message is universal; it is that reject handling must feed a publication-readiness gate. A sync can transfer invalid-but-stored data, while a downstream index resolver rejects it.

## 11. Search administration and visibility

SAP documents search and indexer configuration through Backoffice [RS-SAP-HELP-SOLR-CONFIG]. SAP also documents a catalog-version visibility configuration in which indexed fields and search restrictions need consistent treatment [RS-SAP-HELP-SOLR-VISIBILITY]. Do not generalize that specific configuration into a universal project setup, but retain the engineering principle: projection-time authorization fields and request-time restrictions must agree.

For a missing search result, use this order:

1. Reproduce the exact query and principal context.
2. Prove the Online source item and required relations.
3. Inspect the most recent relevant index job and counts.
4. Locate item-specific resolver or selection failures.
5. Inspect active index/document state using authorized tooling.
6. Compare visibility fields and search restrictions.
7. Correct source data or configuration through governed change.
8. Run the narrowest supported index operation.
9. Verify detail and search paths independently.

Increasing a timeout, launching a full index, rerunning full synchronization, or disabling restrictions before localizing the fault can increase impact or create a security defect.

## 12. CronJob and process recovery

Before retrying a partially completed job, classify its work:

- **Read-only:** retry may be operationally safe, but repeated load still matters.
- **Idempotent mutation:** replay produces the same business result when the idempotency assumptions hold.
- **Deduplicated mutation:** a durable key prevents duplicate effects.
- **At-least-once side effect:** reconciliation is required before retry.
- **Unknown:** stop automatic retries and investigate state.

Record selected inputs, completed identifiers, failure point, external calls, retry counter, node/worker evidence, and downstream state. A trigger pause is containment, not recovery. Recovery includes reconciliation and acceptance testing.

## 13. Backoffice customization and authorization testing

Backoffice widgets and editor configuration can guide an operator, but visual absence is not security. Test permissions at the platform/service boundary and with negative cases:

- a product editor can modify approved product fields but not user roles;
- a catalog manager can synchronize an assigned catalog but not unrelated catalogs;
- order support can inspect an order without gaining script execution;
- a custom action rejects direct invocation by an unauthorized principal;
- exports respect field-level sensitivity and retention policy;
- bulk actions maintain the same authorization rules as single-item actions.

Performance tests should include realistic collection sizes. A widget that loads an unbounded relation or performs one query per row can turn a convenience customization into an administration outage.

## 14. Stateful administration incident laboratory

`ECO-ADMIN-001` promotes the guided scenario into a persisted investigation. It contains seven evidence requests and seven actions. Learners must distinguish sync from indexing, inspect a product-specific failure, protect visibility semantics, apply a governed bounded correction, and verify all paths. Blind full synchronization, initialization, and disabling visibility restrictions are prohibited and disqualify an expert pass.

The tutor reveals questions and citations, not the stored solution. Submission generates deterministic scores for triage, diagnosis, risk, recovery, integrity, verification, communication, root cause, and prevention. Evidence is recorded against `C-ADMIN-001` through `C-ADMIN-003`; a learner can reset and retest, but the earlier attempt remains separate from authoritative content.

## 15. Operational runbook outline

For a “sync succeeded, search stale” runbook, include:

1. scope and safety classification;
2. required Backoffice/HAC/search roles;
3. site/catalog/version/principal capture;
4. synchronization evidence query;
5. Online item and relation checks;
6. index job and failed-item checks;
7. visibility consistency checks;
8. approved correction options and rollback;
9. bounded index action;
10. product detail, search, authorization, and storefront acceptance;
11. monitoring period and incident closure evidence;
12. escalation package when managed-service support is required.

The runbook must identify which steps are customer administration, project-code remediation, managed-service support, or shared responsibility. It must not instruct direct database modification.

## References

- [RS-SAP-BACKOFFICE] Backoffice Administration Cockpit.
- [RS-SAP-BACKEND-ADMIN] Backend Administration.
- [RS-SAP-HELP-SYNC] Synchronization in Backoffice.
- [RS-SAP-HELP-SOLR-CONFIG] Define Search and Indexer Configuration.
- [RS-SAP-HELP-SOLR-VISIBILITY] Catalog-version visibility with Solr.
- [RS-SAP-HELP-PLATFORM] Platform Implementation.
- [RS-SAP-COMM-CLEANUP] Community cleanup article; scenario source only.
