# PR-ODF2 closure — CSP-safe VitePress hydration

## Scope and diagnosis

This focused runtime fix changes only the public documentation frontend and its
validation. VitePress serialized the function-valued `themeConfig.editLink.pattern`
and restored it in the browser through dynamic function construction. The docs
project's restrictive Content Security Policy does not allow `unsafe-eval`, so
hydration could stop before client-side navigation attached even though static
HTML remained visible.

## Fix and evidence

- The edit-link pattern is now VitePress's declarative `:path` string form. The
  resulting link still targets the canonical file under `docs/` without
  requiring runtime function reconstruction.
- A focused isolation test prevents the edit-link configuration from returning
  to a function-valued pattern.
- Existing browser coverage verifies rendered-page changes across header,
  sidebar, card, history, deep-link, Mermaid, and mobile navigation paths.
- The CSP remains restrictive; `unsafe-eval` was not added.

No Media Monitor pipeline or publication behavior, root deployment
configuration, or `apps/news_site` file changed.

## Deployment status

The production build and local browser suite are **locally validated**. No
provider deployment is performed or claimed by this PR. Provider verification
remains a post-deployment check against the dedicated docs project.

## Carry-state proposal

Human review should accept this regression fix independently of the completed
PR-MD6 documentation program. Proposed carry-state addition:

```yaml
docs_frontend_csp_closure: context/closures/PR-ODF2.md
docs_frontend_status: locally_validated
docs_frontend_provider_verification: PENDING_HUMAN_DEPLOYMENT
```
