# M27 — Cloud Operations and Incident Management

**Release:** 0.2.0 research milestone · **Status:** implemented, technical/editorial/runtime review required · **Competencies:** C-OPS-001, C-OPS-002, C-OPS-003

## Purpose and responsibility boundary

This module prepares Cloud Portal administrators and production engineers to investigate deployments, logs, telemetry, and recovery without pretending they control SAP-managed infrastructure. No Cloud Portal subscription or production environment is available; the lab uses synthetic evidence derived from official operational documentation.

## Outcomes

Learners can trace a failed deployment, query application logs safely, correlate storefront and backend symptoms, choose rollback/redeploy/restore actions, explain the managed-service boundary, and write an incident review.

## 1. Cloud operational model

Cloud Portal exposes environment, build, deployment, endpoint, security, log, and backup/restore workflows [SAP-HELP-CLOUD-PORTAL]. Customers own custom code, selected versions/extensions, configuration, data changes, validation, and release decisions. SAP operates provider-managed infrastructure and performs activities such as Kubernetes cluster upgrades [RS-SAP-CLUSTER-UPGRADE]. Do not teach direct node, control-plane, or provider-account access as a customer capability.

## 2. Evidence before action

Create an incident timeline containing deployment/build ID, source revision, environment, database action, endpoint health, first error, affected user journey, correlation IDs, OpenSearch queries, Dynatrace problem window, and operator actions. Preserve evidence before restarts or broad cache changes.

SAP documents access to environment logs through the Cloud Portal Monitoring panel and OpenSearch, including `logs-json-*` and filters for Commerce Tomcat logs [RS-SAP-ENV-LOGS]. Platform logging supports Log4j2/SLF4J and JSON-formatted JDBC and access logs [RS-SAP-PLATFORM-LOGGING]. Never log tokens, passwords, payment data, or unrestricted personal data.

## 3. Observability workflow

```text
customer symptom
  -> endpoint and journey scope
  -> deployment/change timeline
  -> OpenSearch errors and correlation IDs
  -> Dynatrace problem/service flow/database evidence
  -> application invariant and downstream dependency
  -> bounded mitigation
  -> independent acceptance checks
```

SAP’s Dynatrace guide covers services, transactions, database behavior, performance, and issue analysis [RS-SAP-DYNATRACE]. Availability of individual features can depend on environment enablement; missing telemetry is itself a readiness gap, not proof that the component is healthy.

## 4. Deployment and rollback semantics

SAP’s rollback guidance distinguishes cancellation during deployment, backup/restore, build compatibility, patch-version builds, and recovery after failed schema migration [RS-SAP-DEPLOY-ROLLBACK]. Cancelling can leave application services requiring a successful deployment. A previous application build may be incompatible after schema changes. Therefore “redeploy the old build” is not a universal rollback plan.

A release plan must state:

- database mode and expected schema changes;
- backward compatibility of current and previous builds;
- backup age and restoration scope;
- media and search-index recovery steps;
- maintenance page and traffic strategy;
- smoke, data, integration, and business acceptance checks;
- escalation to SAP Support where managed components are involved.

## 5. Incident scenario — deployment succeeds, checkout fails

Initial evidence: Cloud Portal reports deployment success; health endpoint responds; checkout latency rises; OpenSearch shows downstream timeouts; Dynatrace service flow attributes most duration to a tax integration; order creation has mixed outcomes. The safe response is not an immediate database restore. First stop duplicate submissions, establish idempotency behavior, evaluate downstream health, protect order integrity, and choose a bounded feature/configuration mitigation.

## 6. Backup and recovery reasoning

Recovery is a business operation, not just a button. Determine recovery point, database/media consistency, credentials, external integrations, Solr reconstruction, and post-restore reconciliation. A restored Commerce database does not automatically restore every external system’s state. Validate catalog/search, customer access, carts, orders, integrations, and monitoring after recovery.

## 7. Managed maintenance

SAP documents cluster upgrades as SAP-managed operations with possible disruption or degradation for services such as CronJobs, Backoffice, storefront, and monitoring [RS-SAP-CLUSTER-UPGRADE]. Operational readiness therefore includes notification handling, blackout/change coordination, retry-safe jobs, saved administrative work, and validation after the activity.

## Guided incident lab

Use `LAB-M27-FAILED-DEPLOYMENT`. Evidence is disclosed in stages: deployment metadata, startup logs, OpenSearch events, Dynatrace service flow, database mode, and recovery options. The learner must request evidence, form and revise hypotheses, choose safe mitigation, define acceptance tests, and produce root cause/prevention sections.

## Independent practice

Write a runbook for a certificate or credential expiry that breaks storefront-to-OCC connectivity. Include detection, ownership, secret rotation boundary, rollback, cache/session considerations, validation, communications, and audit evidence. Do not include real secrets.

## Tutor behavior

The tutor presents one evidence stage at a time, rejects unsupported certainty, penalizes destructive actions without prerequisites, asks for rollback conditions, and grades the investigation against evidence use, safety, diagnosis, recovery, verification, and prevention—not keyword overlap.

## References

- [SAP-HELP-CLOUD-PORTAL] Cloud Portal.
- [RS-SAP-ENV-LOGS] Accessing Environment Logs.
- [RS-SAP-PLATFORM-LOGGING] Logging.
- [RS-SAP-DYNATRACE] Dynatrace Feature Guide for SAP Commerce.
- [RS-SAP-DEPLOY-ROLLBACK] Deployment Rollback.
- [RS-SAP-CLUSTER-UPGRADE] Kubernetes Cluster Upgrade.
