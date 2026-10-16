# Current-state architecture inventory — 2026-10-16

## Evidence

The supplied workspace contained only `.` and had no Git metadata, source files, build files, tests, content, or ADR conventions. Searches for files and a Git status check returned no repository. Therefore no existing Athena Hub, AI Tutor, Forma, Java/Spring, frontend, API, AI provider, auth, persistence, progress, licensing, publication, or integration implementation was available to reuse or verify.

## Initial decisions

| Area | State | Decision |
| --- | --- | --- |
| Athena Hub / AI Tutor | unavailable | Define versioned contract only; no integration claim |
| Forma | unavailable | Do not create or misrepresent a storefront integration |
| SAP Commerce runtime | unavailable | Use clearly labeled deterministic simulation for practice |
| Content | missing | Create structured JSON/Markdown source of truth |
| Publication | missing | Add reproducible HTML + Pandoc PDF prototype |
| Persistence/auth/licensing | missing | Keep out of local vertical slice |
| AI provider | missing | Provide tutor contract and safe citation/abstention rules; no provider dependency |

## Implemented state after the Operations/SRE milestone

| Area | Verified state | Remaining boundary |
| --- | --- | --- |
| Learner service | Local Python HTTP service with module, assessment, tutor, progress, incident, and operations APIs | No production auth, tenant isolation, rate limiting, or hosted deployment |
| Persistence | SQLite assessment attempts, competency evidence, incident sessions, event streams, and results | Local single-user model only; migrations and retention policy need formalization |
| Ecosystem simulation | Four deterministic stateful scenarios - Composable Storefront stale price, Backoffice sync/index failure, failed deployment, and checkout/JDBC-pool contention - with progressive evidence, consequential actions, unsafe hard-fails, reset, scoring, coaching, and persisted evidence | Synthetic only; no claim of complete SAP, storefront, CDN, Backoffice, Dynatrace, database, or cloud runtime emulation |
| Deep practice | Fifteen operations exercises plus four developer testing exercises with seeded constraints, progressive hints, protected solutions, deterministic grading, separate competency evidence, and persisted assisted/independent evidence | Machine-validated only; no human educational or technical review; platform test plans unexecuted |
| Content | General 27-module roadmap plus Operations/SRE 60-module specialization roadmap | Eight general and two operations modules authored; all remain review-required |
| Publication | Reproducible HTML/PDF module generation and machine QA | Human technical/editorial/accessibility review pending |
| Athena Hub | Versioned boundary contract only | Host repository unavailable; no integration claim |
| Forma | Unavailable | No storefront connector created |
| SAP Commerce runtime | Unavailable | Code examples and operational behavior requiring a tenant remain unexecuted |

## Known research gaps

The source registry now distinguishes inspected official pages from restricted, historical, community, and independent sources. Current official pages for Composable Storefront, Backoffice, cloud operations, Dynatrace transaction/database diagnosis, CronJob aspect behavior, and SAP Commerce JUnit/JUnit 5 test infrastructure were inspected on 2026-10-16. Subscription-specific metric names, retention, permissions, restricted support content, and live-runtime validation remain explicit gaps.
