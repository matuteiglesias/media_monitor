Let’s treat the editorial part as its own subsystem, not just “the stages after acquire”.

Right now editorial is trying to do four jobs at once:

```text
1. Run PromptFlow on digest groups.
2. Convert raw LLM output into structured editorial briefs.
3. Generate drafts from those briefs, with legacy fallback.
4. Build a human handoff surface.
```

That is a valid chain, but the boundaries are still a bit soft. The main improvement is to make the editorial subsystem governed by **contracts and decision surfaces**, not by raw PromptFlow output.

---

# 1. Current editorial architecture

The current editorial lane appears to be:

```text
data/digest_jsonls/<digest_id>.jsonl
  → stage04_promptflow_run.py
  → data/pf_out/pfout_<digest_id>*.jsonl
  → stage06_build_piece_briefs.py
  → storage/buses/news_piece_brief/v1/*.jsonl
  → stage05_explode_pf_outputs.py
  → data/drafts/<digest_id>/*.jsonl
  → build_editorial_access_indexes.py
  → storage/indexes/editorial_latest.json
```

The owner wrapper currently runs:

```text
make s04
make s06
make s05
```

so it already recognizes the intended order: PromptFlow first, piece briefs second, draft generation third. 

The important new seam is `stage06_build_piece_briefs.py`: it reads PF output, extracts seed ideas, builds deterministic brief IDs, validates `news_piece_brief.v1`, and writes into `storage/buses/news_piece_brief/v1`. 

That is the right architectural direction.

---

# 2. The core editorial problem

The biggest ambiguity is that `data/pf_out/*` is still too influential.

Raw PF output is useful as a runtime artifact, but it should not be treated as the editorial truth. It is Level 0. The actual editorial contract should be:

```text
news_piece_brief.v1
```

Then drafts and handoff should flow from that.

Current `stage05_explode_pf_outputs.py` already partly does this. It reads `storage/buses/news_piece_brief/v1`, but also reads raw PF output, digest maps, drafts, and quarantine. It supports a preferred brief-based path and a fallback legacy path. 

That is okay during transition, but the architecture should say explicitly:

```text
Preferred path:
  news_piece_brief.v1 → drafts

Emergency path:
  pf_out + digest_map → drafts
```

The fallback should be noisy and measured, not silent.

---

# 3. Better target architecture

I would organize editorial around four internal products.

## E1. PromptFlow Runner

Job:

```text
digest groups → raw PF output
```

Inputs:

```text
data/digest_jsonls/<digest_id>.jsonl
```

Outputs:

```text
data/pf_out/pfout_<digest_id>*.jsonl
```

Status:

```text
runtime dependency, not editorial contract
```

Issue to fix: the stage04 file header still mentions `data/pf_in/pfin_<DIGEST_AT>.jsonl`, while the actual code uses `data/digest_jsonls/<digest_id>.jsonl`. That comment drift should be fixed immediately because it misdescribes the seam. 

---

## E2. Brief Builder

Job:

```text
raw PF output → news_piece_brief.v1
```

Inputs:

```text
data/pf_out/*
contracts/schemas/news_piece_brief.v1.json
```

Outputs:

```text
storage/buses/news_piece_brief/v1/*.jsonl
```

This is the core editorial adapter.

It should become the main promoted boundary.

Current file:

```text
stage06_build_piece_briefs.py
```

This one is probably the most strategically important editorial module.

---

## E3. Draft Builder

Job:

```text
news_piece_brief.v1 → draft artifacts
```

Inputs:

```text
storage/buses/news_piece_brief/v1/*.jsonl
data/digest_map/<digest_id>.csv, while transition lasts
```

Outputs:

```text
data/drafts/<digest_id>/*.jsonl
```

Future outputs:

```text
storage/buses/news_article_draft/v1/*.jsonl
storage/buses/news_yt_script_draft/v1/*.jsonl
```

Current file:

```text
stage05_explode_pf_outputs.py
```

But the name is now stale. It says “explode PF outputs”, while the strategic job is really:

```text
build drafts from editorial briefs
```

I would eventually rename conceptually, not necessarily physically yet:

```text
stage05_build_drafts.py
```

or:

```text
draft_builder.py
```

For compatibility, keep the old command wrapper.

---

## E4. Editorial Handoff Builder

Job:

```text
briefs + drafts + fallback evidence → human decision surface
```

Inputs:

```text
storage/buses/news_piece_brief/v1/*.jsonl
data/drafts/<digest_id>/*.jsonl
data/quarantine/*.jsonl
data/pf_out/*.jsonl, transitional only
```

Outputs:

```text
storage/indexes/editorial_latest.json
```

Current file:

```text
build_editorial_access_indexes.py
```

It computes metrics, latest briefs, draft records, fallback summaries, and action candidates. It also picks `yt_script` first when available. 

This is not just an index. It is the editorial cockpit.

---

# 4. What I would change first

Not a big refactor. A **seam-hardening pass**.

## Change 1: make `news_piece_brief.v1` the declared editorial contract

Add this to the editorial README/runbook:

```text
Raw PromptFlow outputs are not a stable editorial contract.
The promoted editorial contract is `news_piece_brief.v1`.
Downstream editorial modules should consume piece briefs whenever possible.
Legacy PF-output fallback is emergency support only.
```

That single statement clarifies the subsystem.

---

## Change 2: make the editorial owner wrapper finish with the handoff index

Current:

```bash
make s04
make s06
make s05
```

Better:

