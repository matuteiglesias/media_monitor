# AP6 closure — procurement and trust packet

> **Status:** implemented internal diligence surface · L1 · human/legal/commercial decisions intentionally unresolved

## Objective

Make technical procurement/diligence questions answerable without repository archaeology while preventing the adoption program from inventing legal, security or commercial commitments.

## Implemented

- [`../procurement_trust_state.yaml`](../procurement_trust_state.yaml) — machine-readable technical/diligence state;
- [`../procurement_trust.md`](../procurement_trust.md) — evaluator-facing summary;
- `scripts/validate_procurement_trust.py` — repository drift/claim guard;
- `tests/test_procurement_trust_packet.py` — adversarial checks for silent license/SLA/runtime/evidence drift.

## Material facts surfaced

AP6 records, among other facts:

- no repository-level `LICENSE` file is present on this adoption branch;
- Python sensing runtime is configured as 3.12 in scheduled publication;
- direct sensing requirements are exact-version pinned;
- Vercel CLI is pinned to 59.11.7;
- scheduled publication currently sets Node 20 while the site package declares Node 22.x (**open mismatch**);
- scheduled `jsonschema` installation is unpinned;
- public freshness has a 120-minute implementation target, explicitly **not an SLA**;
- publication-cycle GitHub evidence retention is 14 days;
- scheduled public deployment references the Vercel secret names `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and `VERCEL_PROJECT_ID`;
- generic private authentication is not yet productized;
- no certification, penetration test, or formal security audit is claimed;
- historical durable backup/replay is not promised by this adoption packet; and
- AP3/AP4/AP5 authority and provenance boundaries are available as diligence evidence.

## Human decisions structurally reserved

The packet requires `human_decision_required` for the unresolved areas that cannot be chosen by an agent, including:

- repository/software licensing;
- commercial licensing model;
- dependency-license acceptance;
- deployment-account ownership;
- private authentication posture;
- provider data rights/retention/permitted use;
- real editorial and delivery authorization;
- durability/cold-archive and adopter retention terms;
- support hours/model and incident commitments;
- uptime/freshness SLA;
- privacy/legal/warranty/indemnity/liability terms;
- export/termination/source-asset transfer obligations;
- pricing, invoicing and payment terms;
- attribution/white-label terms; and
- pilot/service acceptance terms.

## Drift guards

The validator refuses the packet if, among other cases:

- an unresolved license field is silently replaced by a license choice;
- evidence pointers stop resolving;
- the current Node mismatch is hidden without the runtime evidence changing;
- the 120-minute implementation target is represented as a contractual SLA;
- certifications are claimed without evidence; or
- a repository-level license file appears while the packet still describes the file as absent.

This converts AP6 from static procurement copy into a bounded claim surface that is expected to fail when repository reality changes.

## Evidence level

This is **L1 / internally validated diligence readiness**.

Procurement clarity may move provisionally from the 15% seed baseline to roughly **50–55%** because most technical archaeology has been collapsed into an evidence-backed packet. The 55–70% target band still requires a real evaluator/procurement conversation and human resolution of whichever legal/commercial decisions actually block that path.

## Remaining AP6 acceptance

A real evaluator should be able to use this packet to identify the remaining questions without browsing repository internals. The owner/human/legal side then needs to resolve only the decisions relevant to the chosen commercial form.

Do not resolve every enterprise control in advance. A buyer requirement should earn any additional security, authentication, compliance or contractual work.

## Next packet

Proceed to **AP7 — transaction and transfer closure**.

AP7 may prepare executable scope, acceptance, responsibility, handoff and transfer templates for the candidate commercial forms, but it must keep actual price, software rights, legal terms, support commitments and signature/acceptance as explicit human fields.