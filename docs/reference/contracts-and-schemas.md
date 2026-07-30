# Contracts and schemas

> **Status:** canonical reference · **Authority:** `contracts/schemas/*.json` and fixtures/tests · **Verified against:** `7723918`

| Contract | Producer authority | Primary consumer/job |
|---|---|---|
| `news_ref.v1` | acquire exporter | news indexes, joins, site inputs |
| `news_digest_group.v1` | acquire exporter | editorial/PromptFlow, group indexes |
| `scrape_request.v1` | acquire/export seam | enrich worker/service |
| `scraped_article.v1` | enrich bus writer | enrich index/downstream editorial context |
| `news_topic_cluster.v1` | PromptFlow normalization | seed/brief generation |
| `news_seed_idea.v1` | PromptFlow normalization | seed-card/brief path |
| `news_seed_card.v1` | seed compiler | editorial development |
| `news_piece_brief.v1` | editorial stage 06 | draft generation/handoff |
| `news_article_draft.v1` | editorial draft writer | human review/promotion |
| `news_yt_script_draft.v1` | editorial script producer | human review |
| `published_article.v1` | explicit human-gated promotion | published indexes/public site |
| `publish_surface_v1` | publish-surface validator projection | publication gate |
| `site_snapshot.v1` | site snapshot builder | validator/Next.js/health |

Schemas are the field/type/enum authority; `contracts/tests/fixtures` are executable examples, not production inputs. A producer must validate before crossing an owner boundary. Consumers must reject unknown schema names/unsupported versions rather than guessing. Identity and provenance fields are summarized in [identity/provenance/replay](../architecture/identity-provenance-and-replay.md).

Verification: `python -m pytest contracts/tests/test_contracts.py`.
