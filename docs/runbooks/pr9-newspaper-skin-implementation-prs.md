# PR9 — Newspaper skin implementation PRs

## Contract authority

`contracts/schemas/publish_surface_v1.json` es la única autoridad del contrato público v1.

- Las únicas shapes públicas aprobadas en v1 son:
  - `frontpage.v1`
  - `topic_page.v1`
  - `story_page.v1`
  - `editorial_handoff.v1`
- Campos requeridos, opcionales y fallback deben mantenerse **solo** en ese archivo de contrato.
- Si hay conflicto entre índices actuales y UI, manda el contrato; se corrige adapter/proyección.

## Governance rules

- **Prohibido introducir nuevas shapes** hasta que exista consumidor real en ruta productiva.
- **Regla de PR:** cualquier campo nuevo debe documentar en el PR:
  1. `consumer route` (ruta productiva consumidora), y
  2. evidencia de uso real (ejecución, captura o artefacto verificable).

## Validation gate

El check operativo es `make validate-publish-surface`, que corre `scripts/validate_publish_surface.py` sobre:

- `storage/indexes/news_recent_refs_latest.jsonl`
- `storage/indexes/news_recent_groups_latest.jsonl`
- `storage/indexes/editorial_latest.json`

El comando debe fallar (exit code != 0) cuando falten archivos o el shape no cumpla contrato.
