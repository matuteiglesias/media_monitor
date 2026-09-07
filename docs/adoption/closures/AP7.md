# AP7 closure — transaction and transfer closure

> **Status:** implemented internal transaction-scoping mechanics · L1 · real counterparty/human terms pending

## Objective

Make at least one “we want to proceed” path mechanically concrete without allowing an agent to choose commercial/legal terms or represent that a contract exists.

## Implemented

`scripts/build_transaction_packet.py` compiles a validated adopter intake into:

- `scope_and_acceptance.md`;
- `responsibility_matrix.yaml`;
- `human_terms.yaml`;
- `asset_inventory.yaml`;
- `exit_handoff.md`;
- a copy of the validated adopter intake; and
- `transaction_manifest.json` with hashes over the generated packet.

The representative intake selects `paid_pilot`, which maps to `bounded_paid_pilot`.

Other supported selected modes are managed deployment/service, technology-license partnership, and strategic asset transfer. `exploratory_undecided` is refused because it is not transaction-ready.

## Guardrails

The agent-generated packet always states:

- `contract_formed=false`;
- `software_rights_granted=false`;
- `payment_obligation_created=false`;
- `signatures_present=false`;
- `human_terms_required=true`.

The validator requires all reserved commercial/legal fields to remain `human_decision_required`, including price, currency, payment, licensing, source/deployment rights, data/privacy terms, support, SLA, warranty/liability, attribution, termination, governing law and acceptance/signature fields.

The asset inventory grants no rights and includes no secret/provider credentials.

The responsibility matrix distinguishes provisional operational ownership derived from the intake from contractual allocation, which remains a human decision.

## Internal acceptance tests

Focused tests exercise:

- compilation of the representative paid-pilot intake;
- carry-through of 14-day duration, 90-minute pilot freshness target, five successful cycles and the requested HTML/email deliverable;
- preservation of human-only price/license/support/privacy/signature fields;
- intake-derived provisional owners without contractualizing them;
- no-rights/no-secrets asset inventory;
- refusal if an agent-generated price is inserted; and
- refusal of an `exploratory_undecided` intake as transaction-ready.

## Evidence level

This is **L1 / internally exercised transaction readiness**.

Transaction closure may move provisionally from the 10–20% seed range to roughly **45%**. The 50–65% target still requires a real counterparty plus human-approved commercial/legal terms and an external acceptance/signature mechanism where appropriate.

## Remaining AP7 acceptance

A human must still:

1. choose/approve actual price, currency, invoice/payment mechanics where relevant;
2. choose the software/repository licensing or service-rights posture;
3. resolve privacy/data, support/SLA, warranty/liability and governing-law terms that the selected counterparty actually requires;
4. decide any source-code/deployment/domain/provider-account/data transfer rights;
5. exchange the correct external document or order form/proposal/contract;
6. obtain the relevant owner/counterparty acceptance/signature; and
7. record the accepted scope so AP8 can compare real execution against it.

## Next packet

Proceed to **AP8 — first real adopter acceptance evidence**.

AP8 may implement an evidence schema/compiler that refuses to mark a cycle accepted unless the required real-world evidence exists. It must not create fake preview URLs, operator actions, delivery receipts, commercial acceptance or customer claims.