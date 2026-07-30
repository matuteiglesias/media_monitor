# PR-ODF1 closure — VitePress navigation and Mermaid runtime

## Scope and diagnosis

This focused regression fix changes only the public documentation frontend and
its validation. Browser instrumentation covered console errors, uncaught page
errors, failed requests, clean deep routes, history, desktop and 390 px mobile
navigation, the custom 404, and Mermaid before and after route changes.

The generated hrefs, VitePress `cleanUrls`, Vercel clean URLs, and CSP are
consistent and did not require broadening. The runtime risk was the third-party
Mermaid Vue component: its asynchronous mount, document-wide mutation observer,
and unconditional observer teardown could race route unmount and interfere with
client navigation. The integration was replaced, not the diagrams or site
architecture.

## Fix and evidence

- Mermaid is pinned directly and rendered by a small route-safe component.
- Teardown is idempotent, stale asynchronous renders cannot update an unmounted
  page, theme observation is limited to the root class, and Mermaid uses strict
  security mode.
- Browser checks render every public Mermaid page. A standalone Node parser
  fixture was not retained because Mermaid's parser requires browser DOMPurify
  hooks for these labels; the browser assertion is the deterministic gate.
- A Chromium Playwright suite verifies URL and H1 changes, RouteCard/header/
  sidebar/in-document links, Back/Forward, deep-link reload, custom 404, SVG in
  light/dark mode, post-diagram navigation, and mobile navigation. It fails on
  console errors, uncaught page errors, and relevant failed requests.
- The docs-site workflow installs only Chromium and runs the browser smoke after
  the production build.

## Deployment status

Local production preview: **locally validated**. No Vercel credentials or linked
project configuration were present, so provider preview verification is
**BLOCKED_EXTERNAL**. After review, deploy `docs-site` with the existing Vercel
project and run:

```bash
cd docs-site
DOCS_PREVIEW_URL=https://<preview-host> npm run test:browser
```

Record the preview URL in the PR evidence. Do not claim deployed or operated
status until that command passes against the provider URL.

## Carry-state proposal

Human review should accept this regression fix independently of the completed
PR-MD6 documentation program. Proposed carry-state addition:

```yaml
docs_frontend_regression_closure: context/closures/PR-ODF1.md
docs_frontend_status: locally_validated
docs_frontend_provider_verification: BLOCKED_EXTERNAL
```
