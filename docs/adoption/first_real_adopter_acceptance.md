# First real adopter acceptance

> **Status:** acceptance harness implemented · **no real adopter accepted by this repository packet**

## Purpose

AP8 is where the adoption program stops treating engineering readiness as adoption evidence.

The acceptance harness exists to answer one question:

> Has a real external adopter actually exercised the loop strongly enough that Media Monitor may truthfully call the cycle accepted?

The answer is **no** until the required external/human evidence exists.

## Files

- [`adopter_acceptance.schema.json`](adopter_acceptance.schema.json) — evidence record schema.
- [`adopter_acceptance.template.yaml`](adopter_acceptance.template.yaml) — deliberately pending template containing `human_evidence_required` placeholders.
- `scripts/evaluate_adopter_acceptance.py` — strict evaluator and missing-evidence reporter.

The repository does **not** contain a committed `status: accepted` adopter record.

## Evidence chain required for accepted status

An accepted record must demonstrate all of the following.

### 1. Real adopter identity

- `evidence_class=real_external`;
- non-placeholder organization and adopter reference.

Representative fixtures or simulated buyers are not enough.

### 2. Completed intake

- validated `media_monitor_adopter_intake.v1` evidence exists;
- the acceptance record SHA matches the actual validated intake bytes semantically/canonically.

### 3. Verified preview or operating identity

- real HTTPS URL, not localhost, `.invalid`, `.test`, or example-domain evidence;
- preview status verified;
- concrete site ID and commit SHA;
- adopter identity independently verified;
- owner/editor identity leakage absent;
- evidence reference recorded.

The acceptance harness does not deploy the preview itself.

### 4. Real source/input exercise

- source mode recorded;
- evidence reference recorded;
- provider/data-rights confirmation explicitly made by a human;
- successful cycles meet or exceed the intake's `minimum_successful_scheduled_cycles`.

One fixture import cannot satisfy this gate.

### 5. Non-developer operator exercise

- a non-developer operator actually used the review path;
- review cycle exercised;
- normal flow required no direct storage/database surgery;
- evidence reference recorded.

### 6. Recipient delivery

- exact artifact SHA-256 recorded;
- status is `delivered`;
- external provider/human delivery reference recorded;
- recipient confirms the artifact was useful;
- evidence reference recorded.

Preparing a brief is not delivery.

### 7. Procurement/trust exercise

- AP6 packet reviewed by an external evaluator;
- no unresolved procurement blockers remain for the accepted path;
- evidence reference recorded.

This does not mean every theoretical enterprise control must be implemented—only that the chosen path's blocking issues are resolved.

### 8. Transaction/scope acceptance

- selected commercial path recorded;
- actual scope/contract accepted;
- external document reference;
- owner acceptance reference;
- counterparty acceptance reference.

AP8 does not fill or sign those documents.

### 9. Deviations classified

Every observed deviation is classified as:

- `reusable_core`; or
- `adopter_specific`.

Any `unresolved_blocking` deviation prevents accepted status.

The evaluator can materialize separate reusable-core and adopter-specific follow-up lists so the second adoption cycle becomes materially easier.

### 10. Explicit human acceptance

- human acceptance recorded;
- accepting human identified;
- timestamp/reference note present.

Even a technically complete record cannot be accepted automatically.

## Evaluation behavior

Pending records:

```bash
python scripts/evaluate_adopter_acceptance.py \
  docs/adoption/adopter_acceptance.template.yaml \
  --output-dir /tmp/media-monitor-adopter-evaluation
```

The expected result is:

```text
accepted=false
evaluation_status=pending_real_adopter_evidence
missing_for_acceptance=[...]
```

An accepted record has an additional safety gate:

```bash
python scripts/evaluate_adopter_acceptance.py \
  <real-evidence-record.yaml> \
  --confirm-real-external-evidence
```

Without that explicit confirmation flag, even a complete `status: accepted` record is refused.

## What the evaluator cannot do

The evaluator cannot create or infer:

- a real adopter;
- a preview deployment;
- provider data rights;
- successful production cycles;
- a non-developer operator exercise;
- a real recipient delivery;
- procurement approval;
- commercial/legal acceptance or signatures; or
- human acceptance.

Those are inputs to AP8, not outputs from it.

## Program completion rule

The adoption-loop engineering harness may be complete while the **adoption program remains incomplete**.

Media Monitor may only record the first adoption cycle as accepted when a real external record passes the AP8 evaluator with explicit real-evidence confirmation.

Until then:

```text
FIRST_REAL_ADOPTER_ACCEPTANCE = PENDING
CUSTOMER_OR_ADOPTER_CLAIM = NOT_AUTHORIZED_BY_AP8
PROGRAM_COMPLETION = NOT_ALLOWED
```

That is intentional. The remaining work is real-world execution, not another internal feature packet.