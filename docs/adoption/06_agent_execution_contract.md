# Adoption-program agent and human execution contract

> **Status:** seed execution guidance · subordinate to repository `AGENTS.md` and explicit human authorization

## Operating model

This program is designed for alternating human judgment and bounded agent execution.

The human owner decides:

- whether a work packet is active;
- what commercial paths are acceptable;
- which adopter/prospect context may be used;
- pricing and payment mechanics;
- code/software licensing;
- legal/privacy/support commitments;
- whether external outreach is sent;
- whether a pilot/customer acceptance result is sufficient.

An agent may research, inspect, design, implement, test and document within an explicitly activated packet. It must not manufacture those commercial decisions.

## Before every packet

1. Read root `AGENTS.md` and follow it.
2. Inspect current source/tests/contracts/deployment evidence relevant to the packet.
3. Read this folder's `README.md`, `carry_state.yaml`, the selected packet and relevant seed context.
4. Treat seed percentages and market-pressure statements as hypotheses, not source truth.
5. State what evidence level currently exists and what level the packet is meant to reach.
6. Keep unrelated hardening/storage/scheduler work out of the adoption PR unless it is a direct prerequisite.

## Architectural guardrails

### No new runtime owner by default

`docs/adoption/` owns program context only. It does not own sensing, enrichment, editorial, publication or site runtime.

### No adopter conditionals in generic core

Reject patterns such as:

```text
if customer == "X": ...
if outlet == "mining-client": ...
```

Prefer configuration, contracts or a deliberately reusable adapter.

### Do not silently weaken authority

Adoption convenience cannot make:

```text
generated == published
selected == authored
monitored == verified editorial claim
```

### Prefer isolated instances before multi-tenancy

For early adopters, separate projects/config roots/deployments may be safer and faster than inventing tenant isolation infrastructure.

### Prefer concierge before platform breadth

Human onboarding, configuration and invoicing are acceptable until repeated evidence shows automation is worth owning.

## PR discipline

Each adoption PR should contain:

- the activated packet ID;
- exact closure dimension(s) targeted;
- evidence before/after;
- scope and non-goals;
- source/runtime owners touched;
- tests/acceptance performed;
- any new reusable-platform requirement discovered;
- carry-state proposal.

If a runtime change crosses an existing owner boundary, follow that owner's canonical architecture/runbook rather than creating a parallel adoption implementation.

## Claims discipline

The agent must distinguish:

- designed;
- implemented;
- locally validated;
- deployment-ready;
- deployed;
- operated;
- real-adopter exercised.

Do not use "customer", "production adopter", "white-label deployment" or similar language for fixture/demo evidence.

## Prospect and outreach hygiene

Named companies/people should not be committed into this public adoption program merely because they appeared in exploratory research. Store prospect-specific analysis in the appropriate private scouting/outreach context and re-verify current facts before use.

The repository should preserve reusable adopter archetypes and requirements, not a stale public target list.

## Stop-and-escalate decisions

The agent should stop and return a decision packet rather than choose on behalf of the owner when work reaches:

- software/repository license selection;
- pricing or discounting;
- liability/warranty/support SLA;
- customer data processing/privacy commitments;
- third-party data rights interpretation;
- public brand/marketing claims with material ambiguity;
- external outreach/send action;
- destructive migration/transfer of customer or production state.

## Completion update

At the end of a packet, update or propose updates to:

- closure evidence level;
- score estimate only if justified;
- new blockers;
- next packet;
- runtime/platform requirements discovered;
- explicit rejected overbuilds.

The program is working when agents can make adoption easier without making the core less governed.
