Great—let’s interrogate **media_monitor** with the same lens. I’ll keep it tight and evidence-based.

# Baseline questions

### What input does this system consume?

* **Google News RSS feeds** grouped by topics; fetched on an hourly anchor, then time-sliced into CSVs/JSONL.   
* **Headlines digests (.md)** produced by stage 03; later parsed into JSONL records for LLM flow. 
* **PromptFlow outputs** (`~/.promptflow/.runs/**/output.jsonl`) as intermediate LLM results. 

### What output should it produce?

* **RSS slice CSVs** (per window) and **mirror JSONL** (per hour) under `data/rss_slices/**` and `data/digest_jsonls/`. 
* **Headlines digest files**: grouped markdown per topic (and metadata JSONL via `create_digest_jsonl`).  
* **Master index CSV** (deduped on `index_id`) plus processed-files log.  
* **Exploded PF artifacts**: normalized articles/ideas JSONL, enriched with `master_ref.csv` and scraped content.  

### What loop keeps it alive (cron, script, manual run)?

* **Hourly orchestrator** `bin/run_hour.sh` (flock lock, sets `DIGEST_AT`, runs `make s01..s05`, copies PF output).   
* **Per-stage Python**:
  `01_digests.py` (fetch+slice+enqueue), `02_master_index_update.py` (roll up), `03_headlines_digests.py` (group & write md/JSONL), `04_promptflow_run.py` (pf run + save), `05_explode_pf_outputs.py` (explode & enrich).     
* **PromptFlow DAG**: parse→ideas with OpenAI connection; outputs agenda table + seed ideas.   

---

# Structural pass — Flow reconstruction

## Dependency graph (who calls/feeds whom)

* **Stage 01** fetches RSS → slices by windows → writes per-slice CSV + hourly JSONL; enqueues scrape jobs. Feeds stages 02 & 03.   
* **Stage 02** scans `rss_slices/**.csv` → adds `index_id` (reuses `uid` if present) → dedupes → updates `data/master_index.csv`.   
* **Stage 03** groups to markdown per topic/group; also composes `digest_jsonls/<id>.jsonl` for PF.  
* **Stage 04** runs PromptFlow with `flow/` jinja+python nodes → saves `data/pf_out/pfout_<id>_*.jsonl`.  
* **Stage 05** explodes PF JSONL into **articles** and **seed ideas**, merges with `master_ref.csv` and scraped content; writes enriched JSONL and draft seeds.   

## Sources vs artifacts

* **Sources**: `backend/*.py` (ids, models, db, io), `flow/*` (jinja/json schemas, DAG), `scripts/*.py`, `bin/run_hour.sh`.  
* **Artifacts (working)**: `data/rss_slices/**.csv`, `data/digest_jsonls/*.jsonl`, `data/pf_out/*.jsonl`, `data/digest_map/*.csv`, `data/status_logs/**`, `data/quarantine/**`. (See your `find` output; also written in code.)  
* **Indexes/refs**: `data/master_index.csv`, `data/master_ref.csv`, `data/scraped_links.jsonl`.  

## Trigger logic

* **Hourly cron/Timer → `bin/run_hour.sh`**: acquires lock, sets `DIGEST_AT` (UTC hour), runs s01→s03 in venv, runs PF if there’s a matching `digest_jsonls`, then s05.    
* **Manual path**: call each stage script with `DIGEST_AT=YYYYMMDDTHH` to reproduce a run; stage 04 accepts `--digest-id`.  

## Config surface

* **Env knobs** (01): `DIGEST_AT`, `DRY_RUN`, `LIMIT`, `SAMPLE`, `NULL_SINK`; deterministic hour anchoring.  
* **RSS topics/queries** in code (can be externalized). 
* **Flow DAG** declares OpenAI connection `open_ai_connection` and model `gpt-4o-mini`.  

## Failure points (concrete)

* **Silent empties**: If no `digest_jsonls/<id>.jsonl`, PF+05 are skipped; hourly loop “succeeds” without editorial payload. 
* **Filename contract**: headlines md must match the strict regex, else dropped.  
* **Index consistency**: `index_id` uniqueness is asserted; inconsistent UID/ID rules will crash 02. 
* **PF dependency**: requires a python with `promptflow` or conda env; missing env → hard error. 
* **Enrichment relies on refs**: if `master_ref.csv` or `scraped_links.jsonl` missing, 05 degrades gracefully but outputs less-rich records.  

---

# Semantic pass — Intent extraction

* **Problem this project solves**
  Turns high-volume RSS streams into **time-boxed editorial digests** and **idea seeds**: deterministic slices → grouped headlines → LLM clustering/ideas → normalized artifacts for drafting.  

* **Unit of success** (per hour)

  1. Non-empty `data/rss_slices/**.csv` + `data/digest_jsonls/<id>.jsonl`. 
  2. At least one `headlines_<window>_<id>_<Topic>_<NN>.md` produced. 
  3. PF run yields `data/pf_out/pfout_<id>_*.jsonl`. 
  4. Stage 05 writes `article_quotes/*.jsonl` and `idea_cluster/*.jsonl` enriched with refs. 

* **“Done” for one cycle**
  Fetch & slice at `DIGEST_AT` → update master index → emit headlines md + digest JSONL → PF run → explode/enrich outputs → append drafts/seeds.    

* **Reusable parts elsewhere**

  * **Anchored slicing** (deterministic `DIGEST_AT`) for any news-like stream. 
  * **UID/index_id scheme** that stabilizes dedup.  
  * **PF DAG** pattern (prompt→python) with pass-through IDs to keep joins deterministic. 

---

# Friction bullets (to carry into the brief)

* PF step conditional on data presence → easy to “green” a run with no editorial artifacts. 
* Strict filename schema for headlines; malformed names silently reduce throughput. 
* `master_index.csv` integrity hinges on consistent `index_id` rules across 01/02. 
* Environment coupling (PF python vs project venv) can misroute outputs or fail. 

# Next Unlock (bounded; imperative)

→ **Codify a single hourly “golden path”**: one `make hourly DIGEST_AT=...` that (a) runs s01→s03, (b) forces `03→digest_jsonls`, (c) always attempts PF with fallback to latest JSONL, (d) runs s05, and (e) emits a **DONE stamp** with counts (files written per stage). This removes the silent-empty class and gives you a one-glance verification (counts>0). You already have most pieces in `run_hour.sh`; just surface the counts and fail hard on 0. 

---

If you want, I can now draft the **brief** and **runbook** for `media_monitor` in your strict style (3-2-1 brief; one-screen runbook) using the findings above.

