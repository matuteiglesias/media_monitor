# Documentation coverage and known gaps

> **Status:** canonical maintenance report · **Verified against:** `65e8c0d`

| Area | Coverage | Remaining gap |
|---|---|---|
| front doors | root and docs router | automated anchor checking is not implemented |
| architecture/authority | end-to-end, owners, state, identity, trust, ADR | diagrams are linted only for presence/context, not rendered |
| components/reference | four owners; commands/config/contracts/storage/status | catalogs are maintained manually |
| operations | six golden paths with reconciliation/recovery | AWS/Vercel examples lack provider execution evidence |
| case studies | AWS sensing and deterministic publication | operated outcomes unavailable |
| historical migration | classification index and PR-runbook banners | app/legacy/notes prose is preserved, not line-by-line rewritten |
| automated quality | relative links, metadata, PR-numbered canonical-name guard | external URLs and semantic claim drift are not automatically verified |

Known runtime/documentation debt remains visible: minimal-loop enrich references an absent script; aggregate site publication references absent npm scripts; acquire supporting runbook contains a stale pre-Terraform statement; full pytest collection includes legacy imports of absent `backend`. These require code or historical-migration decisions outside documentation semantics.
