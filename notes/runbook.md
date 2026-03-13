---
id: 02
title: Media Monitor – Hourly News Digest ETL
last_verified: 2025-10-15
next_check: 2025-11-01
maintainer: matias
env: /home/matias/repos/media_monitor
dependencies: [python3.10, pandas, requests, openai, promptflow]
risk_level: medium
---

## 1. Purpose
Continuously scrape, cluster, and summarize news articles into hourly digest markdowns using PromptFlow and LLM templates.

## 2. Core Operations
### A. Start or Rebuild
1. Ensure environment ready:
```bash
   pip install -r flow/requirements.txt
   export $(grep -v '^#' .pf.env | xargs)
```

2. Run one loop manually:

   ```bash
   bash bin/run_hour.sh
   ```

3. Verify output:

   * `data/output_digests/headlines_4h_window_*.md` exist.
   * `data/digest_jsonls/*.jsonl` non-empty.
   * `data/digest_map/*.csv` updated.

4. Optional test cycle:

   ```bash
   make hourly-test
   ```

### B. Troubleshoot

| Symptom           | Probable cause                            | Fix                                                          |
| ----------------- | ----------------------------------------- | ------------------------------------------------------------ |
| Missing digests   | Scraper stage failed (network, RSS empty) | Check `data/rss_slices/rss_dumps/`                           |
| Empty PF outputs  | PromptFlow mis-tokenized                  | Inspect `data/pf_out/`; rerun `backend/04_promptflow_run.py` |
| Quarantined JSONL | Parse failure in stage05                  | Open `data/quarantine/` for diagnostics                      |
| DB mismatch       | `master_index.csv` stale                  | Run `backend/02_master_index_update.py` manually             |


### C. Deploy or Publish

1. Outputs appear in `data/output_digests/`.
2. Upload or sync digests to publication system if configured.
3. Append summary stats to `digests.log`.

## 3. Parameters / Config

* `.pf.env`: contains API keys, model, temperature, etc.
* `flow/flow.dag.yaml`: defines stage order.
* `makefile`: targets (`hourly`, `rebuild`, `clean`).
* SQL schemas (`sql/001_*.sql`) define persistent store (articles, runs).

## 4. Recovery Protocol

1. Stop timers or cron job.
2. Backup `/data/` directory.
3. Clear `data/quarantine/`, rerun pipeline sequentially:

```bash
python backend/01_digests.py && python backend/02_master_index_update.py ...
```
4. Compare new `master_index.csv` vs. backup to verify.

## 5. Verification Checklist

* [ ] New digest markdowns created under `/data/output_digests/`.
* [ ] `master_index.csv` timestamp <1h old.
* [ ] No quarantined JSONLs left unreviewed.
* [ ] `digests.log` contains success message.
* [ ] `.pf.env` loaded correctly.

## 6. Notes

* When stable, schedule via cron or systemd (`bin/run_hour.sh` every hour).
* Future enhancement: centralize configs + DB integration for multi-source aggregation.



