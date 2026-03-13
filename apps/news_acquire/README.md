# news_acquire (wrapper placeholder)

`apps/news_acquire` is the future owner for acquisition responsibilities.

Current state (PR2):
- This folder is scaffolding only.
- Runtime acquisition still executes via legacy stages.
- Contract outputs should eventually target `storage/buses/` using versioned schemas in `contracts/schemas/`.

Contract classification relevant to acquisition:
- Stable now: `news_ref.v1`, `scrape_request.v1`, `scraped_article.v1`.
- Experimental structured: downstream editorial/enrichment contracts are not yet acquisition runtime outputs.
