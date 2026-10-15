# M01 — SAP Commerce Cloud Architecture and Fundamentals

**Release:** 0.1.0 · **Status:** published vertical-slice module · **Competencies:** C-ARCH-001, C-ARCH-002, C-ARCH-003

## Purpose and scope

This module establishes the mental model needed to reason about an SAP Commerce Cloud solution without confusing a platform capability with an application customization or an external system. It is an original teaching manual. It does not reproduce SAP course text and it does not claim to describe every version-specific runtime detail.

The module is deliberately boundary-first: before writing a service, an engineer should be able to name the owning boundary, the data it controls, the consistency it promises, and the evidence that would prove the behavior works.

## Learning outcomes

By the end, a learner can:

1. Explain why commerce architecture is a set of collaborating boundaries rather than a single storefront.
2. Trace a read request from an API edge through application services to a catalog projection.
3. Separate verified SAP facts, engineering interpretation, and simulation-only behavior.
4. design a small product-query change with explicit failure and observability behavior.
5. investigate a stale-catalog symptom using evidence instead of guessing.

**Prerequisites:** intermediate Java, Spring, HTTP, SQL, and basic distributed-systems vocabulary. SAP’s current learning-journey page lists intermediate Java/J2EE and Spring knowledge as a prerequisite [SAP-LEARN-JOURNEY-IMPLEMENT].

## 1. A boundary model for commerce engineering

An online order crosses more boundaries than the browser suggests. A useful working model is:

```text
shopper/browser
      | HTTPS
      v
API / storefront boundary ---- identity and input policy
      |
      v
application boundary ---------- use cases and orchestration
      |
      +--> catalog/search projection
      +--> cart and order state
      +--> pricing and promotion decisions
      +--> customer/account context
      |
      v
platform persistence + processes + events
      |
      +--> ERP / payment / tax / fulfillment integrations
```

This is a reasoning diagram, not a claim that every deployment has exactly these processes. The engineering question is not “which class handles products?” but “which boundary owns the truth, which boundary exposes a projection, and what happens when they disagree?”

SAP’s official technical essentials course explicitly groups foundational learning around configuration, data modeling, product modeling, import/export, FlexibleSearch, services, and facades [SAP-LEARN-TECH-ESSENTIALS]. The teaching sequence here uses those topics as a coherent request path rather than isolated vocabulary.

### Verified fact, interpretation, and simulation

Use three labels in design notes:

| Label | Meaning | Example |
| --- | --- | --- |
| Verified SAP | Supported by a current SAP source record | SAP publishes a course covering services and facades |
| Engineering interpretation | An original explanation or recommended design | Keep orchestration out of a DTO mapper |
| Simulation-only | Behavior implemented for practice | The local lab injects a deterministic catalog delay |

The local simulation intentionally does not reproduce the SAP Commerce runtime, extension framework, persistence engine, cloud deployment, or Backoffice. It gives a safe state machine for practicing evidence collection.

## 2. Request tracing and ownership

For a product detail request, write a trace before writing code:

```text
GET /products/P100
  -> authenticate / authorize
  -> resolve site, catalog version, language, currency
  -> choose product read use case
  -> obtain product projection
  -> map internal data to API representation
  -> emit correlation id, latency, result status
```

The important design distinction is between an internal model and an API representation. A public response should not accidentally expose internal persistence fields, mutable relations, or secrets. The conversion boundary should also be testable without requiring the entire platform.

A failure taxonomy makes the trace operationally useful:

| Failure | Likely boundary | Evidence to request |
| --- | --- | --- |
| 401/403 | identity or authorization | subject, roles, policy decision |
| 404 for known product | catalog/site/version projection | catalog version, index timestamp, product identifier |
| 409 on write | state or concurrency rule | entity version, idempotency key, transition log |
| 5xx with timeout | downstream or overloaded dependency | correlation id, timeout budget, dependency latency |
| correct item, stale price | projection or cache | price source timestamp, cache key, invalidation event |

## 3. Practical architecture heuristic

For each proposed change, record five decisions:

1. **Owner:** which component owns the invariant?
2. **Boundary:** which interface is allowed to call it?
3. **Consistency:** what must be immediately consistent and what may converge?
4. **Failure:** how does the caller learn that the operation did not complete?
5. **Evidence:** which test, log, metric, or trace proves the intended behavior?

Example: “show a newly approved product in search.” Product approval may update a source model, then a search projection. If the projection is asynchronous, immediate product retrieval and search visibility have different consistency contracts. A good incident report records both timestamps instead of declaring one system “wrong.”

## 4. Worked example: product read boundary

