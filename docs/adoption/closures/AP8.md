# AP8 closure — first real adopter acceptance evidence

> **Status:** acceptance harness implemented · L1 · **first real external adopter acceptance remains pending**

## Objective

Replace simulated buyer pressure with observed adopter evidence, while making it impossible for internal engineering progress alone to masquerade as real adoption.

## Implemented

- `docs/adoption/adopter_acceptance.schema.json` — structured evidence record;
- `docs/adoption/adopter_acceptance.template.yaml` — committed pending template only;
- `scripts/evaluate_adopter_acceptance.py` — strict evidence evaluator;
- `tests/test_adopter_acceptance.py` — refusal/acceptance-gate tests;
- `docs/adoption/first_real_adopter_acceptance.md` — operator/evaluator rules.

## Critical truth boundary

No committed adopter record has `status: accepted`.

The repository therefore makes **no claim that Media Monitor currently has a real accepted adopter/customer through AP8**.

The only accepted-status exercise in tests is generated under a temporary test directory and explicitly identified as synthetic unit-test evidence. It exists solely to prove the evaluator's logic and is never committed as adoption evidence.

## Accepted-status requirements

The evaluator requires, among other evidence:

- `evidence_class=real_external`;
- completed validated intake with matching canonical SHA;
- verified real HTTPS preview/operating URL and identity checks;
- source/provider evidence, human rights confirmation, and enough repeated successful cycles to meet the intake acceptance requirement;
- non-developer operator exercise without storage/database surgery;
- real delivered recipient artifact with exact SHA, provider reference, and recipient usefulness confirmation;
- external procurement review with no unresolved blockers for the selected path;
- accepted scope/contract plus external owner/counterparty acceptance references;
- no `unresolved_blocking` deviations; and
- explicit human acceptance evidence.

Even when all evidence fields are complete, a `status: accepted` record is refused unless the evaluator is invoked with `--confirm-real-external-evidence`.

## Internal tests

Focused tests prove that:

- the committed pending template remains not accepted and reports missing evidence;
- `representative_test` cannot claim accepted status;
- complete accepted evidence still requires the explicit confirmation flag;
- intake SHA drift blocks acceptance;
- unresolved blocking deviations block acceptance;
- reserved/example preview URLs block acceptance; and
- pending evaluations split deviations into reusable-core backlog versus adopter-specific follow-ups without claiming acceptance.

## Evidence level

The **acceptance harness** is L1/internal.

The **first real adopter acceptance is L0/pending because no real external adoption record has yet passed the harness**.

Do not increase closure scores or claim program completion because AP8 tooling exists.

## Program state after AP8 engineering

The AP0–AP8 engineering path is now materially encoded, but the adoption program has crossed into a different type of work:

```text
engineering readiness -> real external execution -> observed evidence -> human acceptance
```

No additional generic engineering packet should be created merely to avoid doing the real-world exercise.

## Human/external work now required

The first adopter cycle must actually provide the missing L2+/external evidence across AP0–AP8:

- outsider understands the offer;
- outsider completes intake;
- adopter preview is actually deployed/verified;
- provider/source path is exercised repeatedly with rights confirmed;
- non-developer operator performs the review cycle;
- recipient receives and uses the deliverable;
- evaluator/procurement reviews the trust packet;
- real scope/commercial/legal path is accepted; and
- a human records final acceptance.

Only then may the AP8 evaluator authorize an accepted-adopter claim and program-completion state.