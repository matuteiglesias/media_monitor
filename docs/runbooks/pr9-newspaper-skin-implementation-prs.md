# PR9 — Newspaper skin implementation PRs

## Contexto

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

- La decisión de activar/postergar PR-4 se toma por evidencia operativa, no por preferencia arquitectónica.
- Cualquier activación debe registrarse en el decision log.

## Decision log

| Fecha | Gatillo | Evidencia | Decisión |
|---|---|---|---|
| YYYY-MM-DD | (1) filesystem / (2) caching-TTL / (3) multi-cliente | Link a incidente, métrica o ticket | Activar API / Postergar API |
