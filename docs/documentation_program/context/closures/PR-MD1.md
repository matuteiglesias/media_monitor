# PR-MD1 documentation closure

- **Status:** ACCEPTED
- **Repository commit inspected:** `858a717d60ac913656663de1b2bc8af67e48875f`
- **Documentation paths changed:** `README.md`, `docs/README.md`, program carry state, and closure records
- **Human acceptance required:** received in the follow-up instruction

## Goal completed

Added one audience- and task-oriented documentation front door and made the root front door route to it without duplicating detailed runbooks. Added an evidence-bounded capability/status matrix and corrected front-door claims that did not match current entrypoints or npm scripts.

## Source truth inspected

- root `README.md` and `Makefile`;
- owner READMEs, runbooks, source entrypoints, and `bin/run_minimal_loop_once.sh`;
- contract schemas/tests and storage/index/snapshot writers;
- sensing run-bundle, compactor, task adapters, focused tests, Dockerfile, and AWS Terraform/deployment scripts;
- publication, site snapshot, site-roll source/tests, `apps/news_site/package.json`, and current publishing runbooks;
- PR-MD0 inventory and historical/supporting documentation surfaces.

## Documents produced or changed

- Added `docs/README.md` as the current documentation router.
- Kept the root README concise while linking the router.
- Corrected the root enrich route to the owner entrypoint and explicitly recorded the broken compatibility-loop branch.
- Corrected the root aggregate news-site publication claim to match missing npm scripts.
- Recorded human acceptance of PR-MD0 and proposed PR-MD2 without pre-accepting it.

## Commands and links verified

```text
python -m pytest contracts/tests/test_contracts.py tests/test_sensing_run_bundle.py tests/test_sensing_compactor.py tests/test_news_enrich_service.py tests/test_news_editorial_briefs_pipeline.py tests/test_build_site_snapshot.py tests/test_roll_site.py
npm --prefix apps/news_site run test:refresh-data
node --test apps/news_site/scripts/validate_site_snapshot.test.mjs
apps/news_enrich/entrypoints/run_enrich_owner.sh --dry-run
python <local relative-Markdown-link checker>
git diff --check
```

No artifact-writing, AWS, or Vercel command was run. Provider-side operation remains unverified.

## Drift found

- `bin/run_minimal_loop_once.sh --lane enrich` invokes absent `scripts/06_scrape_enrich.py`; the owner entrypoint exists and is now the front-door route.
- `scripts/publish_news_site.sh` invokes npm scripts `refresh-data` and `smoke:public-data`, neither defined by `apps/news_site/package.json`.
- `docs/runbooks/README.md` links missing `docs/current_state.md` and still promotes PR-numbered documents as active entrances.
- The acquisition runbook retains the already-recorded pre-Terraform statement.

## Decisions made

- Route to the best current supporting source while planned canonical capability pages do not yet exist.
- Display broken or externally dependent paths as gaps instead of implying validation.
- Keep the root golden path short and move audience/status navigation into `docs/README.md`.
- Preserve all historical and PR-era documents for later classified migration.

## Known limitations

- Capability-oriented architecture, component, reference, and operations pages remain future bounded PRs.
- The status matrix is manually maintained until PR-MD6 adds documentation checks.
- Provider-side AWS/Vercel state was neither inspected nor changed.

## Proposed carry update

- `next_pr`: `PR-MD2` after human acceptance
- blockers: none known; acceptance of PR-MD1 is required
- reader-facing change: one coherent root-to-docs entrance with honest status and task routing
- maintenance obligation: code PRs changing entrypoints or evidence status must update the front-door matrix
