# Media Monitor adoption loop

> **Status:** AP0–AP8 engineering harness implemented at internal evidence level · **real external adoption remains pending** · not runtime authority and not a commercial commitment

## Purpose

Media Monitor already proves a substantial governed product path: sensing, deterministic selection, story context, human-gated editorial publication, generated public snapshots, health/freshness checks, an offline deterministic demo, and configurable additional-outlet machinery.

This folder governs the separate last-mile problem:

```text
interest
  -> requirements
  -> adopter preview
  -> adopter/provider input
  -> operator authority
  -> recipient deliverable
  -> procurement/trust
  -> transaction mechanics
  -> observed real-adopter acceptance
```

The program lives inside this repository so adoption claims stay aligned with real contracts/evidence. It creates **no new runtime owner**. Runtime authority remains with the existing `apps/**`, contracts, builders and deployment surfaces.

## Current state

The AP0–AP8 **engineering surfaces now exist**. That does not mean the external adoption gates are complete.

| Surface | Internal readiness | External truth still required |
| --- | --- | --- |
| Offer | L1 | outsider comprehension |
| Intake | L1 | outsider completion |
| Preview/bootstrap | L1 | isolated external preview |
| External signal boundary | L1 | provider-real exercise + rights |
| Analyst/reviewer operation | L1 | non-developer exercise |
| Recipient deliverable | L1 | real delivery + usefulness |
| Procurement/trust | L1 | external diligence + selected blocker resolution |
| Transaction/transfer mechanics | L1 | real counterparty + human terms/acceptance |
| First adopter acceptance | harness L1 | **real adopter L0/pending** |

The authoritative carry state is [`carry_state.yaml`](carry_state.yaml). The detailed packet map is [`03_work_packets.md`](03_work_packets.md).

## Current adopter-facing front door

[`ADOPT_MEDIA_MONITOR.md`](../../ADOPT_MEDIA_MONITOR.md) is the bounded evaluator surface. It distinguishes:

- bounded pilot;
- managed white-label deployment;
- technology/license partnership; and
- strategic technology transfer.

It deliberately does not invent pricing, licensing, SLA or customer claims.

## Current evidence boundary

Start from executable evidence, not adoption prose:

- [root README](../../README.md) — product/evaluator entry point;
- [EVIDENCE.md](../../EVIDENCE.md) — production/rehearsal/demo evidence classes;
- [build another outlet](../../examples/outlet/README.md) — generic second-outlet compilation;
- [documentation map](../README.md) — architecture/operation routing;
- [artifact/state authority](../architecture/artifact-ladder-and-state.md) — canonicality boundaries;
- [trust boundaries](../architecture/trust-boundaries.md) — mutation/secrets boundary;
- [identity/provenance/replay](../architecture/identity-provenance-and-replay.md) — identity and replay semantics.

## Baseline and current provisional closure estimates

These are heuristic readiness estimates, not product KPIs or customer evidence.

| Closure question | Seed | Current provisional | Target band |
| --- | ---: | ---: | ---: |
| Stranger knows exactly what is offered | 35% | ~65% L1 | 80–90% |
| Stranger can provide requirements cleanly | 20% | ~60% L1 | 75–85% |
| Preview without bespoke archaeology | 35% | ~60% L1 | 70–80% |
| Analyst/operator can operate comfortably | 25% | ~55% L1 | 60–70% |
| Recipient receives expected deliverable | 30% | ~55% L1 | 65–75% |
| Procurement understands trust/license/support | 15% | ~55% L1 | 55–70% |
| They can proceed commercially/transfer | 10–20% | ~40–45% L1 | 50–65% |

No target-band claim is earned merely by internal implementation. See [`02_closure_scorecard.md`](02_closure_scorecard.md).

## Product thesis under test

The reusable proposition is not “another media-monitoring dashboard.” It is:

> Bring your sources or signal stream, watch priorities, brand and editorial policy. Media Monitor provides a governed path from monitored evidence to deterministic prioritization, context, optional assisted editorial work, explicit human authority and a deployable intelligence/publication surface.

