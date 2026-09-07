# AP1 closure — adopter intake and manifest

> **State:** implemented · internal evidence L1 · outsider validation pending

## Goal

Convert fuzzy adopter interest into a bounded, machine-checkable requirements packet and a deterministic implementation-plan classification before engineering starts.

## Implemented

- `docs/adoption/adopter_intake.schema.json`
  - JSON Schema 2020-12;
  - stable `media_monitor_adopter_intake.v1` identity;
  - required organization/use-case/source/watch/authority/identity/privacy/deliverable/integration/acceptance/commercial sections;
  - fails closed on `auto_publish_generated_text`, which must remain `false`;
  - reserves pricing and licensing as `human_decision_required`.
- `docs/adoption/adopter_intake.example.yaml`
  - representative private executive-brief pilot;
  - adopter-provided feed;
  - explicit reviewer/approver roles;
  - delivery/acceptance targets and unresolved human decisions.
- `scripts/adopter_intake.py`
  - validates YAML against the schema;
  - emits deterministic intake SHA-256;
  - compiles a JSON or Markdown implementation plan;
  - classifies requested work into `CONFIG_ONLY`, `ADAPTER_REQUIRED`, `REUSABLE_PLATFORM_REQUIREMENT`, `HUMAN_DECISION_REQUIRED`, and `OUT_OF_SCOPE`;
  - suggests AP2/AP3/AP4/AP5 sequencing from actual intake characteristics;
  - never provisions, deploys, prices, licenses or mutates production.
- `tests/test_adopter_intake.py`
  - validates the representative intake;
  - proves the generated→published authority violation is rejected;
  - checks deterministic plan classification and hashing.
- runtime CI includes the AP1 contract suite.

## Representative-plan result

The seed intake intentionally exercises multiple boundaries:

- watch policy, identity and acceptance thresholds → `CONFIG_ONLY`;
- adopter-provided feed → `ADAPTER_REQUIRED` / AP3;
- HTML/email brief → `REUSABLE_PLATFORM_REQUIREMENT` / AP5;
- private mode → AP4/AP6 requirement;
- unresolved auth/account ownership/attribution → `HUMAN_DECISION_REQUIRED`;
- pricing and license → always human decisions.

This is useful because a realistic pilot is no longer allowed to appear as one undifferentiated feature request.

## Evidence level

**L1 — internally exercised.**

AP1 reaches L2 only when a first-time outsider can complete an intake and the resulting plan is sufficiently precise to begin with at most one clarification round.

## Score effect

Requirements-intake readiness moves provisionally from the 20% seed estimate to approximately **60%**. The 75–85% target band remains gated on outsider/L2 evidence.

## Rejected overbuild

AP1 does not add:

- self-service onboarding UI;
- customer database/CRM;
- tenant provisioning;
- pricing engine;
- contract automation;
- generic feature-request tracker.

## Remaining human actions

- outsider completion/clarity test;
- human choice of any actual commercial, license, privacy or support terms;
- activation of real-adopter work.

## Next packet

**AP2 — real adopter bootstrap** is now technically unblocked for the configuration/bootstrap subset. AP3/AP4/AP5 remain conditional on what a validated intake requires.
