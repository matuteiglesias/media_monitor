SHELL := /bin/bash
# Project python (stages 01/02/03/05)
PYTHON := ./.venv/bin/python
# PF python (PromptFlow CLI lives here; usually your conda "new_env")
PF_PYTHON ?= python

export PYTHONPATH := $(PWD)
-include .env
export

# ------------ Knobs ------------
HOUR      ?= $(shell date -u +%Y%m%dT%H)
DIGEST_AT ?= $(HOUR)
DRY_RUN   ?= 0
LIMIT     ?= 200
SAMPLE    ?=
NULL_SINK ?= 0
PF_MODE   ?= legacy           # legacy=new digest_jsonls | new=pf_in
FLOW_DIR  ?= ./flow
PF_RUNS   ?= $(HOME)/.promptflow/.runs

# ------------ Helpers ------------
define _env_prefix
DIGEST_AT=$(DIGEST_AT) DRY_RUN=$(DRY_RUN) LIMIT=$(LIMIT) SAMPLE=$(SAMPLE) NULL_SINK=$(NULL_SINK)
endef

.PHONY: help hour env s01 s02 s03 s04 s05 prep pf explode all stage-any scrape-one requeue-fails ls pf-ls clean-null

help:      ## Show help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' Makefile | sed 's/:.*## / — /' | sort

hour:      ## Print current UTC hour bucket
	@echo $(HOUR)

env:       ## Print effective env knobs
	@echo "DIGEST_AT=$(DIGEST_AT)  DRY_RUN=$(DRY_RUN)  LIMIT=$(LIMIT)  SAMPLE=$(SAMPLE)  NULL_SINK=$(NULL_SINK)  PF_MODE=$(PF_MODE)"
	@echo "PYTHON=$(PYTHON)  PF_PYTHON=$(PF_PYTHON)  FLOW_DIR=$(FLOW_DIR)"

ls:        ## Quick listing of hour-scoped artifacts
	@echo "== rss_dumps =="; ls -1 data/rss_slices/rss_dumps/*_$(DIGEST_AT)00.csv 2>/dev/null || true; \
	 echo "== digest_map =="; ls -1 data/digest_map/$(DIGEST_AT).csv 2>/dev/null || true; \
	 echo "== digest_jsonls =="; ls -lh data/digest_jsonls/$(DIGEST_AT).jsonl 2>/dev/null || true; \
	 echo "== pf_in =="; ls -lh data/pf_in/pfin_$(DIGEST_AT).jsonl 2>/dev/null || true; \
	 echo "== pf_out =="; ls -1 data/pf_out/pfout_$(DIGEST_AT)*.jsonl 2>/dev/null || true; \
	 echo "== drafts =="; ls -1 data/drafts/$(DIGEST_AT)/*.jsonl 2>/dev/null || true; \
	 echo "== quarantine =="; ls -1 data/quarantine 2>/dev/null | sed 's/^/ - /' || true

clean-null: ## Remove null-sink temp outputs
	@rm -rf data/_tmp/null || true

# ------------ Stage targets (canonical) ------------
s01:       ## Stage 01 — digests pull & slice (no heavy work)
	@$(_env_prefix) $(PYTHON) -m legacy.stage01_digests

s02:       ## Stage 02 — master index update + digest_map
	@$(_env_prefix) $(PYTHON) -m legacy.stage02_master_index_update

s03:       ## Stage 03 — headlines digests (build grouped JSONL + MD)
	@$(_env_prefix) $(PYTHON) -m legacy.stage03_headlines_digests


# Trim PF_MODE once (prevents "legacy           " issues)
PF_MODE := $(strip $(PF_MODE))

s04:       ## Stage 04 — PromptFlow run via CLI (conda env)
	@set -euo pipefail; \
	legacy_file="data/digest_jsonls/$(DIGEST_AT).jsonl"; \
	article_file="data/pf_in/pfin_$(DIGEST_AT).jsonl"; \
	mode="$(PF_MODE)"; infile=""; \
	if [ "$$mode" = "legacy" ]; then \
	  infile="$$legacy_file"; \
	elif [ "$$mode" = "new" ]; then \
	  infile="$$article_file"; \
	else \
	  if [ -s "$$legacy_file" ] && grep -m1 -q '"id_digest"' "$$legacy_file" && grep -m1 -q '"content"' "$$legacy_file"; then \
	    infile="$$legacy_file"; \
	  elif [ -s "$$article_file" ] && grep -m1 -q '"digest_id_hour"' "$$article_file"; then \
	    infile="$$article_file"; \
	  else \
	    echo "[s04] No suitable PF input for DIGEST_AT=$(DIGEST_AT)"; \
	    echo "      looked for $$legacy_file (digest-level) and $$article_file (per-article)"; \
	    exit 0; \
	  fi; \
	fi; \
	if [ "$(DRY_RUN)" = "1" ]; then \
	  echo "[s04] DRY_RUN=1 → would run PF with $$infile"; \
	  exit 0; \
	fi; \
	if [ ! -s "$$infile" ]; then \
	  echo "[s04] PF input missing/empty: $$infile"; \
	  exit 0; \
	fi; \
	echo "[s04] PF input: $$infile"; \
	$(PF_PYTHON) -m promptflow._cli.pf run create --flow $(FLOW_DIR) --data "$$infile"; \
	out_jsonl="$$(find '$(PF_RUNS)' -type f -path '*/flow_outputs/output.jsonl' -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)"; \
	if [ -z "$$out_jsonl" ] || [ ! -f "$$out_jsonl" ]; then \
	  echo "[s04] Could not locate PF output.jsonl under $(PF_RUNS)"; \
	  exit 1; \
	fi; \
	ts="$$(date -u +%H%M%S)"; dest="data/pf_out/pfout_$(DIGEST_AT)_$${ts}.jsonl"; \
	mkdir -p data/pf_out; cp "$$out_jsonl" "$$dest"; \
	echo "[s04] PF output copied → $$dest"

