# M05 — OCC, REST APIs, OAuth, and API Contract Design

**Release:** 0.1.0 · **Status:** complete for milestone slice · **Competencies:** C-OCC-001, C-OCC-002

## Purpose

OCC is a public contract, not a thin serialization layer. This chapter teaches how to expose a use case through a versioned API while preserving authorization, validation, error semantics, compatibility, and testability.

## SAP-specific foundations

SAP documents OCC as a set of extensions providing commerce-driven REST web services. Its documented flow commonly passes from a controller to a facade, with DTOs and mappers at the web-service boundary [SAP-HELP-OCC-ARCH]. OCC exposes product, cart, order, search, stock, customer, promotions, and voucher functionality; custom functionality can be developed with the `yocc` template [SAP-HELP-OCC-FEATURES] [SAP-HELP-EXTENSION-TEMPLATES].

SAP documents OAuth 2.0 as the default authorization framework for commerce-driven OCC web services. That is a platform-specific statement for the cited 2211 scope; it is not permission to accept any token or to skip endpoint-level authorization [SAP-HELP-OCC-FEATURES]. SAP also warns that AddOn-based OCC v2 extensions are deprecated with a planned removal date; new designs must check the current supported extension path [SAP-HELP-OCC-ARCH].

### JDK 21 OAuth implementation boundary

“OAuth 2.0” names the protocol family, not one immutable Commerce extension. SAP's JDK 21 migration guide states that the legacy `oauth2` extension is removed and replaced by `authorizationserver`, `resourceserver`, and `oauth2commons`, following the move from the end-of-life Spring Security OAuth library to Spring Security/Spring Authorization Server [RS-SAP-HELP-OAUTH-MIGRATION]. Consequently, examples must declare whether they target a pre-JDK21 update or the JDK21 line. Copying bean names, grant configuration, token endpoints, or client-role assumptions across that boundary without migration evidence is unsafe.

The deprecation register also lists older Accelerator UI and OCC template/AddOn paths for planned removal and says new projects should not begin on deprecated components [RS-SAP-HELP-DEPRECATION]. The academy retains those patterns only for maintenance and modernization scenarios. Greenfield labs use current extension paths once their target update is established.

## Contract design

For each endpoint document:

- resource and use case owner;
- authentication and authorization policy;
- request validation and normalized errors;
- response schema and pagination;
- idempotency and concurrency behavior;
- cacheability and freshness;
- versioning/deprecation policy;
- audit and privacy fields;
- contract, integration, and security tests.

Example:

```http
GET /occ/v2/{baseSiteId}/products/{productCode}?fields=FULL
Authorization: Bearer <token>
```

The path is representative of OCC-style design, not a claim that this exact request is enabled in every project. Confirm the actual base site, fields, scopes, and supported endpoint in the targeted system.

## Security review

Authentication answers who the caller is; authorization answers what that caller may do. Never derive account ownership from a client-provided account code without a server-side authorization decision. Avoid returning internal identifiers, stack traces, payment secrets, or unrestricted customer attributes. Validate path, query, and body values before invoking a facade. Use consistent error shapes that do not leak existence when enumeration would be harmful.

## Compatibility and deprecation

An API contract evolves through additive fields, explicit deprecation, tolerant clients, and compatibility tests. Removing an AddOn path because documentation says it is deprecated is not itself a migration plan: identify consumers, supported replacement, rollout order, observability, and rollback.

## Guided lab — secure product endpoint

Design a product endpoint that returns a localized name, price, stock status, and catalog context. Provide the controller/facade boundary, DTO schema, authorization rule, validation errors, pagination strategy for related products, and five tests. **Acceptance:** no persistence model leaks into the contract; the learner cites OCC and OAuth sources; the simulation label remains explicit.

## Independent practice — order submission

Design `POST /orders` for a detached storefront. Address idempotency keys, duplicate requests, cart ownership, payment boundary, order state transitions, errors, retry behavior, and audit evidence. Defend what the API promises synchronously and what becomes asynchronous.

## API test matrix

| Concern | Test |
| --- | --- |
| Authentication | no token, expired token, wrong client |
| Authorization | other customer’s cart/order, B2B account mismatch |
| Validation | missing code, illegal quantity, unsupported currency |
| Contract | response fields, error schema, pagination |
| Reliability | timeout, retry, duplicate idempotency key |
| Security | injection-shaped input, enumeration, sensitive field exposure |

## References

- [SAP-HELP-OCC-FEATURES] OCC Features.
- [SAP-HELP-OCC-ARCH] OCC AddOn-based Architecture.
- [SAP-HELP-EXTENSION-TEMPLATES] Available Extension Templates.
- [SAP-HELP-CLOUD-PORTAL] Cloud Portal.
- [RS-SAP-HELP-OAUTH-MIGRATION] Moving to the New OAuth Implementation.
- [RS-SAP-HELP-DEPRECATION] Deprecation Status.
