# Guía para Codex: sprint "newspaper skin" sobre `next-contentlayer`

## Contexto

Construir la capa pública del medio con **Next.js + Contentlayer + Tailwind**, usando `shadcn/next-contentlayer` como base técnica, y `web3templates/stablo` solo como referencia visual. El contenido debe venir del pipeline existente, no de un CMS nuevo.

**Ruta canónica:**

`news in -> brief -> draft -> human last mile -> published site`

## Restricciones duras

1. **No CMS nuevo**: no Sanity, no Wisp, no DB editorial paralela.
2. **No mover source of truth**: la web consume artefactos compactos del sistema actual.
3. **No big refactor** de acquire/editorial/enrich.
4. **No wrappers ornamentales**: cada capa nueva debe reducir ambigüedad real.
5. **Repos externos permitidos con control**: solo para extraer patrones/layout o copiar componentes puntuales.

## Repos externos permitidos

### Base técnica preferida

- `shadcn/next-contentlayer`

### Referencia estética opcional

- `web3templates/stablo` (solo layout/componentes; no Sanity)

### Referencia secundaria

- Templates de Vercel (patrones, no gobernanza)


## Comparación práctica con `shadcn/next-contentlayer`

`shadcn/next-contentlayer` encaja como base técnica de shell (App Router + Tailwind + estructura limpia), pero su flujo por defecto usa MDX/Contentlayer como fuente principal de posts. En este repo eso **no** debe gobernar la salida editorial pública.

Regla operativa:

- **Sí**: reutilizar estructura de app, layout, estilos y componentes de presentación.
- **No**: usar `content/posts` + `allPosts` como verdad editorial del outlet.
- **Sí condicional**: Contentlayer solo para páginas estáticas auxiliares (about/help), nunca para feed/handoff.


## Entregables que debe producir Codex

### 1) Arquitectura mínima del sitio

Propuesta tipo:

- `apps/news_site/` (o equivalente claro)
- `app/`
- `components/`
- `lib/`
- `public/`
- `scripts/` (si hace falta compactar snapshots)

> El contenido editorial dinámico no se define en MDX manual como fuente primaria.

### 2) Adapter seam explícito

Definir y documentar consumo de artefactos, por ejemplo:

- `storage/indexes/news_recent_refs_latest.jsonl`
- `storage/indexes/news_recent_groups_latest.jsonl`
- `storage/indexes/editorial_latest.json`
- snapshots de drafts listos para publish

Si hay transformación intermedia, debe ser mínima, local y con contrato claro.

### 3) Newspaper skin

Prioridades de UI:

- portada con hero
- rail de últimas noticias
- bloques por topic/category
- artículo individual
- listado por tema
- navegación sobria y grilla editorial densa
- espacio para `analysis`, `latest`, `video`, `opinion` (aunque algunos sean placeholders iniciales)

### 4) Plan de pruning

Inventario explícito de qué parte del template:

- se usa
- se omite
- se archiva
- se elimina

Evitar “template bloat”.

## Preguntas obligatorias antes de tocar código

1. ¿Cuál es el source of truth exacto para la capa pública?
2. ¿Qué archivos actuales alcanzan para una portada útil hoy?
3. ¿Falta dato, mapping o skin?
4. ¿Qué partes del template externo son reutilizables sin arrastrar CMS?
5. ¿Cuál es la ruta más corta a una portada viva?

## Criterios de decisión

Cada cambio debe responder **sí** a todo esto:

- ¿Reduce ambigüedad en la ruta canónica?
- ¿Acerca a “human last mile sobre generated drafts”?
- ¿Mantiene contracts como autoridad?
- ¿Evita segunda gobernanza editorial?
- ¿Facilita publicar hoy?

## Tareas permitidas

### Sí

- inspeccionar/clone de `shadcn/next-contentlayer` y `stablo`
- copiar componentes UI selectivos
- construir app Next.js mínima
- conectar lectores de índices compactos
- usar fixtures/mocks temporales claramente marcados
- documentar qué se importó y qué se descartó

### No

- introducir Sanity o CMS alterno
- mover source of truth al frontend
- importar ecosistema completo sin pruning
- rediseñar backend pipeline

## Orden sugerido del sprint

### PR-1 — Bootstrap sitio público mínimo

- app Next.js local
- layout base
- home simple
- consumo de `news_recent_refs_latest.jsonl` y `news_recent_groups_latest.jsonl`

### PR-2 — Newspaper skin

- hero, latest rail, topic blocks
- shell de artículo y categoría
- tipografía + spacing editorial

### PR-3 — Editorial handoff surface

- lectura de `editorial_latest.json`
- vista de briefs/drafts listos
- prioridad YT-first si existe señal

### PR-4 — Pruning + canonización

- limpieza de template bloat
- README operativo corto
- truth table: source-of-truth / adapter / UI / historical

## Forma de entrega esperada por PR

- objetivo
- por qué importa ahora
- scope exacto
- non-goals
- done criteria
- riesgos
- evidencia runtime/screenshots
- lista de archivos importados de repos externos
- componentes usados vs descartados

## Prompt corto para pegar en Codex

```text
Context:
We are building a semi-automated editorial outlet. The canonical architecture is contracts-first and runtime-first. The public site must consume compacted outputs from the existing system, not create a new source of truth.

Primary technical base:
- shadcn/next-contentlayer as preferred frontend shell
Secondary visual reference:
- web3templates/stablo for layout inspiration only
Do not adopt Sanity or any new CMS.

North:
news in -> brief -> draft -> human last mile -> published site

Hard constraints:
- no new CMS
- no new editorial DB
- no changing source of truth
- no big refactor of acquire/editorial/enrich
- no fluffy wrappers
- keep compatibility with KB contracts mindset

You are allowed to inspect external repos/templates, but only to:
- extract layout/page patterns
- copy selected UI components
- compare structure
- derive a minimal local implementation

Do:
1. Propose the smallest viable public site architecture.
2. Identify the exact current files/indexes to consume.
3. Build a minimal newspaper-style frontend surface.
4. Keep the adapter seam explicit between indexes/contracts and UI.
5. Prefer a clean golden path over flexibility.

Do not:
- introduce Sanity, Wisp, or another CMS
- move source of truth into the frontend
- import whole template ecosystems without pruning
- redesign the backend pipeline

Output format:
- Reassessment
- Proposed PRs (max 4)
- For each PR: goal, why now, scope, non-goals, done criteria, risks
- Explicit note on which external repo files/components you would reuse
```

## Ejecución inmediata en este repo

Para pasar de guía a ejecución, seguir `docs/runbooks/pr9-newspaper-skin-implementation-prs.md`, que traduce esta guía a PRs concretos con scope, non-goals, checks y done criteria.

## Cierre

Usar templates como material, no como autoridad arquitectónica.
