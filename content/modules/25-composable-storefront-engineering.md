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

## 10. Release engineering: compatibility is a tested relation

Composable Storefront must be treated as a versioned application supply chain, not as a theme placed on any “2211” backend. SAP’s dependency matrix binds storefront update lines to Angular and Node.js lines [RS-SAP-CS-DEPS]. SAP’s release policy describes a roll-forward model and recommends aligning storefront and Commerce Cloud update releases [RS-SAP-CS-RELEASE-POLICY]. That recommendation is evidence to plan an upgrade; it is not evidence that a project’s customizations are compatible.

A release record should capture an immutable set rather than a floating statement:

```yaml
commerceCloudUpdate: 2211.<verified-update>
storefrontLibraries: 2211.<verified-compatible-update>
angular: <matrix-compatible-major-and-patch>
node: <matrix-compatible-major-and-patch>
packageLockDigest: sha256:<build-output>
occContractBaseline: storefront-api-<project-version>
featureLevel: <configured-value>
rendering: ssr-with-hydration
evidence:
  - dependency-matrix-snapshot
  - clean-install-build
  - contract-test-report
  - accessibility-report
  - browser-trace
```

The placeholders are intentional. A learning manual should not convert a version observed on the retrieval date into a permanent prescription. Before an implementation, verify the current matrix and the relevant release note, then pin the toolchain in source control and CI.

### Upgrade failure domains

| Boundary | Typical incompatibility | Required evidence |
| --- | --- | --- |
| Build | Angular compiler, TypeScript, Node, package peer dependency | clean locked install and production build |
| Bootstrap | NgModule-to-standalone changes, provider registration | cold start and route smoke tests |
| Library API | removed symbol or changed facade contract | compiler result and customization inventory |
| OCC | field, endpoint, auth, or error-contract drift | consumer-driven contract tests against target API |
| CMS | changed component type, slot, or mapping | page inventory and component fallback tests |
| SSR | server-only API use, transfer-state or hydration mismatch | rendered HTML, hydration console, duplicate-call trace |
| Accessibility | feature-level behavior affects custom components | keyboard, screen-reader, zoom, and automated scans |

Rollback is also relational. Reinstalling an earlier JavaScript bundle may be technically possible, but a CMS model, OCC contract, feature level, or edge-cache policy may already have changed. The release plan must state which boundaries remain backward compatible.

## 11. CMS-driven composition without surrendering engineering boundaries

The backend determines pages, slots, and component metadata; the Angular application maps component types to implementations. This makes composition configurable while preserving a compiled application boundary. A component mapping is not an authorization mechanism and CMS content is not trusted executable code.

```ts
type NoticeViewModel = Readonly<{
  heading: string;
  message: string;
  severity: 'info' | 'warning';
}>;

@Component({
  selector: 'academy-product-notice',
  template: `
    <aside *ngIf="vm$ | async as vm" [attr.aria-label]="vm.heading">
      <h2>{{ vm.heading }}</h2>
      <p>{{ vm.message }}</p>
    </aside>
  `
})
export class ProductNoticeComponent {
  readonly vm$ = this.cms.data$.pipe(
    map(data => validateAndMapNotice(data)),
    distinctUntilChanged()
  );

  constructor(private readonly cms: CmsComponentData<UnknownNoticeData>) {}
}
```

The example illustrates project-owned design principles rather than a guarantee about imports in every storefront release. The mapper rejects invalid shape, templates interpolate text rather than trusting arbitrary HTML, and the component exposes one observable view model. Verify exact package symbols against the target library.

For each override, maintain a customization ledger with the SAP component type, project component, reason, library version introduced, tests, accessibility owner, and retirement condition. Without that ledger, upgrades fail through forgotten substitutions rather than obvious compiler errors.

## 12. OCC, authentication, and browser trust

SAP describes composable storefront as using Commerce REST APIs for its backend communication [RS-SAP-GITHUB-SPARTACUS]. This separation creates useful test seams but does not make browser state authoritative.