The following Java-like example is intentionally framework-neutral. It demonstrates dependency direction and a stable output contract; it is not presented as a drop-in SAP Commerce class.

```java
public final class ProductQueryService {
    private final ProductProjectionRepository products;
    private final ProductViewMapper mapper;

    public ProductQueryService(ProductProjectionRepository products,
                               ProductViewMapper mapper) {
        this.products = products;
        this.mapper = mapper;
    }

    public ProductView find(String code, QueryContext context) {
        ProductProjection product = products.findVisible(code, context)
            .orElseThrow(() -> new ProductNotFound(code));
        return mapper.toView(product, context);
    }
}
```

The useful properties are not the syntax: the query has an explicit context, visibility is decided by the owning repository/use case, mapping is a separate concern, and “not found” is a meaningful domain outcome. Production code must adapt these ideas to the actual platform version and supported extension contracts.

## 5. Operations and security

Architecture is incomplete without runtime behavior. A minimum product-read trace should carry a correlation identifier, outcome, duration, site/catalog context, and a non-sensitive product identifier. Do not log access tokens, full payment data, or unrestricted customer payloads. Treat catalog content, imported files, and learner-submitted code as untrusted input.

For a real deployment, verify current SAP cloud, security, and API behavior in the applicable SAP Help documentation before converting a recommendation into a platform-specific implementation. The public-cloud Help Portal and Composable Storefront links are registered but marked `research-gap` in this release because the portal pages did not expose their content to the retrieval client [SAP-HELP-COMMERCE-PUBLIC] [SAP-HELP-COMPOSABLE].

## 6. Guided practice — trace a catalog read

**Objective:** use an observable request trace to distinguish a missing source product from a stale projection.

**Initial state:** run the local server. The simulation contains `P100` in the source catalog and a current read projection.

**Steps:**

1. `curl http://127.0.0.1:8000/api/simulation/products/P100`
2. Record the returned `correlationId`, `sourceUpdatedAt`, and `projectionUpdatedAt`.
3. Call `POST /api/simulation/scenarios/stale-projection`.
4. Repeat the product request and compare timestamps and `diagnostics`.
5. Write a short incident explanation naming the failing boundary and one safe remediation.

**Acceptance criteria:** the learner identifies projection staleness from evidence, does not call the source product missing, and proposes reindex/reprojection or a bounded fallback according to the scenario contract. The simulation is not proof of SAP runtime behavior.

**Failure cases:** unknown product returns a structured 404; stale projection returns 200 with a diagnostic marker; malformed scenario requests return 400.

**Cleanup:** `POST /api/simulation/reset`.

## 7. Independent practice — choose a consistency contract

Design an approval flow where a product becomes purchasable before it becomes searchable. State the owner of each invariant, the API response semantics, retry/idempotency strategy, and three metrics. Do not assume synchronous search indexing. Your answer is evaluated against the rubric in the assessment item `M01-ARCH-008`.

## 8. Diagnostic walkthrough

Symptom: a product detail endpoint returns the updated name, but search still shows the previous name.

1. Confirm both calls use the same site, catalog, language, and currency context.
2. Compare source update time with projection/index update time.
3. Check whether the search projection consumed the update event.
4. Check retry and dead-letter evidence before replaying anything.
5. Replay idempotently, then verify both read paths independently.

The anti-pattern is to flush caches or restart services before establishing which projection is stale. Those actions can destroy evidence and may not repair a failed synchronization.

## 9. Review questions

- Which boundary owns “product is purchasable,” and why might search not own that invariant?
- What is the difference between an API DTO and a persistence model?
- Which evidence separates a 404 caused by an unknown code from a 404 caused by catalog context?
- When is eventual consistency acceptable for a commerce projection?
- Which technical claims in this module require a version-specific SAP source check?

## Summary

Senior commerce engineering begins with boundaries, ownership, consistency, and evidence. The official SAP learning references anchor the subject areas; this module supplies original reasoning patterns, a safe simulation, and competency evidence. The next modules will deepen the specific platform mechanisms only after their applicable sources are verified.

## References

- [SAP-LEARN-JOURNEY-IMPLEMENT] Implementing SAP Commerce Cloud — official learning journey.
- [SAP-LEARN-TECH-ESSENTIALS] Exploring the Technical Essentials of SAP Commerce Cloud — official course.
- [SAP-HELP-COMMERCE-PUBLIC] SAP Commerce Cloud Public Cloud documentation — source record currently marked research gap.
- [SAP-HELP-COMPOSABLE] SAP Commerce Composable Storefront documentation — source record currently marked research gap.
