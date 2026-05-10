# Handoff memo: monorepo News / Media Monitor

Este memo resume el estado actual de `media_monitor` para continuidad operativa sin romper runtime.

## Estado del repositorio

- El repo evolucionó de pipeline legacy a monorepo con tres dominios: `news_acquire`, `news_editorial`, `news_enrich`.
- La arquitectura objetivo existe (apps, contracts, storage), pero la operación canónica aún corre por `bin/run_hour.sh` + `make s01..s05`.
- `legacy/` permanece como capa de compatibilidad (wrappers), no como zona primaria de nueva lógica.

## Modelo mental correcto

Trabajar con dos capas en paralelo:

1. **Runtime efectivo actual**: `bin/run_hour.sh`, `make s01..s05`, wrappers legacy, datos operativos en `data/`.
2. **Arquitectura objetivo**: implementación por dominio en `apps/*/src/*`, contratos en `contracts/schemas/`, exports target en `storage/`.

Evitar asumir “migración 100% completa”. El estado real es una transición gobernada.

## Semáforo por dominio

- **Acquire**: más maduro (amarillo tirando a verde).
- **Editorial**: estructuralmente correcto pero dependiente de PromptFlow y su conexión local (amarillo).
- **Enrich**: modularizado, aún con necesidad de endurecimiento operativo (amarillo).

## PromptFlow: riesgo operativo clave

- `flow/` sigue siendo seam editorial real.
- La conexión `open_ai_connection` debe existir en el runtime local de PromptFlow.
- Variables de entorno no siempre alcanzan; validar connection store/keyring y runtime Python efectivo.
- Distinguir fallas de código vs fallas de configuración/runtime de PromptFlow.

## Contratos y buses (postura recomendada)

Priorizar superficies públicas mínimas y estables:

- `news_ref.v1`
- `news_digest_group.v1`
- `news_topic_cluster.v1` (con cautela de shape)
- `article_draft.v1` / `news_draft.v1`
- `scraped_article.v1`

No promover todavía como bus público:

- `pf_out` crudo
- colas/work items de ejecución
- artefactos internos de staging

## Principios de trabajo para siguientes PRs

- No hacer refactors masivos ni reemplazo big-bang.
- Mantener compatibilidad de wrappers mientras se cierra la migración.
- Cerrar loops operativos: observabilidad, smoke checks por módulo, taxonomy de fallos, manifests e índices útiles.
- Usar contratos versionados como frontera entre módulos/sistemas.

## Rutas de inspección rápida

- Runtime: `bin/run_hour.sh`, `makefile`
- Acquire: `apps/news_acquire/README.md`, `apps/news_acquire/runbook.md`, `apps/news_acquire/src/news_acquire/`
- Editorial: `apps/news_editorial/README.md`, `apps/news_editorial/runbook.md`, `apps/news_editorial/src/news_editorial/`, `flow/`
- Enrich: `apps/news_enrich/README.md`, `apps/news_enrich/runbook.md`, `apps/news_enrich/src/news_enrich/`
- Contratos: `contracts/README.md`, `contracts/schemas/`
- Storage: `storage/README.md`

## Frase guía

`media_monitor` está en consolidación post-migración: la arquitectura objetivo ya existe y está parcialmente implementada con código real; el trabajo útil ahora es cerrar la brecha entre ownership modular, operación cotidiana, exports estables y observabilidad.
