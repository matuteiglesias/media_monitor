# Media Monitor Artifact Ladder

## Level 0 — Runtime workspace

Path:
- `data/*`

Examples:
- `data/rss_slices/rss_dumps/*.csv`
- `data/slices/jsonl/*.jsonl`
- `data/digest_map/*.csv`
- `data/digest_jsonls/*.jsonl`
- `data/pf_out/*.jsonl`
- `data/drafts/<digest>/*.jsonl`
- `data/quarantine/*.jsonl`

Rule:
Only runtime stages, adapters, and transitional decision indexes may read Level 0.

## Level 1 — Contract buses

Path:
- `storage/buses/*`

Current buses:
- `news_ref.v1`
- `news_digest_group.v1`
- `news_piece_brief.v1`

Target buses:
- `news_article_draft.v1`
- `news_yt_script_draft.v1`
- maybe `scraped_article.v1`

Rule:
New module-to-module integrations should use Level 1.

## Level 2 — Access / decision indexes

Path:
- `storage/indexes/*`

Current indexes:
- `news_recent_refs_latest.jsonl`
- `news_recent_groups_latest.jsonl`
- `editorial_latest.json`
- `pr3a_exports_latest.json`
- `pr3a_export_compact_latest.json`

Rule:
Humans, UI, agents, and publication validators should use Level 2.

## Level 3 — Public snapshots

Path:
- `web/data/*`
- `apps/news_site/public/data/*`

Rule:
Public/demo surfaces consume only hardened public snapshots.



                     ┌────────────────────────────┐
                     │ U1 news_acquire             │
                     │ RSS → slices / digest data  │
                     └──────────────┬─────────────┘
                                    │
                                    ▼
                         Level 0: data/*
                                    │
                                    ▼
                     ┌────────────────────────────┐
                     │ U2 bus_exporter             │
                     │ data → storage/buses        │
                     └──────────────┬─────────────┘
                                    │
                         Level 1: storage/buses
                                    │
             ┌──────────────────────┴──────────────────────┐
             ▼                                             ▼
             ┌────────────────────────────┐              ┌────────────────────────────┐
             │ U3 news_access_index_builder│              │ U4 promptflow_runner        │
             │ buses → news indexes        │              │ digest group → PF output    │
             └──────────────┬─────────────┘              └──────────────┬─────────────┘
                    │                                             │
                    ▼                                             ▼
            Level 2: storage/indexes                   Level 0: data/pf_out
                                                             │
                                                             ▼
                                                ┌────────────────────────────┐
                                                │ U5 piece_brief_builder      │
                                                │ PF output → piece brief bus │
                                                └──────────────┬─────────────┘
                                                               │
                                                   Level 1: news_piece_brief
                                                               │
                                                               ▼
                                                ┌────────────────────────────┐
                                                │ U6 draft_builder            │
                                                │ briefs → drafts             │
                                                └──────────────┬─────────────┘
                                                               │
                                                               ▼
                                                ┌────────────────────────────┐
                                                │ U7 editorial index builder  │
                                                │ mixed state → handoff index │
                                                └──────────────┬─────────────┘
                                                               │
                          ┌──────────────────-─────────────────┘
                          ▼
             ┌────────────────────────────┐
             │ U8 publish_surface_validator│
             │ validates latest indexes    │
             └──────────────┬─────────────┘
                            ▼
                ┌────────────────────────────┐
                │ U9 public_snapshot_builder  │
                │ internal index → safe public│
                └──────────────┬─────────────┘
                               ▼        
        Level 3: web/data / public app data