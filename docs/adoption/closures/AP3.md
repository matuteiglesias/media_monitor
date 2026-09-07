# AP3 closure — bring-your-own signal boundary

> **State:** implemented file boundary · internal evidence L1 · external-provider validation pending

## Goal

Let an adopter keep its own monitoring/source system while feeding Media Monitor's governed downstream compiler through one explicit, provenance-preserving seam.

## Implemented

- `contracts/schemas/external_monitored_signal.v1.json`
  - stable provider/adopter row contract;
  - provider/source/external identity;
  - source/title/topic/time/link;
  - observed time and source-record provenance.
- contract fixture + contract-suite registration.
- `scripts/import_external_signals.py`
  - JSONL file adapter;
  - deterministic 10-character downstream identity derived from provider/source/external identity;
  - schema validation;
  - identical-observation dedupe with count preservation;
  - fail-closed quarantine for conflicting repeated identities;
  - schema-invalid quarantine;
  - atomic output/quarantine/manifest writes;
  - input/output hashes and import counts.
- AP2 preview bootstrap now accepts `--normalized-signals` so a clean external import can feed the existing generic selection/context/site-snapshot builders.
- `tests/test_external_signal_import.py`
  - normal import;
  - deterministic identity;
  - identical duplicate collapse;
  - full quarantine of semantic identity conflicts;
  - schema-invalid quarantine;
  - end-to-end external file → normalized signals → adopter preview.
- [`external_signal_boundary.md`](../external_signal_boundary.md) documents the consumer route and trust boundary.

## Authority result

External data receives no canonical-state or publication authority merely by entering the adapter.

The import path is:

```text
external_monitored_signal.v1
  → validate
  → identity/dedupe/conflict reconciliation
  → normalized access-index fields + provenance
  → generic downstream compiler
```

Invalid or ambiguous provider facts quarantine before downstream use. The adapter cannot publish editorial content or move sensing current/generation pointers.

## Evidence level

**L1 — internally exercised.**

The implementation proves a provider-shaped fixture can pass through the import boundary and into an adopter-branded snapshot without importer/provider conditions in generic builders.

AP3 reaches L2 when a technically competent outsider maps a representative real provider export to `external_monitored_signal.v1` and completes a clean import without repository archaeology.

A continuously operating live-source claim requires repeated cycles/freshness evidence beyond AP3.

## Score effect

The external input seam improves preview feasibility and strategic-partner fit. Combined AP2/AP3 preview readiness moves provisionally to approximately **60%**, still below the 70–80% target because no isolated provider preview URL or repeatedly operating real source has been evidenced.

## Rejected overbuild

AP3 does not add:

- generic connector marketplace;
- HTTP ingestion service;
- API credentials UI;
- provider-specific hard-coded adapters;
- multi-tenant queues;
- automatic data-rights interpretation;
- source-vendor billing.

## Remaining acceptance / human-facing work

- choose a representative real external export when available;
- confirm the adopter/provider is permitted to supply and retain that data;
- map provider fields to the stable contract;
- exercise repeated cycles if a live-source claim is desired;
- combine with AP2 provider preview deployment when explicitly authorized.

## Next packet

The representative seed intake is private and requires human review, so the next bounded program packet is **AP4 — minimal analyst/reviewer operation**. AP5 remains independently justified by its requested HTML/email brief deliverable.
