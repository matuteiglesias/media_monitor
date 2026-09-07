# Bring-your-own monitored-signal boundary

> **Status:** AP3 implemented file boundary · internally exercised · not a universal provider connector or live API service

## Purpose

An adopter may already own monitoring infrastructure, vendor feeds, analyst-curated clips or another source system. Media Monitor should not require that adopter to replace its acquisition stack in order to use the governed downstream selection/context/publication machinery.

AP3 therefore defines one narrow boundary:

```text
external provider / adopter source system
        ↓
external_monitored_signal.v1 JSONL
        ↓
scripts/import_external_signals.py
        ↓
normalized monitored-signal/access-index JSONL
        ↓
selection → context → preview/publication compiler
```

This is an integration seam, not a promise to support every provider format directly.

## Input contract

Every input row must satisfy [`external_monitored_signal.v1`](../../contracts/schemas/external_monitored_signal.v1.json).

Required identity and evidence fields include:

- `provider_id`;
- `source_id`;
- `external_id`;
- `source_name`;
- title/topic/published timestamp/link;
- `observed_at`;
- provider/source-system provenance with `record_id`.

Provider-specific exports should be mapped to this boundary before entering the generic downstream compiler.

## Deterministic identity

The adapter derives Media Monitor's downstream `index_id` from:

```text
sha256(provider_id \x1f source_id \x1f external_id)[:10]
```

This makes the same provider identity stable across repeated imports while avoiding dependence on provider-native ID shape.

## Dedupe and conflict semantics

Repeated rows with the same provider/source/external identity and the same semantic signal content deduplicate. The normalized row records how many duplicate observations were collapsed.

If the same identity carries **different semantic content**, all occurrences for that identity are quarantined with `identity_conflict`. The adapter does not choose a winner.

Schema-invalid rows are likewise quarantined.

This is intentional fail-closed behavior: a provider-side identity collision should not silently rewrite what Media Monitor believes the monitored signal was.

## Output fields

Accepted rows contain the downstream fields already understood by the generic selection/context/snapshot path:

```text
index_id
digest_at
title
topic
published_at
link
source
external_provenance
```

`external_provenance` keeps the provider/source/external identity, observed time, source-record provenance, content hash and duplicate-observation count attached to the normalized row.

## Example

Prepare JSONL of contract-valid rows, then run:

```bash
python scripts/import_external_signals.py \
  provider-export.jsonl \
  --digest-at 20260115T12 \
  --output .demo/adopter/import/normalized.jsonl \
  --quarantine .demo/adopter/import/quarantine.jsonl \
  --manifest .demo/adopter/import/manifest.json \
  --require-clean
```

The import writes only to the paths supplied by the caller.

A clean normalized file can then feed the AP2 preview compiler:

```bash
python scripts/bootstrap_adopter_preview.py \
  docs/adoption/adopter_intake.example.yaml \
  --normalized-signals .demo/adopter/import/normalized.jsonl \
  --output .demo/adopter/preview
```

The preview remains explicitly non-deployed. Importing one file does not prove a continuously operating live source connection.

## Trust boundary

External rows have **no direct state authority**.

They may affect the isolated normalized output only after:

1. JSON parsing;
2. `external_monitored_signal.v1` validation;
3. deterministic identity construction;
4. duplicate/conflict reconciliation;
5. explicit quarantine of invalid/conflicting rows.

The adapter does not:

- write canonical sensing generations/current pointers;
- publish editorial content;
- bypass human publication approval;
- mutate Vercel/AWS/provider state;
- fetch arbitrary provider APIs;
- infer data rights or retention permissions.

Those remain separate responsibilities.

## Import manifest

Each import records:

- input SHA-256;
- row counts;
- accepted/quarantined counts;
- duplicate observations;
- conflicting identities;
- output/quarantine hashes;
- identity rule;
- exact paths and digest identity.

This is sufficient to make an isolated pilot import auditable without pretending the provider export is canonical Media Monitor history.

## Evidence level

AP3 has **L1 — internally exercised** evidence through contract fixtures, importer tests, dedupe/conflict/quarantine tests, and the end-to-end external-file → adopter-preview path.

L2 requires a technically competent outsider/provider to map a real representative export to the contract and successfully produce the normalized output without internal repository knowledge.

A true live-source claim additionally requires repeated ingestion cycles and source freshness/identity evidence; this file boundary alone does not establish that state.
