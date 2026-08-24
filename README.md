# 🗞️ Media Monitor

[![Runtime contracts](https://github.com/matuteiglesias/media_monitor/actions/workflows/runtime-ci.yml/badge.svg)](https://github.com/matuteiglesias/media_monitor/actions/workflows/runtime-ci.yml)

`media_monitor` es un **sistema desplegado y gobernado de inteligencia de noticias y publicación editorial**.

Su objetivo es separar con contratos explícitos cuatro cosas que suelen mezclarse en sistemas de medios asistidos por IA:

1. **señales externas monitoreadas**;
2. **selección determinística de qué importa ahora**;
3. **contexto observado de cobertura**;
4. **análisis editorial propio**, que sólo existe públicamente después de aprobación humana explícita.

La generación asistida nunca equivale a publicación. `published_article.v1` continúa detrás de un gate humano.

## Verlo funcionando

- **Outlet canónico actual:** https://mediamonitor-psi.vercel.app
- **Health público:** https://mediamonitor-psi.vercel.app/api/health
- **Para periodistas:** https://mediamonitor-psi.vercel.app/journalists
- **Metodología:** https://mediamonitor-psi.vercel.app/methodology
- **Documentación técnica:** [`docs/README.md`](docs/README.md)

Existe un cutover preparado hacia `https://media.matuteiglesias.link`, pero el host de Vercel sigue siendo canónico hasta que DNS, HTTPS y paridad de snapshot estén verificados. Ver [`OWNED_DOMAIN_CUTOVER.md`](OWNED_DOMAIN_CUTOVER.md).

**“Live” no significa simplemente que una URL responda.** La superficie sólo debe describirse como corriente cuando `/api/health` informa `freshness_status=FRESH`, `is_current=true` y `within_target=true`.

No se enlaza todavía un “artículo representativo” como si estuviera human-approved cuando esa aprobación pública no existe. El repositorio sí contiene una tranche de aceptación aislada que ejercita objetos `human_approved` sin convertirlos en decisiones editoriales públicas.

## Prueba local en un comando

Después de instalar las dependencias Python del repositorio:

```bash
python -m pip install -r requirements-sensing.txt jsonschema
bin/media demo
```

El comando construye dos veces el mismo outlet de fixture y exige el mismo `snapshot_id`. No usa red, LLM, base de datos ni credenciales de deployment.

Salida:

```text
.demo/media-monitor/
├── demo_manifest.json
├── site_snapshot.json
├── README.txt
└── storage/indexes/
    ├── news_recent_refs_latest.jsonl
    ├── news_recent_groups_latest.jsonl
    ├── editorial_selection_latest.json
    ├── story_contexts_latest.jsonl
    └── published_articles_latest.jsonl
```

Los datos son deliberadamente ficticios y están marcados `DETERMINISTIC_FIXTURE_NOT_LIVE_NEWS`. El propósito es demostrar la arquitectura, no simular actualidad real.

## Arquitectura en una pantalla

```mermaid
flowchart LR
    A[Fuentes RSS / públicas] --> B[news_acquire]
    B --> C[news_ref.v1 + digest groups]
    C --> D[access indexes]
    D --> E[editorial_selection.v1\nno LLM]
    D --> F[story_context.v1]
    E --> F
    D --> G[news_editorial\nbriefs + drafts]
    G --> H{aprobación humana}
    H -->|sí| I[published_article.v1]
    H -->|no| J[hold / revise]
    D --> K[site_snapshot.v4]
    E --> K
    F --> K
    I --> K
    K --> L[Next outlet]
    L --> M[/api/health + sitemap + feeds + OG/JSON-LD]
```

Principio de autoridad:

```text
monitoreado ≠ seleccionado ≠ generado ≠ aprobado ≠ publicado
```

Cada transición tiene un contrato o gate explícito.

## Qué demuestra el repositorio

| Capacidad | Evidencia principal |
|---|---|
| Ingesta y sensing reproducible | `apps/news_acquire/`, run bundles, buses versionados |
| Contratos interoperables | `contracts/schemas/` |
| Curation determinística | `editorial_selection.v1`, `scripts/build_editorial_selection.py` |
| Contexto de cobertura | `story_context.v1`, `scripts/build_story_contexts.py` |
| Gate editorial humano | `scripts/promote_draft_to_published.py` |
| Publicación inmutable | `published_article.v1` + `site_snapshot.v4` |
| Freshness truth | `/api/health`, `publication_health.v1` |
| Discoverability | sitemap, robots, feeds separados, metadata y JSON-LD |
| Operación | scheduled guarded refresh + crawler/social acceptance |
| Reproducibilidad para adopters | `bin/media demo` |

## Superficies públicas deliberadamente separadas

### Análisis propio

Sólo objetos `published_article.v1` con estado publicado y aprobación humana pueden aparecer como análisis de Media Monitor.

### Qué importa ahora

`editorial_selection.v1` prioriza señales externas de forma determinística usando frescura, prioridad temática y diversidad. Selección no implica autoría.

### Cable cronológico

`signals.latest` conserva la secuencia temporal de señales externas monitoreadas.

### Contexto de historia

`story_context.v1` agrega cobertura observada, fuentes relacionadas, ventanas y relación con la shortlist sin generar interpretación editorial.

## Entrypoints para distintos usuarios

### Quiero entender o reutilizar el sistema

1. Ejecutar `bin/media demo`.
2. Leer este README.
3. Ir al [mapa de documentación](docs/README.md).
4. Inspeccionar `contracts/schemas/` y `sites/`.

### Quiero operar este deployment

```bash
bin/media status --target production
bin/media doctor --target preview
bin/media publish --target preview --digest-at YYYYMMDDTHH
```

Las lanes de adquisición/enriquecimiento/editorial siguen disponibles mediante `bin/run_minimal_loop_once.sh`, pero ya no son el punto de entrada recomendado para un newcomer.

### Quiero entender el frontend público

```text
apps/news_site/
├── app/                 rutas Next
├── config/              identidad pública/editorial
├── lib/adapter/         consumo del snapshot
└── public/data/         snapshot de deployment generado
```

## Ownership y límites

- `apps/news_acquire` posee adquisición y sensing.
- `apps/news_enrich` posee scrape/enrichment.
- `apps/news_editorial` posee briefs/drafts, **no publicación**.
- promotion + published indexes poseen la frontera de aprobación.
- snapshot builders poseen el read model público.
- `apps/news_site` presenta contratos compilados; no debe inventar hechos upstream.

La integración entre owners ocurre por buses, índices y snapshots versionados, no por imports cruzados oportunistas.

## Estado de producción vs. fixtures

El repositorio contiene tres clases de evidencia y las mantiene separadas:

- **producción:** datos/snapshots materializados por el pipeline real;
- **rehearsal/toy acceptance:** objetos realistas aislados para probar gates y consumidores;
- **demo:** fixtures completamente determinísticos para adopters.

Ninguna fixture puede presentarse como contenido editorial público real.

## CI como contrato ejecutable

`Runtime contracts` prueba, entre otras cosas:

- schemas y buses;
- publicación y gate humano;
- selección determinística;
- story contexts;
- snapshot/publication semantics;
- freshness;
- crawler/social surface;
- owned-domain cutover;
- el demo offline reproducible;
- typecheck del outlet Next.

Los cambios visuales/documentales del docs-site tienen además su workflow de aislamiento propio.

## Estructura del repositorio

```text
apps/                 owners de runtime y sitio
bin/                  entrypoints humanos
config/               políticas reutilizables
contracts/schemas/    contratos de integración
sites/                 configuración de outlets
docs/                  arquitectura, runbooks y decisiones
scripts/               builders/validators/operación
storage/               runtime local generado (gitignored)
tests/                 contratos y acceptance tests
legacy/                arqueología/compatibilidad explícita
```

## Desarrollo y contribución

Por ahora, empezar por:

```bash
python -m pytest -q tests/test_adopter_demo.py
bin/media demo
```

La guía formal de contribución y el ejemplo de “crear otro outlet” se añaden en los siguientes paquetes P1-F2/F3.

## Principios de diseño

- No agregar un orquestador sin un consumidor real.
- No confundir selección con autoría.
- No confundir generación con aprobación.
- Preferir contratos explícitos y builders determinísticos.
- Falla cerrada en publicación, identidad y provenance.
- Mantener el deployment de Argentina como **una instancia** del sistema, no como la definición del sistema.

Para operación profunda, migraciones, archaeology y runbooks, comenzar en [`docs/README.md`](docs/README.md).
