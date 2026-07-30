# Editorial human last mile

> **Status:** canonical runbook · **Owner:** human reviewer and publication tooling · **Verified against:** `e068f5a`

## Preflight and review

Build/reconcile the editorial index and handoff for one digest; inspect briefs, draft, citations/source links, fallback inputs, quarantine, and fact-check flags. A decision index is not approval.

```bash
make build-editorial-access-indexes DIGEST_AT=YYYYMMDDTHH
make materialize-editorial-handoff
make diagnose-editorial DIGEST_AT=YYYYMMDDTHH
```

## Approve and publish

Select exactly one valid `DRAFT_ID`; review rendered content and provenance, then explicitly cross the human gate:

```bash
make promote-draft DRAFT_ID=<reviewed-id>
make build-published-article-indexes
# equivalent combined target: make publish-article DRAFT_ID=<reviewed-id>
```

## Reconcile/failure

Require one schema-valid published record with matching draft/digest/story group, `review_status=human_approved`, citations/source links, stable article ID/slug, and rebuilt indexes resolving that article. Run publish-surface validation before deployment. Missing sources, multiple draft matches, non-draft status, schema error, unexplained fallback, or absent explicit approval is a stop. Correct the draft through editorial revision; do not hand-edit published indexes. Rollback is a new reviewed publication/removal policy decision, not deletion of approval evidence.
