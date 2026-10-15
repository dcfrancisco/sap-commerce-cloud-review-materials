# Current-state architecture inventory — 2026-10-16

## Evidence

The supplied workspace contained only `.` and had no Git metadata, source files, build files, tests, content, or ADR conventions. Searches for files and a Git status check returned no repository. Therefore no existing Athena Hub, AI Tutor, Forma, Java/Spring, frontend, API, AI provider, auth, persistence, progress, licensing, publication, or integration implementation was available to reuse or verify.

## Decisions

| Area | State | Decision |
| --- | --- | --- |
| Athena Hub / AI Tutor | unavailable | Define versioned contract only; no integration claim |
| Forma | unavailable | Do not create or misrepresent a storefront integration |
| SAP Commerce runtime | unavailable | Use clearly labeled deterministic simulation for practice |
| Content | missing | Create structured JSON/Markdown source of truth |
| Publication | missing | Add reproducible HTML + Pandoc PDF prototype |
| Persistence/auth/licensing | missing | Keep out of local vertical slice |
| AI provider | missing | Provide tutor contract and safe citation/abstention rules; no provider dependency |

## Known research gaps

The official SAP Learning pages were reachable and their visible metadata was recorded in `content/sources.json`. The SAP Help Portal links were reachable as URLs but did not expose document content to the retrieval client, so they remain `research-gap`; no unsupported Help Portal claims are treated as verified.
