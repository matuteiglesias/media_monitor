# Media Monitor documentation frontend

This package is a presentation-only VitePress project. Canonical authored
documentation stays in repository-root `docs/`; `npm run sync` combines the
curated public subset with `scaffold/` in ignored `.generated/site`. Builds land
in ignored `dist/`. The sync produces `public-route-manifest.json` and
`exclusion-report.json` for review.

## Local commands

Requires Node 20 or 22:

```bash
npm ci
npm run dev
npm run sync
npm run check
npm run build
npm run preview
```

`check` validates governed metadata, local links, unique routes, section
coverage, excluded-path leakage, deployment isolation, and unsafe generated
paths. VitePress also fails the production build on dead links. Search is a
local, build-generated fuzzy index; no publication runtime endpoint is used.
Production isolation is structural: the check verifies the docs configuration,
content source, route manifest, build commands, and emitted paths. It does not
freeze sibling news-project files by byte hash. On pull requests, GitHub Actions
separately diffs the base and head commits and rejects a docs-frontend change
that also touches root Vercel, `apps/news_site/**`, or owned publication/snapshot
deployment scripts. Without base/head SHAs that guard reports a skip and does
not break a local or Vercel production build.

## Public-content policy

The site publishes capability-oriented architecture, component, operations,
contract/reference, case-study, and maintenance pages. Documentation-program
state, prompts and closures; notes; legacy/PR runbooks; raw data/storage;
provider evidence; environment files; Terraform state; and generated snapshots
are excluded. An exclusion report makes that boundary inspectable. Links from a
published canonical page to a non-public Markdown page fail the content check;
repository source/contract links are deliberately sent to GitHub.

## Separate Vercel project — required setting

> **The build reads `../docs`. In Vercel, “Include source files outside of the
> Root Directory in the Build Step” must be enabled. The sync fails explicitly
> when canonical docs are unavailable.**

> **Stop if the Vercel log says `Detected Next.js`, installs the `news-site`
> package, or runs `validate_site_snapshot.mjs`. That proves the deployment is
> targeting the existing publication project/root, not this docs project. Do
> not change that project's root to compensate: cancel the deployment and
> create/import a separate project with Root Directory `docs-site`. A correct
> log installs `@media-monitor/docs-site` with `npm ci` and runs VitePress.**

Create a new project without linking or changing the existing publication
project:

| Setting | Value |
|---|---|
| Repository | `matuteiglesias/media_monitor` |
| Project | explicit docs-only project (for example `media-monitor-docs`) |
| Root Directory | `docs-site` |
| Include source files outside Root Directory | enabled |
| Install Command | `npm ci` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Production Branch | `main` |

Optionally set `DOCS_SITE_URL=https://media-monitor-docs.<owner-domain>` to emit
the canonical sitemap hostname. Do not add rewrites to `/`, `/web`, `/web/data`,
or any news-site/publication route. `docs-site/vercel.json` defines only static
output, headers, clean URLs, and immutable hashed-asset caching; it contains no
functions.

### Exact dashboard/CLI handoff

Dashboard: **Add New → Project → Import repository → Root Directory
`docs-site` → enable outside-root source files → configure commands above →
Deploy**. After dashboard project creation, a scoped preview can be created with:

```bash
cd docs-site
npx vercel link --project media-monitor-docs
npx vercel --preview
```

Do not run the preview command from the repository root and do not select the
existing news-site/publication project when `vercel link` prompts. Before
deploying, inspect `.vercel/project.json` (ignored) and confirm its project ID is
the newly created docs-only project. `.vercel/` must remain ignored and must not
be committed. If a root-level link already exists, the
explicit `cd docs-site` boundary is mandatory.

The existing news/publication project remains separate. It keeps its current
root/project configuration, owns root `vercel.json` and `/web` publication-data
behavior, and must never use `docs-site/vercel.json`. Do not relink or redeploy
that project while deploying docs.

Verify `/`, `/architecture/system-overview`, `/operations/sensing-run-bundles`,
`/reference/contracts-and-schemas`, `/case-studies/aws-immutable-sensing-retrofit`,
and an unknown path. Promote only that docs deployment after review. Confirm the
pre-existing Media Monitor URL and `/web/data` behavior independently; this
project must never own them.

## Visual rationale

Warm paper, navy ink, rust signal accents, editorial serif headings, compact
datelines, column rules, and square dossier cards distinguish the field manual
without compromising technical tables, code, Mermaid diagrams, or small-screen
reading. The local SVG mark combines layered copy and a signal rail. System font
stacks avoid font-CDN requests. Focus rings, contrast, skip navigation inherited
from VitePress, reduced motion, responsive layouts, and semantic component
markup provide the accessibility baseline.
