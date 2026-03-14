# Contracts (PR2)

Draft-but-concrete contracts for incremental migration.

## Stable now

- `news_ref.v1`
- `scrape_request.v1`
- `scraped_article.v1`
- `public_contract_v1` (`contracts/schemas/publish_surface_v1.json`) con solo `frontpage.v1`, `topic_page.v1`, `story_page.v1`, `editorial_handoff.v1`.

## Experimental structured

- `news_digest_group.v1`
- `news_topic_cluster.v1`
- `news_seed_idea.v1`
- `news_seed_card.v1`
- `news_piece_brief.v1`
- `news_article_draft.v1`
- `news_yt_script_draft.v1`

## Provenance rule

Each contract is grounded in current repository seams/models and is validated by fixture-based contract tests in `contracts/tests/test_contracts.py`.


## Public v1 governance

- No se permiten nuevas shapes públicas hasta tener consumidor real en ruta productiva.
- Cualquier campo nuevo requiere `consumer route` y evidencia de uso en el PR.
