# P0-C3 editorial rehearsal pack

This pack takes P0-C3 to the final pre-publication gate without manufacturing a human approval.

## Candidate set

Three current Argentina-economy drafts were written from primary INDEC evidence available on 2026-08-24:

1. `c3-trade-july-2026` — July trade surplus and the price/quantity decomposition of the export/import change.
2. `c3-cpi-july-2026` — July CPI at 2.1% m/m, framed with explicit restraint about persistence.
3. `c3-retail-june-2026` — June real retail weakness across supermarkets and wholesale self-service stores.

The candidate rows are complete `news_article_draft.v1` objects with source links, structured citations, fact-check flags and revision notes.

## Simulated editorial judgment

`review_ledger.json` is deliberately marked `SIMULATED_HUMAN_JUDGMENT`.

The rehearsal decisions are:

- **SIMULATED_APPROVE** — trade: strongest analytical value and primary-source coverage.
- **SIMULATED_APPROVE** — CPI: publishable short analytical note; optional composition enrichment.
- **SIMULATED_REVISE** — retail: relevant signal, but needs stable technical-report links and more contextual evidence before a real analytical approval.

These decisions are editorial QA, not publication authority.

## Machinery proof

Run:

```bash
python scripts/rehearse_c3_editorial_tranche.py --output-dir /tmp/media-monitor-c3
```

The rehearsal:

1. validates every candidate against `news_article_draft.v1`;
2. validates that every review decision is explicitly simulated;
3. sends only `SIMULATED_APPROVE` candidates through the real `promote()` implementation;
4. redirects the resulting `published_article.v1` records to an isolated rehearsal bus;
5. rebuilds published-article indexes from that isolated bus;
6. labels the resulting review status `simulated_human_judgment_not_publication_approval`;
7. restores the real production bus path without touching it.

The existing production CLI remains authoritative and still refuses publication unless `--approve-human` is explicitly supplied.

## Exit condition

After this rehearsal is green, C3 machinery is ready for a real first tranche. The only action intentionally left undone is the actual human publication decision. A real approval would promote the chosen draft(s) through the existing gate, rebuild `published_article` indexes, and let `site_snapshot.v2`/P0-C2 expose them as approved analysis.

This pack is sufficient to continue to P0-D without weakening the publication boundary.
