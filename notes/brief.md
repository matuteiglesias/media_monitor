---
id: 02
title: Media Monitor – Automated News & Digest Pipeline
heartbeat: daily
status: in_build
last_touch: 2025-10-15
next_review: 2025-10-20
tags: [etl, scraping, llm, promptflow, automation]
impact: high
confidence: high
dependencies: [SUC01, SUC44]
---

## 1. Current State
- Modular backend rebuilt (01–05 stages now under `/backend`).
- Pipeline runs hourly via `bin/run_hour.sh`; produces digest MD files and JSONLs.
- PromptFlow templates operational (`flow/01–03_*.jinja2`), DAG defined in `flow.dag.yaml`.

## 2. Friction
- Mixed legacy code (`legacy/`) may cause confusion or redundant runs.
- `.pf.env` contains sensitive vars; no `.env` loader standardization yet.
- Occasional PF output explosion errors (`data/quarantine/V05_*.jsonl`).
- Directory permissions for `data/output_digests/` occasionally block writes.

## 3. Next Unlock
→ Verify the hourly job loop under controlled conditions:
1. Run `make hourly-test` (local dry run).
2. Inspect `data/output_digests` and confirm new `.md` digests appear.
3. Check logs for PF response explosion handling.

## 4. Evidence / Links
- scripts: `backend/01_digests.py` → `05_explode_pf_outputs.py`
- runner: `bin/run_hour.sh`
- config: `flow/flow.dag.yaml`
- output: `data/output_digests/`
- monitor: `digests.log`

## 5. Notes / Debris
- Long-term: integrate Meilisearch bootstrap (`scripts/meili_bootstrap.py`) as post-publish step.
