# news_editorial (wrapper placeholder)

`apps/news_editorial` is the future owner for editorial grouping and idea generation.

Current state (PR2):
- This folder is scaffolding only.
- Runtime editorial processing still executes via legacy stages (`stage03`/`stage04`/`stage05`).
- Existing seams (digest JSONL, PF outputs, digest-map joins) remain operational while contracts are formalized.

Contract classification relevant to editorial:
- Stable now inputs: `news_ref.v1`, `scrape_request.v1`, `scraped_article.v1`.
- Experimental structured outputs: `news_digest_group.v1`, `news_topic_cluster.v1`, `news_seed_idea.v1`, `news_seed_card.v1`.
