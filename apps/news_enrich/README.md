# news_enrich (wrapper placeholder)

`apps/news_enrich` is the future owner for enrichment and publication-readiness workflows.

Current state (PR2):
- This folder is scaffolding only.
- Runtime remains on legacy path with PromptFlow + explode adapters unchanged.
- Migration will proceed through adapters and contract tests, not a big-bang runtime replacement.

Contract classification relevant to enrich:
- Stable now contracts provide canonical upstream references.
- Experimental structured contracts are draft interoperability surfaces pending runtime adoption.
