# Adoption-loop work packets

> **Status:** AP0–AP8 engineering surfaces implemented at internal evidence level; real-adopter acceptance remains pending.

## Packet discipline

One packet owns one reviewable objective. Commercial copy, runtime adapters, operator UX, recipient delivery, procurement facts and legal/commercial decisions must not collapse into one authority.

Code is justified only when it removes demonstrated adopter friction through a reusable seam. Internal implementation is not external adoption evidence.

## Current program map

| Packet | Engineering status | Evidence boundary | Remaining external/human gate |
| --- | --- | --- | --- |
| AP0 offer/front door | implemented | L1 | outsider understands offer and gaps |
| AP1 intake/manifest | implemented | L1 | outsider completes intake with ≤1 clarification round |
| AP2 adopter bootstrap | implemented | L1 representative | isolated real/representative preview deployed and identity-verified |
| AP3 external signals | implemented | L1 | provider maps representative-real input, rights confirmed, repeated cycles |
| AP4 reviewer operation | implemented | L1 | non-developer completes governed review cycle |
| AP5 recipient deliverable | implemented | L1 | real recipient receives exact authorized artifact and confirms usefulness |
| AP6 procurement/trust | implemented | L1 | external evaluator uses packet; selected-path blockers resolved by humans |
| AP7 transaction/transfer | implemented | L1 | real counterparty + human-approved terms/external acceptance mechanism |
| AP8 adopter acceptance | harness implemented | harness L1; adopter acceptance L0/pending | real_external evidence passes strict evaluator + human confirmation |

## AP0 — Offer and evaluator front door

**Goal:** make the offer intelligible without unsupported commercial claims.

**Implemented:** `ADOPT_MEDIA_MONITOR.md`, root README routing, four engagement paths, evidence-calibrated current/provisional capability boundary, AP0 closure record.

**Non-goals:** pricing page, checkout, CRM, inflated customer claims.

**External done condition:** a first-time evaluator can explain the offer, distinguish proven capabilities from pilot-stage gaps, and choose the relevant engagement path without architecture archaeology.

---

## AP1 — Adopter intake and manifest

**Goal:** convert fuzzy interest into bounded implementation inputs.

**Implemented:** validated `media_monitor_adopter_intake.v1`, YAML example, deterministic validator/plan compiler, five engineering/decision buckets.

**Non-goals:** self-service onboarding UI, customer database.

**External done condition:** an outsider completes the intake without repository knowledge and the resulting plan is actionable with at most one clarification round.

---

## AP2 — Real adopter bootstrap

**Goal:** make “give me one for X” operationally boring without tenant infrastructure.

**Implemented:** validated intake → isolated adopter-branded representative preview package using the generic editorial-selection, story-context and site-snapshot builders; owner/editor leakage checks; explicit fixture/not-live caveats.

**Hard rule:** no adopter-name/topic conditionals inside generic builders.

**Non-goals:** multi-tenant runtime, dynamic tenant provisioning.

**External done condition:** a real or representative external adopter reaches an isolated provider preview with verified identity and no generic-core edits.

---

## AP3 — Bring-your-own signal boundary

**Goal:** let an adopter retain its acquisition/monitoring system.

**Implemented:** `external_monitored_signal.v1`, deterministic file import, validation, quarantine, duplicate accounting, fail-closed identity conflicts, provenance preservation, normalized external input → AP2 compiler.

**Non-goals:** connector marketplace, vendor-specific hard-coded adapters, live HTTP ingestion service.

**External done condition:** an external producer maps a representative-real export without repository archaeology, provider/data-rights assumptions are confirmed, and repeated successful cycles support the live-source claim.

---

## AP4 — Minimal analyst/reviewer operation

**Goal:** make existing human authority usable by an adopter operator.

**Implemented:** readable review queue with draft/source/citation/fact-check/revision evidence; hold/revise/reject/approve decision journal; explicit isolated published-bus seam; existing `--approve-human` publication authority preserved.

**Non-goals:** newsroom CMS, collaborative editor, generic RBAC/SSO.

**External done condition:** a non-developer performs the ordinary review cycle, including a refusal/recovery case, without direct storage/database surgery.

---

## AP5 — Client/boss deliverable

**Goal:** produce the artifact the adopter's recipient actually consumes.

**Implemented first surface:** `html_email_brief` only. Validated intake + `site_snapshot.v4` → branded HTML/text brief from human-approved `published_article.v1` content, exact hashes, delivery manifest, separate human authorization, and external delivery-evidence recording.

**Authority rule:** prepare ≠ authorize ≠ external send ≠ receipt. AP5 itself sends nothing.

**Non-goals:** SMTP/provider choice before adopter demand; WhatsApp/Slack/PDF suite; recipient-address database.

**External done condition:** a real recipient receives the agreed exact artifact on the agreed cadence, delivery evidence is recorded, and the recipient confirms usefulness.

---

## AP6 — Procurement and trust packet

**Goal:** make technical/commercial diligence answerable without repository archaeology.

**Implemented:** machine-readable diligence state, evaluator-facing summary, repository-fact drift validator, and explicit `human_decision_required` fields.

**Material current facts include:** no repository-level license file; Python 3.12 scheduled runtime; Vercel CLI 59.11.7; scheduled Node 20 vs site Node 22.x mismatch; unpinned scheduled extra `jsonschema`; 120-minute freshness implementation target is not an SLA; publication-cycle artifact retention is 14 days; no generic private-auth product or certification/security-audit claim.

**Non-goals:** fabricated certifications, invented SLA/privacy/license/support terms, unrelated production fixes inside diligence docs.

**External done condition:** a real evaluator can identify the remaining blockers from this packet, and humans resolve only the terms/controls actually required by the selected path.

---

## AP7 — Transaction and transfer closure

**Goal:** make “we want to proceed” mechanically concrete.

**Implemented:** validated selected commercial path → scope/acceptance, provisional responsibility matrix, human-terms sheet, asset inventory, exit/handoff checklist and hash-bound transaction manifest.

**Hard authority rule:** every agent-generated packet states no contract formed, no software rights granted, no payment obligation, no signatures; reserved commercial/legal terms remain `human_decision_required`.

**Non-goals:** billing platform, agent-set prices, license grants, signatures or rights transfer.

**External done condition:** a real counterparty selects/confirms a path, humans approve the actual required terms, the correct external proposal/order/contract is exchanged, and acceptance/signatures are obtained where appropriate.

---

## AP8 — First real adopter acceptance

**Goal:** replace simulated buyer pressure with observed adopter evidence.

**Implemented harness:** acceptance schema, committed pending-only template, strict evaluator, reusable-vs-adopter-specific deviation split, and refusal tests.

**Critical truth boundary:** there is no committed accepted adopter record. Representative/test evidence cannot satisfy accepted status. A real accepted record must satisfy intake, preview, source cycles/rights, non-developer operator, recipient delivery, procurement, transaction, deviations and explicit human acceptance gates, then be evaluated with `--confirm-real-external-evidence`.

**Engineering done condition:** the harness can truthfully say why a cycle is pending/not accepted and can validate a complete real-external evidence record.

**Adoption done condition:** the first real external adoption cycle passes that evaluator. This has **not happened yet**.

## Activation rule after AP8

There is no default AP9 engineering packet.

The next authoritative action is `HUMAN_REAL_ADOPTER_EXECUTION`, as recorded in `carry_state.yaml`. Future agents should not restart AP1–AP8 merely because the external L2 gates are still pending.

Additional generic code should only be added when a real adopter exercise exposes a reusable blocker. Adopter-specific requirements remain outside generic core unless repeated evidence earns promotion.
