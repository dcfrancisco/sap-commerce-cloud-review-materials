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

## References

- [RS-SAP-BACKOFFICE] Backoffice Administration Cockpit.
- [RS-SAP-BACKEND-ADMIN] Backend Administration.
- [RS-SAP-HELP-SYNC] Synchronization in Backoffice.
- [RS-SAP-HELP-PLATFORM] Platform Implementation.
- [RS-SAP-COMM-CLEANUP] Community cleanup article; scenario source only.