Commercial forms remain deliberately plural until real evidence selects one:

1. bounded paid pilot;
2. managed white-label deployment/service;
3. software/license or technology partnership;
4. strategic asset/technology transfer.

## Program rules

1. **Do not build generic SaaS infrastructure in anticipation of demand.** No multi-tenancy, billing platform, enterprise SSO, generic CMS, connector marketplace, omnichannel suite or generic dashboard suite without a real adopter requirement.
2. **Concierge operation is legitimate.** Early adopters may use human configuration, isolated deployments, manual onboarding and ordinary invoicing.
3. **One reusable requirement earns one reusable change.** Adopter-specific conditions do not leak into generic core.
4. **Keep authority states distinct.** Monitored, selected, generated, reviewed, approved, published, authorized-for-delivery and delivered are not interchangeable.
5. **Public claims match evidence.** A fixture is not a customer. A prepared artifact is not delivery. A transaction template is not a contract.
6. **Commercial/legal decisions remain human decisions.** Pricing, licensing, privacy/legal, warranty/liability, support/SLA, rights transfer, external sends and signatures require explicit human authority.
7. **No fake completion.** AP8 is specifically designed to refuse accepted-adopter status when real external evidence is missing.
8. **This program does not supersede `AGENTS.md`.**

## AP0–AP8 outputs

- **AP0 — Offer/front door:** public evaluator surface.
- **AP1 — Intake:** validated manifest and deterministic implementation-plan compiler.
- **AP2 — Bootstrap:** isolated adopter-branded representative preview compiler.
- **AP3 — External signals:** provider-neutral import contract with validation/quarantine/provenance.
- **AP4 — Reviewer:** readable review queue, decision journal and isolated human-approved publication seam.
- **AP5 — Recipient:** human-approved HTML/text brief preparation, explicit delivery authorization and evidence recording.
- **AP6 — Procurement/trust:** machine-readable diligence state, human summary and drift guard.
- **AP7 — Transaction/transfer:** scope, responsibility, human-terms, asset and exit/handoff packet with no-rights/no-contract guardrails.
- **AP8 — Acceptance:** strict real-adopter evidence schema/evaluator and committed pending-only template.

## Navigation

- [public adopter/evaluator front door](../../ADOPT_MEDIA_MONITOR.md)
- [01 · market pressure and adopter archetypes](01_context_and_market_pressure.md)
- [02 · closure scorecard](02_closure_scorecard.md)
- [03 · work packets/current state](03_work_packets.md)
- [04 · adopter intake contract](04_adopter_intake_contract.md)
- [05 · commercial-front seed](05_commercial_front_seed.md)
- [06 · agent/human execution contract](06_agent_execution_contract.md)
- [external signal boundary](external_signal_boundary.md)
- [recipient delivery boundary](recipient_delivery.md)
- [procurement/trust packet](procurement_trust.md)
- [transaction/transfer closure](transaction_and_transfer.md)
- [first real adopter acceptance](first_real_adopter_acceptance.md)
- [AP0–AP8 closure records](closures/)
- [`adopter_intake.example.yaml`](adopter_intake.example.yaml)
- [`adopter_acceptance.template.yaml`](adopter_acceptance.template.yaml)
- [`carry_state.yaml`](carry_state.yaml)

## What happens next

There is no default AP9 engineering packet.

The next authoritative phase is **real adopter execution**:

1. outsider validates AP0/AP1;
2. isolated preview is deployed/verified;
3. real/representative provider input is exercised and rights confirmed;
4. non-developer operator exercises review;
5. recipient actually receives and uses the deliverable;
6. external evaluator uses the trust packet and blocking terms are resolved;
7. real counterparty scope/commercial/legal acceptance occurs; and
8. a `real_external` AP8 evidence record passes the strict evaluator with explicit human confirmation.

Until step 8 succeeds, the adoption program remains **not complete**, regardless of how polished the internal engineering becomes.
