# Media Monitor adoption-loop seed

> **Status:** active adoption program · supporting product/adoption context · **not runtime authority and not a commercial commitment**

## Purpose

Media Monitor already proves a substantial governed product path: sensing, deterministic selection, story context, human-gated editorial publication, generated public snapshots, health/freshness checks, an offline deterministic demo, and a configurable second-instance example.

The remaining adoption problem is different. A technically serious outsider can inspect the system, but the path from **interest** to **requirements** to **their live preview** to **their operator** to **their deliverable** to **a commercial decision** is not yet closed.

This folder is the program for closing that loop without turning Media Monitor into an undifferentiated multi-tenant SaaS.

It is deliberately housed inside this repository because the adoption surface must stay aligned with the real product contracts, evidence and deployment machinery. It does **not** create a new runtime owner. Runtime ownership remains with the existing `apps/**`, builders, contracts and deployment surfaces.

## Current adopter-facing front door

AP0 has promoted the bounded evaluator surface into [`ADOPT_MEDIA_MONITOR.md`](../../ADOPT_MEDIA_MONITOR.md).

That page is the current answer to "what can an outside organization evaluate here?" It distinguishes bounded pilot, managed white-label deployment, technology/license partnership and strategic technology transfer; states what is proven versus not yet productized; and routes a prospect into the adopter-intake questions without inventing pricing, licensing or SLA terms.

AP0 is internally implemented at evidence level **L1**. External **L2** validation remains pending before the offer-clarity target band is claimed. See [`closures/AP0.md`](closures/AP0.md).

## Current evidence boundary

Start from current source and executable evidence, not from this program's prose:

- [root README](../../README.md) — deployed product and operator/evaluator front door;
- [EVIDENCE.md](../../EVIDENCE.md) — what counts as production, rehearsal and demo evidence;
- [build another outlet](../../examples/outlet/README.md) — proves another configured outlet can compile through the generic selection/context/snapshot machinery;
- [documentation map](../README.md) — canonical architecture and operation routing;
- [artifact/state authority](../architecture/artifact-ladder-and-state.md) — do not bypass existing authority boundaries.

The current adopter example deliberately stops before live acquisition and production deployment. The repository also deliberately avoided building a full editorial CMS, enterprise auth, generic personalization and similar product breadth without a proven consumer. Those choices remain valid until adopter evidence changes them.

## Baseline closure problem

The percentages below are heuristic starting estimates, not measured product KPIs. The program exists to replace them with evidence.

| Closure question | Seed estimate | Desired direction |
|---|---:|---|
| Stranger knows exactly what is being offered | 35% | clear offer and evidence route |
| Stranger can provide requirements cleanly | 20% | bounded adopter intake contract |
| A live preview can be made without bespoke archaeology | 35% | repeatable real-adopter bootstrap |
| Their analyst/operator can use it comfortably | 25% | minimal operator/reviewer path |
| Their client/boss receives the expected deliverable | 30% | governed delivery artifact(s) |
| Procurement understands license/security/support | 15% | explicit trust/procurement packet |
| They can pay, sign, license or take ownership | 10–20% | explicit transaction/transfer paths |

See [closure scorecard](02_closure_scorecard.md) for evidence-based scoring rules, AP0 movement and target bands.

## Product thesis under test

The strongest reusable proposition is not "another media-monitoring dashboard." It is:

> Bring your sources or signal stream, watch priorities, brand and editorial policy. Media Monitor provides a governed path from monitored evidence to deterministic prioritization, context, optional assisted editorial work, explicit human authority and a deployable intelligence/publication surface.

Possible commercial forms are deliberately plural at this stage:

1. bounded paid pilot;
2. managed white-label deployment;
3. software/license or technology partnership;
4. strategic transfer/acquisition of the asset and know-how.

No one path is canonical until real adopter evidence supports it.

## Program rules

1. **Do not build generic SaaS infrastructure in anticipation of demand.** No multi-tenancy, billing platform, enterprise SSO, generic CMS, omnichannel notification system or dashboard suite without a real adopter requirement.
2. **Concierge operation is allowed.** For the first adopters, human configuration, invoices, isolated deployments and manual onboarding can be the correct architecture.
3. **One reusable requirement earns one reusable change.** Adopter-specific conditions must not leak into core builders.
4. **Keep monitored, selected, generated, approved and published authority distinct.** Adoption work cannot weaken the product's strongest governance boundary.
5. **Public claims must match evidence.** A fixture second instance is not a live adopter. A deployment-ready path is not an operated customer instance.
6. **Commercial/legal decisions remain human decisions.** Pricing, licensing, warranty/support commitments, privacy/data terms and outbound claims require explicit human approval.
7. **This program does not supersede `AGENTS.md`.** A human must authorize a work packet before an agent executes it.

## Work-packet sequence

The sequence is defined in [03_work_packets.md](03_work_packets.md):

- **AP0 — Offer and evaluator front door** — implemented L1; L2 validation pending
- **AP1 — Adopter intake and manifest** — default next packet
- **AP2 — Real adopter bootstrap**
- **AP3 — Bring-your-own signal boundary**
- **AP4 — Minimal analyst/reviewer operation**
- **AP5 — Client/boss deliverable**
- **AP6 — Procurement and trust packet**
- **AP7 — Transaction and transfer closure**
- **AP8 — First real adopter acceptance**

Each packet should be independently reviewable. A packet may conclude that no code is required.

## Navigation

- [public adopter/evaluator front door](../../ADOPT_MEDIA_MONITOR.md)
- [01 · market pressure and adopter archetypes](01_context_and_market_pressure.md)
- [02 · closure scorecard](02_closure_scorecard.md)
- [03 · work packets](03_work_packets.md)
- [04 · adopter intake contract](04_adopter_intake_contract.md)
- [05 · commercial-front seed](05_commercial_front_seed.md)
- [06 · agent/human execution contract](06_agent_execution_contract.md)
- [AP0 closure](closures/AP0.md)
- [`adopter_intake.example.yaml`](adopter_intake.example.yaml)
- [`carry_state.yaml`](carry_state.yaml)

## Program completion condition

Do not call adoption-loop closure complete because a sales page exists or a demo looks polished.

The program has materially succeeded when a first-time external adopter can:

1. understand the bounded offer without repository archaeology;
2. describe their needs through a stable intake surface;
3. receive a branded preview using live or representative real inputs without outlet-specific core edits;
4. operate the normal review/approval path without a developer sitting beside them;
5. receive the agreed recurring intelligence deliverable;
6. understand the product's security, data, retention, support, licensing and responsibility boundaries;
7. enter a paid pilot, license/managed deployment, partnership or transfer using an explicit human-approved commercial path;
8. leave behind acceptance evidence that makes the next adopter easier rather than more bespoke.
