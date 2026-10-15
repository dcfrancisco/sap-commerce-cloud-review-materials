# M25 — Composable Storefront / Spartacus Engineering

**Release:** 0.2.0 research milestone · **Status:** implemented, technical/editorial/runtime review required · **Competencies:** C-CS-001, C-CS-002, C-CS-003

## Purpose and scope

This vertical slice establishes Composable Storefront as a first-class engineering discipline. It covers version compatibility, architecture, CMS mapping, OCC boundaries, RxJS-oriented state flow, accessibility, SSR/hydration, performance, testing, and incident diagnosis. No licensed SAP storefront package or live Commerce backend is present, so code is reviewable but not claimed as executed against SAP Commerce Cloud.

## Learning outcomes

Learners can select a compatible storefront toolchain, trace a product request from route to OCC response, design a CMS component customization, review authentication boundaries, diagnose stale storefront data, and construct an upgrade test plan.

## 1. Product and version boundaries

“Spartacus” does not identify one interchangeable runtime. SAP’s open-source repository explains that supported Composable Storefront libraries use the SAP Commerce Cloud product name, while open-source Spartacus remains a separate boundary. It also states that version numbering aligns with Commerce Cloud beginning at 2211.19 [RS-SAP-GITHUB-SPARTACUS].

The official dependencies matrix maps each storefront release to specific Angular and Node.js versions and states that open-source 4.x and earlier are unsupported [RS-SAP-CS-DEPS]. The current matrix retrieved for this release includes major jumps from Angular 17 to 19 and then 21. Therefore every project record must include:

- storefront package version;
- Commerce Cloud update line;
- Angular, Node.js, TypeScript, and package-manager versions;
- supported OCC/API compatibility;
- enabled feature level and flags;
- SSR and deployment mode;
- browser and accessibility support targets.

Do not write “2211 compatible” without the update and dependency evidence.

## 2. Runtime request architecture

```text
Browser route
  -> Angular router and guards
  -> page/layout and CMS component mapping
  -> storefront facade/service
  -> state/effect or direct connector
  -> OCC adapter/connector
  -> Commerce REST API
  -> normalized state/selectors
  -> component view model
```

This is a teaching model; exact state libraries and APIs vary by storefront release. Components should consume a stable facade or observable view model rather than constructing OCC URLs or owning token logic. API adapters translate external contracts. Effects coordinate asynchronous work. Selectors derive state without side effects.

## 3. Configuration example

The following TypeScript demonstrates the shape of explicit configuration. It is not executed here and package APIs must be verified for the selected release.

```ts
export const commerceConfig = {
  backend: {
    occ: {
      baseUrl: 'https://commerce.example.invalid',
      prefix: '/occ/v2/'
    }
  },
  context: {
    baseSite: ['electronics'],
    currency: ['USD'],
    language: ['en']
  }
};
```

Environment-specific endpoints belong in deployment configuration. Never put production client secrets in browser-delivered configuration. Browser applications are public clients; authorization decisions remain server-side.

## 4. CMS component mapping

```ts
export const cmsConfig = {
  cmsComponents: {
    AcademyProductNoticeComponent: {
      component: ProductNoticeComponent
    }
  }
};
```

A robust component validates nullable CMS data, exposes semantic HTML, supports localization, handles loading/error/empty states, and does not trust CMS strings as safe HTML. A component override creates an upgrade obligation: record the original behavior, selector/template assumptions, accessibility contract, tests, and feature-level dependency.

## 5. RxJS and state discipline

Prefer an observable view model that has one clear lifecycle. Avoid nested subscriptions, mutation inside selectors, and effects that silently swallow failures. For cart mutations, include duplicate-action protection and show whether the server accepted, rejected, or partially completed the operation. Authentication expiration should route through a central policy rather than each component retrying independently.

## 6. SSR, hydration, SEO, and performance

SAP’s performance guidance recommends lazy loading, SSR transfer state to avoid duplicate requests, SEO metadata, service-worker/PWA configuration where appropriate, and resource integrity controls [RS-SAP-CS-PERF]. The 221121.7 update guidance requires Angular 21 and Node.js 22, describes standalone bootstrap modernization, and requires non-destructive hydration for SSR projects [RS-SAP-CS-2211217]. These are version-specific requirements—not universal instructions for older applications.

Measure server-render latency, client hydration duration, JavaScript transferred, duplicate OCC calls, Core Web Vitals, cache behavior, and error rate. A fast synthetic home page is insufficient if authenticated checkout regresses.

## 7. Accessibility and feature rollout

SAP documents phased rollout for accessibility changes beginning with 2211.23 [RS-SAP-CS-A11Y]. Custom components remain the project’s responsibility. Test keyboard traversal, focus restoration after navigation, 200% zoom, screen-reader labels, validation errors, live regions, color contrast, and reduced motion. Feature levels and flags support controlled adoption but do not replace regression testing [RS-SAP-CS-FEATURE-FLAGS].

## 8. Testing strategy

- Unit: pure mappers, guards, facades, selectors, and error policies.
- Component: input states, semantic output, keyboard behavior, and CMS data.
- Contract: OCC request paths, headers, query options, and response mapping.
- Integration: auth expiration, cart mutation, locale/site changes, and SSR transfer state.
- Browser E2E: search → product → cart → checkout boundary, with accessibility scans and traces.
- Performance: budgets for initial JavaScript, LCP, CLS, interaction latency, and OCC duplication.

## 9. Incident walkthrough — stale price

Symptom: product detail shows an old price after Backoffice displays a new value. Determine whether the stale value originates in Commerce pricing, OCC response, intermediary caching, SSR transfer state, browser service worker, or client state. Capture the product/site/currency context and correlation evidence at each boundary. Do not “clear every cache” before localizing the stale layer.

## Guided practice

Use `LAB-M25-STOREFRONT-STALE-PRICE`. Inspect a staged evidence bundle containing an OCC response, SSR snapshot, client state timestamp, and service-worker cache record. Identify the first stale boundary, propose the smallest safe corrective action, and define regression tests.

## Independent practice

Create an upgrade decision record from a 6.x storefront to a current 2211-aligned release. Include dependency hops, Angular/Node migration, custom component inventory, OCC compatibility, accessibility flags, SSR/hydration, rollback, and release evidence.

## References

- [RS-SAP-GITHUB-SPARTACUS] SAP Spartacus repository.
- [RS-SAP-CS-DEPS] Dependencies Matrix.
- [RS-SAP-CS-PERF] Performance Best Practices.
- [RS-SAP-CS-A11Y] Accessibility Rollout Phases.
- [RS-SAP-CS-FEATURE-FLAGS] Feature Levels and Feature Flags.
- [RS-SAP-CS-2211217] Update Release 221121.7.
