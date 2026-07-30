# PR-MDF0 closure — public documentation frontend

## Outcome

**DEPLOYMENT_READY / BLOCKED_EXTERNAL**

The separate static VitePress frontend is implemented and locally validated.
No Vercel CLI, token, linked project, project URL, or domain was available in
the execution environment, so this record makes no public-deployment claim.
The documentation production carry state remains unchanged; this optional
presentation track does not revise acceptance of PR-MD6.

## Reader problem solved

Evaluators, operators, and contributors now have a curated public edition with a
clear end-to-end route, capability navigation, fuzzy local search, responsive
sidebars/outline, technical rendering, status honesty, and direct canonical
source editing rather than an unfiltered repository document dump.

## Architecture and content policy

`docs-site/scaffold` owns presentation, navigation, design, reusable components,
and public route landings. `scripts/sync-content.mjs` copies only curated
capability roots from canonical `docs/` into ignored `.generated/site`, emits a
public route manifest and exclusion report, and fails if outside-root canonical
content is missing. VitePress builds the combined tree into ignored `dist/`.
There is no second committed authored copy of canonical pages.

The public set includes architecture, component owners, operations, reference,
case studies, and maintenance. Program prompts/state/closures, notes, legacy and
PR-era runbooks, raw storage/data, evidence, environment files, Terraform state,
and snapshots remain excluded. The public replacement for the internal docs
router is explicit in the exclusion report.

## Visual and interaction evidence

The theme uses warm paper/navy/rust in light mode and charcoal in dark mode,
editorial system-serif display type, compact sans-serif metadata, square dossier
cards, rules, pipeline motifs, and an original local signal/publication SVG. It
adds status, lane, and artifact-flow components; five semantic callout styles;
Mermaid SSR/static output; local fuzzy search; light/dark controls; curated
navigation; GitHub edit links; last-updated support; clean URLs; and a custom
404. Focus-visible styling, reduced-motion handling, responsive 390px rules,
semantic links/headings, VitePress skip navigation, and no external fonts are
included.

A browser automation/screenshot binary was not present, so no screenshots were
fabricated. Static output and preview HTTP checks verified the homepage, one
route in each required technical area, and the custom 404. Browser-only manual
review (search interaction, sidebar, theme toggle, keyboard order, and exact
390px visual capture) remains a minimal reviewer/deployment handoff item.

## Isolation proof

The existing root `vercel.json` and the news-site package, lockfile, and Next
configuration were hashed into the check baseline and remained unchanged. The
new `docs-site/vercel.json` has no rewrites or functions and cannot own `/web`,
`/web/data`, or publication runtime behavior. A built-output scan found no
publication endpoint request.

## Commands and results

- `cd docs-site && npm ci` — passed; npm reported four dependency audit findings
  (three moderate, one high) for review.
- `npm run check` — passed: 27 canonical routes, 35 rendered pages, 59 explicit
  exclusions; links, metadata, routes, unsafe paths, and deployment isolation
  checked.
- `npm run build` — passed with VitePress 1.6.4; Mermaid rendered during SSR;
  Rollup warned about a chunk larger than 500 kB.
- `npm run preview -- --host 127.0.0.1 --port 4173` plus `curl` — key routes 200;
  unknown route 404 with the custom title.
- protected-file `git diff --exit-code` — passed.
- built-output `/web/data`/publication-request scan — passed with no matches.

## Exact external handoff

Create a **new** Vercel project from `matuteiglesias/media_monitor`, set Root
Directory to `docs-site`, enable **Include source files outside of the Root
Directory in the Build Step**, use `npm run build` and output `dist`, and keep
production branch `main`. Optionally set `DOCS_SITE_URL`. Then link only that
project, create a preview, execute the route/browser checklist, and independently
confirm the existing Media Monitor deployment. Exact dashboard and CLI steps
are in `docs-site/README.md`.

## Scope and non-goals

No sensing, enrich, editorial, approval, publication, contract, storage,
snapshot, Make target, news-site, root Vercel, AWS, or provider semantics were
changed. No provider deployment was attempted or claimed.

## Proposed carry-state change

None. Preserve `docs/documentation_program/carry_state_v0_1.yaml` pending human
review. Track Vercel project creation, preview URL, screenshots, and manual
browser review as the external acceptance step for this presentation track.
