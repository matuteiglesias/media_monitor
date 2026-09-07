# Adoption-loop closure scorecard

> **Status:** seed measurement rubric · percentages are heuristic until replaced by observed adopter evidence

## Why score the last mile

Media Monitor can be technically mature while commercially difficult to adopt. This scorecard prevents more core engineering from masquerading as progress on the actual adoption bottleneck.

Scores should move only when new evidence reduces outsider friction.

## Seed baseline and target bands

| Closure dimension | Seed baseline | Target band after seed program | Evidence that earns the target |
|---|---:|---:|---|
| Stranger knows exactly what is offered | 35% | 80%+ | first-time evaluator can choose pilot / managed deployment / license-partnership / transfer and state what they receive |
| Stranger can provide requirements cleanly | 20% | 75–85% | adopter intake captures enough information to produce a bounded implementation plan with at most one clarification round |
| Live preview without bespoke archaeology | 35% | 70–80% | a second real adopter configuration reaches preview using documented/configured seams, with no outlet-specific core condition |
| Analyst/operator can use it comfortably | 25% | 60–70% | non-developer can complete standard review/approve/reject flow from a runbook or minimal operator surface |
| Client/boss receives expected deliverable | 30% | 65–75% | agreed scheduled brief/report/feed is generated, delivered and independently checked |
| Procurement understands license/security/support | 15% | 55–70% | explicit packet answers IP/license status, dependencies, secrets, data boundaries, retention, support/SLA posture and known limitations |
| They can pay/sign/license/take ownership | 10–20% | 50–65% | at least one human-approved transaction path can be executed without inventing its mechanics during the conversation |

Targets are deliberately below 100%. The goal is to make a first real transaction/adoption possible, not to pre-build enterprise procurement for every future buyer.

## Evidence ladder

Use the following evidence levels for each dimension:

- **L0 — asserted:** prose says the capability exists.
- **L1 — internally exercised:** maintainer/agent can follow it using fixtures or controlled inputs.
- **L2 — outsider-reproducible:** a technically competent outsider succeeds from documented surfaces.
- **L3 — real-adopter exercised:** one external adopter uses it with their actual/representative identity, sources or workflow.
- **L4 — repeated:** a second adopter or repeated cycle succeeds without bespoke repair.

A high percentage without at least L2 evidence is not credible. A commercial closure claim should normally require L3.

## Dimension-specific acceptance tests

### Offer clarity

Pass when an evaluator can answer, without reading architecture internals:

- what Media Monitor does;
- what they provide;
- what they receive;
- what remains human-controlled;
- which engagement forms are available;
- what is proven versus still pilot-stage.

### Requirements intake

Pass when the intake surface captures:

- organization/use case;
- source mode;
- topics/watch priorities;
- geography/languages;
- privacy/publication mode;
- approval authority;
- branding;
- cadence/deliverables;
- deployment/integration constraints;
- pilot acceptance criteria.

### Live preview

Pass when a fresh adopter profile can produce a preview without editing generic selection/context/snapshot builders for adopter-specific reasons.

### Operator comfort

Pass when a non-developer can perform the normal editorial decision path, understand failure/hold states, and recover from ordinary operator mistakes without direct database/storage editing.

### Deliverable closure

Pass when the adopter's actual recipient receives the artifact they care about. A beautiful internal index is not sufficient evidence.

### Procurement closure

Pass when unanswered questions are commercial choices rather than missing technical facts. The current absence of a repository-level `LICENSE` file is a concrete unresolved decision, not something to paper over with ambiguous wording.

### Transaction closure

Pass when the human owner has approved a concrete mechanism for at least one path, for example:

- bounded paid pilot with scope/acceptance/invoice;
- managed deployment agreement;
- software/technology license;
- asset/technology transfer checklist.

An online checkout is not required.

## Score maintenance rule

Every work packet should state which dimensions it expects to move and what new evidence was produced. If a packet creates code but moves no closure dimension, challenge whether it belongs in this program.
