# Transaction and transfer closure

> **Status:** AP7 internal implementation · scoping mechanics only · no contract, price, license grant, signature, payment obligation, or asset transfer is created by this tooling

## Purpose

Close the operational gap behind the sentence:

> “We want to proceed.”

Before AP7, that sentence still required inventing scope, acceptance, responsibilities, handoff, transfer inventory and reserved legal/commercial terms in real time.

AP7 turns a validated adopter intake into a bounded transaction-scoping packet while preserving the distinction between:

- technical scoping that an agent can prepare; and
- commercial/legal commitments that only the relevant humans can approve.

## Supported candidate commercial paths

The intake may select one of:

| Intake value | AP7 transaction mode |
| --- | --- |
| `paid_pilot` | `bounded_paid_pilot` |
| `managed_white_label` | `managed_deployment_service` |
| `technology_license_partnership` | `technology_license_partnership` |
| `strategic_transfer` | `strategic_asset_transfer` |

`exploratory_undecided` is intentionally rejected by the AP7 compiler. An undecided conversation is not transaction-ready.

## Command

```bash
python scripts/build_transaction_packet.py build \
  --intake docs/adoption/adopter_intake.example.yaml \
  --out <isolated-transaction-packet-dir>
```

Validate an existing packet:

```bash
python scripts/build_transaction_packet.py validate \
  --packet-dir <isolated-transaction-packet-dir>
```

## Generated packet

The compiler writes:

### `scope_and_acceptance.md`

Carries forward the adopter's actual:

- organization/use case;
- selected commercial mode;
- source mode;
- requested deliverables and cadence;
- pilot duration;
- freshness acceptance target;
- minimum successful cycles;
- operator-review requirement;
- recipient-delivery requirement; and
- required evidence.

The intake's freshness target remains a **pilot acceptance target**, not a contractual SLA until the human terms explicitly say otherwise.

### `responsibility_matrix.yaml`

Separates:

- provisional operational ownership inferred from the intake; from
- contractual allocation, which remains `human_decision_required`.

This allows scoping to proceed without falsely converting an intake answer into a legal responsibility clause.

### `human_terms.yaml`

Every reserved commercial/legal field is initialized as:

```text
human_decision_required
```

This includes, among other fields:

- price/currency;
- invoice/payment terms;
- repository/software license;
- source-code/deployment rights;
- data rights/retention;
- privacy/DPA terms;
- support and incident commitments;
- SLA;
- warranty/indemnity/liability;
- attribution/white-label terms;
- termination/retention/deletion;
- governing law/venue; and
- owner/counterparty acceptance.

The validator refuses an agent-generated packet if any of those terms have been silently filled.

### `asset_inventory.yaml`

Lists the technical surfaces that can be discussed during scoping while explicitly stating:

- no software/source-code rights are granted;
- no provider credentials or secrets are included;
- historical-corpus inclusion is unresolved;
- deployment/domain/provider-account transfer is unresolved; and
- post-transfer support is unresolved.

An inventory is not a license or transfer instrument.

### `exit_handoff.md`

Provides a technical exit/handoff checklist without creating contractual obligations. It separates exportable technical artifacts from secrets/credentials and lists the remaining termination decisions.

### `transaction_manifest.json`

SHA-binds the generated packet and states:

- `contract_formed=false`;
- `software_rights_granted=false`;
- `payment_obligation_created=false`;
- `signatures_present=false`; and
- `human_terms_required=true`.

## Authority boundary

Agents may:

- compile the validated intake;
- materialize scope/acceptance;
- inventory technical surfaces;
- carry forward provisional owners from the intake;
- enumerate unresolved human decisions;
- validate hashes and guardrails.

Agents may **not**:

- choose or quote an actual price as an approved term;
- grant a repository/software license;
- transfer source code, provider accounts, domains, deployment assets, data rights or historical corpora;
- accept warranty/liability/privacy/SLA/support terms;
- sign or represent that either party has accepted a contract; or
- create an invoice/payment obligation.

## What AP7 proves

Internally, AP7 proves that a selected commercial path can reach a concrete scoping packet without rebuilding transaction mechanics from scratch.

It does **not** prove that a real counterparty has agreed to those terms or that a transaction is legally executable. The actual human terms and external document/signature mechanism remain the final human boundary.

## AP8 handoff

Once a real adopter has:

- completed intake;
- exercised preview/source/review/delivery as applicable; and
- reached a human-approved commercial/legal path,

AP8 should record the observed acceptance evidence and deviations. AP8 must not manufacture the missing real-world steps just to mark the program complete.