- The browser can request a site, language, and currency context; the server validates what applies.
- UI route guards improve experience; API authorization enforces access.
- Tokens must use supported flows and central handling. Components should not copy tokens into logs, analytics, URLs, or local debug output.
- A cart identifier is not proof that the caller owns the cart.
- A displayed price is not the final order authority. Commerce must validate price, inventory, promotion, delivery, and payment conditions at the appropriate server boundary.
- A retry of a write is safe only when the contract defines duplicate behavior or an idempotency design controls it.

An interceptor can attach cross-cutting request metadata, but a retry interceptor must distinguish safe reads from business mutations. Automatically retrying add-to-cart, payment authorization, or place-order requests after an ambiguous timeout can duplicate effects.

## 13. SSR and cache mechanics

SAP’s SSR setup guidance describes a request path through an edge cache, reverse proxy, SSR node, optional OCC cache, and OCC server [RS-SAP-CS-SSR-SETUP]. This page is version-scoped; use it as an architectural reference and verify details against the selected release. The important diagnostic lesson is that each layer can hold a different representation.

```text
Browser
  -> CDN/edge object: route + site + language + currency + user class
  -> SSR process: route resolution and CMS/OCC reads
  -> transfer state embedded in HTML
  -> hydration: client adopts server DOM and state
  -> later navigation: client-side connector and state flow
```

A correct cache key must represent every request dimension that can change the response. Which dimensions belong in a key is project-specific, but common candidates include host/base site, path and query, language, currency, authorization class, experiment variant, and content release. Personalized pages should not become anonymously shared cache objects.

When an SSR page is stale but OCC is fresh:

1. Reproduce one exact context and preserve request/response timestamps.
2. Compare cold and warm requests.
3. Record edge age, vary behavior, cache key derivation, and release identifiers.
4. Inspect embedded transfer state before JavaScript changes it.
5. Compare initial hydration with client-side navigation.
6. Confirm cart and checkout authority separately.
7. Correct and invalidate the narrowest proven layer.
8. Watch origin load and error rate while repopulating.

“Clear all caches” discards causal evidence, can generate a thundering herd, and does not repair a defective key. It is therefore a prohibited expert action in the academy’s `ECO-CS-001` simulation.

## 14. Storefront observability and acceptance

Correlate browser navigation, SSR render, edge result, and OCC request without exposing personal or credential data. Useful events include route template, anonymized session class, site/language/currency, cache hit class, render duration, hydration duration, OCC operation, response class, and release identifier. High-cardinality product or customer identifiers require an explicit telemetry policy.

Recovery acceptance for a stale-render incident includes:

- anonymous cold SSR and warm cached SSR;
- at least two currencies or languages affected by the key design;
- hydration without DOM mismatch or duplicate API traffic;
- client-side navigation from listing to product detail;
- authenticated and anonymous cache separation;
- cart and checkout price recalculation;
- accessibility behavior after dynamic updates;
- cache repopulation load within its error and latency budget.

## 15. Stateful incident laboratory

Start `ECO-CS-001` through the local scenario API or learner UI. The simulator stores every investigation, action, tutor interaction, and conclusion. It reveals no reference root cause until submission. Unsafe actions remain disqualifying even if a later safe correction restores service.

Suggested sequence:

1. establish request context;
2. compare OCC and SSR;
3. inspect transfer state and unrelated service-worker evidence;
4. correlate release history;
5. establish cart/checkout authority;
6. freeze cache changes;
7. apply a bounded key correction or bounded rollback;
8. verify every rendering path;
9. submit a conclusion with impact, ownership, uncertainty, and prevention.

The exercise is a deterministic model, not a reproduction of SAP-managed infrastructure or a particular CDN. Its competency evidence is valid for academy practice; it is not proof of execution on a licensed runtime.

## References

- [RS-SAP-GITHUB-SPARTACUS] SAP Spartacus repository.
- [RS-SAP-CS-DEPS] Dependencies Matrix.
- [RS-SAP-CS-PERF] Performance Best Practices.
- [RS-SAP-CS-SSR-SETUP] Recommended Setup for Server-Side Rendering (version-scoped).
- [RS-SAP-CS-RELEASE-POLICY] Update Release Policy and Publication Frequency.
- [RS-SAP-CS-A11Y] Accessibility Rollout Phases.
- [RS-SAP-CS-FEATURE-FLAGS] Feature Levels and Feature Flags.
- [RS-SAP-CS-2211217] Update Release 221121.7.
