# Media Monitor procurement and trust packet

> **Status:** technical diligence summary · not a contract, license grant, SLA, privacy addendum, warranty, certification, or security audit

Machine-readable authority: [`procurement_trust_state.yaml`](procurement_trust_state.yaml).

This packet exists so an evaluator can understand what is already evidenced, what is merely an implementation target, and what still requires an explicit human/legal/commercial decision without reading the whole repository.

## Executive status

| Area | Current evidenced state | Before contractual adoption |
| --- | --- | --- |
| Repository | Public GitHub repository | Repository/software licensing **not chosen** |
| Scheduled production | GitHub Actions workflow exists; hourly cron at minute 45; 25-minute timeout | Scheduler hardening/cutover must not be overstated |
| Runtime | Python 3.12; Vercel CLI 59.11.7 | **Open mismatch:** scheduled Node 20 vs site engine 22.x; scheduled extra `jsonschema` is unpinned |
| Freshness | Workflow implementation target is 120 minutes and verifies public/crawler surfaces | This is **not an SLA** |
| CI evidence retention | Publication-cycle GitHub artifact retention is 14 days | Historical durability/backup policy remains separate hardening work |
| Secrets | Scheduled workflow references `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` as GitHub secrets | Deployment-account ownership is adopter/commercial decision |
| External provider data | AP3 has identity/provenance/validation/quarantine boundary | Provider rights, retention, permitted use require human/provider confirmation |
| Editorial authority | Generated/draft/published states are separated; explicit human publication gate exists | Real adopter editorial roles/approval remain human decisions |
| Recipient delivery | AP5 can prepare and evidence a human-approved HTML/text briefing | Real recipient address, authorization, sender/provider and delivery acceptance remain external/human |
| Private operation | Public surface exists | Generic private authentication is not yet productized |
| Security | Trust/mutation boundaries are documented | No certification, penetration test, or formal security audit is claimed |
| Support/incidents | Technical runbooks exist | Support hours, incident commitment, SLA, warranty and liability are unchosen |
| Export/handoff | Structured JSON/JSONL/YAML/HTML/text artifacts and provenance hashes exist | Contractual export/termination/asset-transfer scope is unchosen |

## Licensing

There is currently **no repository-level `LICENSE` file** in this adoption branch. Public repository visibility is not being treated as a software license grant.

Before software rights are granted to an adopter, the owner must explicitly decide:

- repository licensing posture;
- commercial licensing model, if any;
- third-party dependency-license acceptance;
- attribution/white-label terms; and
- source/deployment asset transfer scope where relevant.

AP6 intentionally does not choose any of these.

## Runtime and reproducibility

The scheduled public workflow currently records:

- cron: `45 * * * *`;
- concurrency group: `scheduled-publication-production`;
- timeout: 25 minutes;
- Python: `3.12`;
- scheduled Node setup: `20`;
- Vercel CLI: `59.11.7`;
- public freshness implementation target: 120 minutes;
- anonymous deployment verification;
- crawler/feed/social-surface verification; and
- publication-cycle evidence upload with 14-day retention.

The Next.js site package declares Node `22.x`, so scheduled Node 20 versus site Node 22.x is an **open runtime-contract mismatch**. AP6 records it; this procurement packet does not fix production runtime.

The direct sensing requirements are exact-version pinned in `requirements-sensing.txt`. The scheduled workflow separately installs `jsonschema` without an exact version; that is also recorded as an open reproducibility detail rather than hidden.

## Secrets, deployment and account ownership

The scheduled workflow references only the following Vercel secret names for public deployment:

- `VERCEL_TOKEN`;
- `VERCEL_ORG_ID`;
- `VERCEL_PROJECT_ID`.

The workflow does not contain those secret values.

For a real adopter, the following are not pre-decided:

- whose provider/deployment account is authoritative;
- private authentication mechanism;
- allowed external services;
- credential rotation/support responsibility; and
- data/geographic restrictions.

Those belong to the adopter intake and eventual commercial/security terms.

## Data-source responsibility

AP3 provides a governed external monitored-signal contract with deterministic identity, schema validation, deduplication, conflict quarantine, and retained provider/source-record provenance.

That technical seam does **not** decide whether a provider/adopter is legally permitted to supply, retain, transform, redistribute, or archive particular data. Rights and retention assumptions must be confirmed by the relevant human/provider parties.

## Editorial and recipient authority

The architecture keeps these states distinct:

```text
generated != reviewed != approved != published != delivered
```

AP4 exposes a small review queue and explicit decision journal while preserving the existing publication gate. AP5 builds recipient artifacts only from `published_article.v1` content with `review_status=human_approved`, then separates package preparation, explicit delivery authorization, external sending, and receipt evidence.

No adoption tooling automatically authorizes real editorial content or sends to a real recipient.

## Storage, retention, durability and recovery

The scheduled publication workflow retains its GitHub publication-cycle artifact for **14 days**.

That fact should not be confused with a general durable historical archive or backup guarantee. Historical corpus durability/replay and cold-archive policy are being handled as a separate Media Monitor storage-hardening concern. Until that work closes, this packet makes **no generic backup, arbitrary historical replay, or recovery-time guarantee**.

Any adopter-specific data-retention or deletion obligation also requires an explicit decision.

## Security posture

Repository architecture documents trust and mutation boundaries, including provider/environment secret handling, allowlisted public projection, and browser read-only behavior.

AP6 makes no claim of:

- SOC 2 or equivalent certification;
- ISO certification;
- penetration testing;
- formal third-party security audit; or
- enterprise authentication controls not actually implemented.

If a buyer requires one of those, it becomes a concrete adoption requirement rather than marketing copy.

## Support, incidents and SLA

Technical runbooks and runtime evidence exist, but there is currently no human-approved contractual definition of:

- support model or hours;
- incident-response commitment;
- uptime/freshness SLA;
- warranty;
- indemnity/liability allocation; or
- service credits/remedies.

The workflow's 120-minute freshness value is an **implementation target**, not a contractual promise.

## Export, termination and transfer

Media Monitor already emits structured machine-readable artifacts and uses content/provenance hashes across multiple boundaries. That makes technical export possible, but it does not define a contractual handoff package.

A real deal must still decide, as applicable:

- which code/config/data/deployment assets transfer;
- whether source code is delivered or merely operated;
- export format and timing;
- historical corpus inclusion;
- credential/account handoff;
- post-termination retention/deletion; and
- support after handoff.

AP7 is responsible for turning one chosen commercial path into an executable scope/acceptance/transfer template. It must continue to leave actual price, licensing and legal terms for explicit human approval.

## Current diligence blockers worth resolving before stronger claims

1. Choose repository/software licensing posture before granting software rights.
2. Resolve or deliberately accept Node 20 scheduled runtime versus Node 22.x site engine.
3. Pin or explicitly govern scheduled `jsonschema` installation.
4. Complete dependency license review before contractual software delivery.
5. Define private authentication only if a real adopter needs it.
6. Close historical durability/recovery policy before promising backup/replay guarantees.
7. Decide support, privacy/legal, SLA, warranty/liability and commercial terms only through human/legal approval.

## Validation

Run:

```bash
python scripts/validate_procurement_trust.py
```

The validator checks repository facts, evidence paths, the missing-license state, runtime mismatch, dependency pin facts, artifact retention, secret-name references, and the `human_decision_required` fields. If repository reality changes, the packet is expected to fail until it is updated.