```bash
make s04
make s06
make s05
make build-editorial-access-indexes
```

Because the editorial product is not “draft files exist”. The product is:

```text
storage/indexes/editorial_latest.json
```

Without refreshing that, the human decision surface may lag behind the actual editorial run.

---

## Change 3: rename concepts before renaming files

Before changing filenames, update docs/comments with conceptual names:

```text
stage04_promptflow_run.py      = PromptFlow runner
stage06_build_piece_briefs.py  = Brief bus builder
stage05_explode_pf_outputs.py  = Draft builder with legacy fallback
build_editorial_access_indexes.py = Editorial handoff builder
```

This gives you clarity without breaking commands.

Later, if you want:

```text
stage05_explode_pf_outputs.py
```

can become a thin wrapper over:

```text
apps/news_editorial/src/news_editorial/draft_builder.py
```

---

## Change 4: make fallback policy explicit

Right now `build_editorial_access_indexes.py` counts `fallback_legacy_count` and `schema_failures`, and derives statuses like `fallback-heavy`, `degraded`, and `ok`. 

That is good. But the policy should be sharpened:

```text
fallback_legacy_count = 0
  → normal

fallback_legacy_count > 0
  → degraded / fallback-emergency

fallback_legacy_count > threshold in 24h
  → breach, do not treat new path as dominant
```

This turns fallback from a hidden rescue into a measurable migration signal.

---

## Change 5: split “draft generated” from “draft publishable”

Current drafts seem to be generated into `data/drafts/<digest_id>/*.jsonl`. That is fine, but the handoff surface should distinguish:

```text
brief-ready
draft-ready
publish-candidate
published
blocked
```

The action candidates already carry fields like `target_format`, `ready_state`, `title`, `topic`, `source`, and `path`. 

I would make `ready_state` a small enum:

```text
brief-ready
draft-ready
needs-human-edit
publish-candidate
blocked
```

Do not overbuild approval workflows yet. Just make the state machine explicit.

---

# 5. Cleaner editorial package structure

Later, inside `apps/news_editorial/src/news_editorial/`, I would aim for:

```text
news_editorial/
  promptflow_runner.py
  piece_briefs.py
  draft_builder.py
  handoff_index.py
  fallback_policy.py
  schemas.py
  paths.py
  slugs.py
```

Then the stage files become wrappers:

```text
stage04_promptflow_run.py
  → promptflow_runner.run()

stage06_build_piece_briefs.py
  → piece_briefs.run()

stage05_explode_pf_outputs.py
  → draft_builder.run()

scripts/build_editorial_access_indexes.py
  → news_editorial.handoff_index.run()
```

This keeps operational commands stable while organizing the implementation by product responsibility.

---

# 6. The future editorial buses

The current bus:

```text
news_piece_brief.v1
```

is good.

The next two useful buses are probably:

```text
news_article_draft.v1
news_yt_script_draft.v1
```

Your artifact ladder already lists them as target buses. 

That would change the editorial architecture from:

```text
brief bus → data/drafts → handoff index
```

to:

```text
brief bus
  → article draft bus
  → yt script draft bus
  → handoff index
```

Then `editorial_latest.json` can be built mostly from Level 1 buses instead of Level 0 runtime folders.

That is the clean target.

---

# 7. What not to do yet

I would not replace PromptFlow right now.

PromptFlow is ugly as an operational dependency, but it is isolated enough if you treat it as:

```text
digest_jsonls → pf_out
```

The bigger problem is not PF itself. The bigger problem is letting PF output remain the de facto contract.

Fix the contract boundary first. Then you can replace PromptFlow later without disturbing the rest of the chain.

I also would not build a CMS or approval system yet. The handoff file plus public snapshot path is enough for now.

---

# 8. A better editorial doctrine

I’d write the editorial architecture like this:

```text
The editorial subsystem converts news digest groups into human-actionable publication candidates.

It has four layers:

1. Generation runtime
   PromptFlow consumes digest groups and emits raw PF output.
   This layer is operational and replaceable.

2. Brief contract
   Raw PF output is normalized into `news_piece_brief.v1`.
   This is the primary editorial bus.

3. Draft production
   Briefs are transformed into article and YT-script draft candidates.
   Legacy PF-output fallback is allowed only as emergency support.

4. Human handoff
   `storage/indexes/editorial_latest.json` is the decision surface.
   Humans, UI, and agents should inspect this file, not raw PF output.
```

That is clear and compatible with what you already have.

---

# 9. Practical next PR

I would make the next editorial PR small:

```text
PR: Editorial seam clarification and handoff closure
```

Scope:

```text
1. Update comments/docstrings:
   - stage04 input is digest_jsonls, not pf_in.
   - stage05 is draft builder with preferred brief bus + legacy fallback.
   - stage06 is the promoted piece-brief bus builder.

2. Update run_editorial_owner.sh:
   - add `make build-editorial-access-indexes`.

3. Update editorial runbook:
   - declare `news_piece_brief.v1` as primary editorial contract.
   - declare `editorial_latest.json` as the human decision surface.
   - declare PF raw output as Level 0 runtime only.
   - declare fallback policy.

4. Add one smoke check:
   - run s04/s06/s05/build-editorial-access-indexes on a fixture or recent digest.
   - assert `storage/indexes/editorial_latest.json` exists.
```

Non-goals:

```text
No PromptFlow replacement.
No file moves.
No CMS.
No new UI.
No draft bus unless already trivial.
```

This gives you a much better editorial architecture without turning this into a large refactor.