pf-legacy:  ## Force PF over digest-level file
	@$(MAKE) s04 PF_MODE=legacy

pf-article: ## Force PF over per-article pfin file
	@$(MAKE) s04 PF_MODE=new




s05:       ## Stage 05 — explode PF outputs → drafts + enqueue generate
	@$(_env_prefix) $(PYTHON) -m legacy.stage05_explode_pf_outputs

# ------------ Pipelines ------------
prep:      ## 01+02 on fixed hour (safe defaults DRY_RUN=1)
	@DIGEST_AT=$(DIGEST_AT) DRY_RUN=1 $(PYTHON) -m legacy.stage01_digests && \
	 DIGEST_AT=$(DIGEST_AT) DRY_RUN=1 $(PYTHON) -m legacy.stage02_master_index_update

pf:        ## Run PromptFlow once for the hour (direct CLI)
	@$(MAKE) s04

explode:   ## Join+validate drafts for the hour
	@$(MAKE) s05

all:       ## 01 → 02 → 03 → 04 → 05 (respecting DRY_RUN/NULL_SINK)
	@$(MAKE) s01 && $(MAKE) s02 && $(MAKE) s03 && $(MAKE) s04 && $(MAKE) s05

# ------------ Run any stage by number ------------
stage-any: ## Run any stage by number: make stage-any STAGE=03
	@if [ -z "$(STAGE)" ]; then echo "STAGE is required (01..05)"; exit 2; fi; \
	case "$(STAGE)" in \
	  01) MOD=legacy.stage01_digests ;; \
	  02) MOD=legacy.stage02_master_index_update ;; \
	  03) MOD=legacy.stage03_headlines_digests ;; \
	  04) echo "Use: make s04 (PF CLI)"; exit 2 ;; \
	  05) MOD=legacy.stage05_explode_pf_outputs ;; \
	  *)  echo "Unknown STAGE=$(STAGE) (expected 01..05)"; exit 2 ;; \
	esac; \
	echo ">> Running $$MOD with DIGEST_AT=$(DIGEST_AT)"; \
	$(_env_prefix) $(PYTHON) -m $$MOD

# ------------ Misc ops ------------
scrape-one:   ## Replay one index_id through scraper: make scrape-one KEY=UI4BXXNXW3
	@$(PYTHON) scripts/replay_job.py --stage scrape --key $(KEY) $(ARGS)

requeue-fails: ## Requeue failures in the last 24h: make requeue-fails STAGE=generate
	@$(PYTHON) scripts/requeue_failed.py --stage $(STAGE) --since 24h

pf-legacy:  ## Force PF over digest-level file
	@$(MAKE) s04 PF_MODE=legacy

pf-article: ## Force PF over per-article pfin file
	@$(MAKE) s04 PF_MODE=new