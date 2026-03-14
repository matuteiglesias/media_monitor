# PR9 — Newspaper skin implementation PRs

## Contract authority

`contracts/schemas/publish_surface_v1.json` es la autoridad del contrato de publicación.

- Adapters deben mapear datos internos a este schema y **no** introducir campos obligatorios fuera del contrato.
- UI debe consumir este shape canónico y tratar sus valores fallback como comportamiento esperado, no como errores de parsing.
- Si hay conflicto entre shape actual de índices y la UI, manda este schema; primero se corrige adapter/proyección.

## Canonical objects

### `FrontpageItem`

- **Obligatorios:** `digest_at`, `title`, `topic`, `published_at`, `link`.
- **Opcionales:** `source`, `index_id`.
- **Fallback behavior:**
  - `digest_at` -> `"unknown"`
  - `title` -> `"(untitled)"`
  - `topic` -> `"unknown"`
  - `published_at` -> `"1970-01-01T00:00:00Z"`
  - `source` -> `"unknown"`
  - `index_id` -> `""`
  - `link` no tiene fallback (si falta, falla validación).

### `Story`

- **Obligatorios:** `id`, `title`, `topic`, `link`.
- **Opcionales:** `source`, `published_at`.
- **Fallback behavior:**
  - `id` -> usar `index_id`; si falta, resolver en adapter con hash de `link`.
  - `title` -> `"(untitled)"`
  - `topic` -> `"unknown"`
  - `source` -> `"unknown"`
  - `published_at` -> `"1970-01-01T00:00:00Z"`
  - `link` no tiene fallback.

### `TopicPage`

- **Obligatorios:** `digest_at`, `topic`, `window_type`.
- **Opcionales:** `group_number`, `article_count`, `top_titles`.
- **Fallback behavior:**
  - `digest_at` -> `"unknown"`
  - `topic` -> `"unknown"`
  - `window_type` -> `"unknown"`
  - `group_number` -> `0`
  - `article_count` -> `0`
  - `top_titles` -> `[]`

### `EditorialHandoffItem`

- **Obligatorios:** `target_format`, `ready_state`, `title`, `topic`.
- **Opcionales:** `priority`, `source`, `path`.
- **Fallback behavior:**
  - `target_format` -> `"article"`
  - `ready_state` -> `"unknown"`
  - `title` -> `topic` o `"(untitled)"`
  - `topic` -> `"unknown"`
  - `priority` -> `"normal"`
  - `source` -> `"unknown"`
  - `path` -> `""`

## Validation gate

El check operativo es `make validate-publish-surface`, que corre `scripts/validate_publish_surface.py` sobre:

- `storage/indexes/news_recent_refs_latest.jsonl`
- `storage/indexes/news_recent_groups_latest.jsonl`
- `storage/indexes/editorial_latest.json`

El comando debe fallar (exit code != 0) cuando falten archivos o el shape no cumpla contrato.
