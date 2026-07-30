# news_editorial

> **Status:** canonical component guide · **Verified against:** `7723918`

`apps.news_editorial` owns the PromptFlow adapter, topic/idea normalization, piece briefs, draft-bus writing, editorial decision index, and handoff packet. It does not own sensed facts, enrichment fetches, human approval, published-article authority, or the public site.

| Interface | Input | Output/consumer |
|---|---|---|
| PromptFlow adapter | digest groups / configured flow | raw model output in Level 0 |
| stage 06 | model seed ideas plus digest mapping | `news_piece_brief.v1` or quarantine |
| stage 05/draft writer | model output, mapping, brief/context | draft artifacts / `news_article_draft.v1` |
| editorial index | brief/draft/fallback sources | `editorial_latest.json` for operator/handoff |
| handoff module | editorial index | materialized review packet |

**Invariants:** model output is untrusted until normalized and schema-valid; source IDs and citations remain attached; invalid rows quarantine; fallback inputs are disclosed; decision indexes are derived views, not approval. Publication remains an explicit human-gated command outside this owner.

**Dependencies:** PromptFlow runtime for live generation, pandas/jsonschema, contract schemas, and acquisition mappings. **Tests:** editorial briefs pipeline, stage 06 schema, editorial index, draft generation, handoff packet, and publish-surface validation.

See [identity/provenance](../architecture/identity-provenance-and-replay.md) and [contracts](../reference/contracts-and-schemas.md).
