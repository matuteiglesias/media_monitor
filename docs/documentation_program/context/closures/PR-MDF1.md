# PR-MDF1 closure — docs deployment isolation

## Outcome

**LOCALLY VALIDATED / DEPLOYMENT_READY / PROVIDER EVIDENCE PENDING**

The docs production check now enforces a semantic product boundary rather than
raw hashes of sibling deployment files. It validates the docs Vercel config,
authored-content source, build controls, route manifest, and emitted paths.
Canonical documentation may describe the news component, while no news runtime
path, snapshot file, `/web` route, package build, or root Vercel configuration
is consumed or emitted by the docs project.

GitHub PR validation owns the separate change-ownership question. With base and
head SHAs it uses a three-dot Git diff and rejects changes to root
`vercel.json`, `apps/news_site/**`, and explicitly owned publication/site
snapshot deployment scripts. Missing SHA context is an explicit non-failing
skip, so Vercel and local production builds do not depend on PR metadata.

## Ownership and deployment handoff

The documentation product is repository `matuteiglesias/media_monitor`, Vercel
Root Directory `docs-site`, outside-root sources enabled, build command
`npm run build`, and output directory `dist`. Any Vercel CLI link must name and
resolve to a docs-only project in `docs-site/.vercel/project.json`; `.vercel/`
remains ignored. The existing news project retains its root configuration,
`/web` behavior, and news-site ownership and must not be relinked or redeployed.

## Evidence and external blocker

Local checks covered clean install, content/build isolation, production build,
harmless docs-config formatting/newline normalization, synthetic protected-path
failure, and docs-only diff success. Built paths and requests were scanned for
news runtime exposure. Browser smoke covered representative routes, navigation,
Mermaid output, and request isolation.

No Vercel credential, confirmed docs project link, or provider URL was available
in this environment. Therefore no deployment was attempted, no URL is recorded,
and the existing news deployment was not touched. Provider-side docs build and
independent news URL confirmation remain the exact external acceptance step.

## Dependency risk

`npm audit --json` reported three moderate findings and one high finding:
direct `vitepress` (moderate) and `vitepress-plugin-mermaid` (moderate), plus
transitive `esbuild` (moderate) and `vite` (high). npm offered no compatible
fix for any finding. The advisories affect the documentation development/build
server dependency graph (including upstream VitePress and Mermaid integration),
not the static `dist` output or the news/pipeline runtime. No forced audit fix
or breaking framework upgrade was used; upstream remediation remains residual
risk to track.

## Scope and carry proposal

Root `vercel.json`, `apps/news_site`, sensing, editorial, publication routes,
snapshots, and pipeline semantics are unchanged. This focused frontend fix does
not alter the main documentation-program acceptance state. Human review owns
acceptance; propose recording PR-MDF1 as the latest optional docs-frontend
closure while preserving the current canonical program carry state.
