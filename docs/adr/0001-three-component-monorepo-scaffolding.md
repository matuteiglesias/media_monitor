# ADR 0001: Three-component monorepo scaffolding (incremental, runtime-safe)

- Status: Accepted (PR2 scaffolding)
- Date: 2026-03-13

## Context

The repository currently has a working operational pipeline in legacy stages (`stage01..05`) with PromptFlow in the active path.
We need a 3-component monorepo structure to support explicit ownership and interoperability contracts, but we must preserve the current runtime while migration is staged.

PR2 is therefore **additive-only scaffolding and governance**:
- create monorepo layout (`apps/*`, `contracts/*`, `storage/*`, `docs/adr/*`),
- establish concrete draft schemas and tests,
- document boundaries and provenance,
- do not move/delete/replace runtime paths.

## Decision

Adopt a staged monorepo organization:
- `apps/news_acquire`
- `apps/news_editorial`
- `apps/news_enrich`

Introduce contract surfaces in `contracts/schemas` and contract compliance tests in `contracts/tests`.

Define storage boundaries:
- `storage/raw/*` private internals,
- `storage/buses/*` versioned integration seams,
- `storage/indexes/*` compact read models,
- `storage/snapshots/*` publication/export artifacts.

## Stable vs experimental classification

### Stable now

- `news_ref.v1`
- `scrape_request.v1`
- `scraped_article.v1`

### Experimental structured

- `news_digest_group.v1`
- `news_topic_cluster.v1`
- `news_seed_idea.v1`
- `news_seed_card.v1`

## Runtime safety / non-goals in PR2

PR2 does **not**:
- replace legacy runtime,
- replace PromptFlow,
- standardize runtime telemetry/run-record API behavior,
- perform broad file moves or deletions.

Observed drift is explicitly acknowledged: `backend.db.finish_run` signature differs from some stage call patterns (`stage=` / `meta=` kwargs). Runtime run-record standardization remains future work.

## Contract provenance mapping (current repo -> contract)

| Contract | Status | Current source object(s) | Field provenance / transforms |
|---|---|---|---|
| `news_ref.v1` | Stable | `data/master_ref.csv` and `data/digest_map/<digest_id>.csv` written in `legacy/stage02_master_index_update.py` | `index_id/source/link/first_seen/last_seen/topics/meta` from master_ref; `digest_file/article_id` from digest_map; `join_key` = `digest_file::article_id` documented seam. |
| `scrape_request.v1` | Stable | planning seam consumed by scrape path (e.g., `articles_to_scrape` records) + stage02 mapping fields | request identity from `digest_id_hour/index_id/topic/source/title/original_link/published`; carry `digest_file/article_id`; derive `join_key`. |
| `scraped_article.v1` | Stable | `backend.models.ScrapeRecordV1` (+ scraped JSONL outputs) | Field names and constraints aligned to `ScrapeRecordV1` core fields and enums. |
| `news_digest_group.v1` | Experimental structured | `legacy/stage03_headlines_digests.py` `digest_jsonls` records | uses existing operational seam fields: `digest_group_id/window_type/topic/group_number/content`; includes `digest_id_hour`. |
| `news_topic_cluster.v1` | Experimental structured | PF clustered agenda output consumed in `legacy/stage05_explode_pf_outputs.py` | maps cluster structure (`topic`, `article_ids`, `deduplicated_titles`) with `digest_group_id`. |
| `news_seed_idea.v1` | Experimental structured | PF generated seed-idea style outputs | draft structured representation for interoperable idea exchange before runtime standardization. |
| `news_seed_card.v1` | Experimental structured | flow/editorial seed-card style artifacts | draft card packaging contract; explicitly experimental and not yet runtime-backed end-to-end. |

## Stable ID rule carried forward

`index_id` remains canonical from `backend/ids.py` (`stable_index_id`): base32-encoded SHA1 digest truncated to 10 characters. PR2 documents and reuses this invariant; it does not redefine it.

## KB-contracts governance authorities used

This ADR follows KB-contracts authority model from:
- Intro: <https://kb-contracts.matuteiglesias.link/docs/intro>
- Integration seams + allowed IO (authority hub)
- Stable IDs + naming rules (authority hub)
- Manifests + integrity rules (authority hub)
- Run record contract (authority hub)
- Storage boundaries + adapter policy (authority hub)
- Contract compliance tests (authority hub)

(These are governance constraints for migration planning; PR2 scaffolding does not claim runtime conformance closure.)

## Consequences

- Teams can start building adapters around explicit schemas without breaking current production path.
- Consumers can target `contracts/` + future `storage/indexes/` rather than private legacy internals.
- Future PRs can migrate responsibilities incrementally behind tested seams.
