# PR9 — Newspaper skin: PRs reales a ejecutar

Este runbook convierte la guía estratégica en una secuencia de PRs **ejecutables hoy** para llegar a una superficie pública viva sin romper la ruta canónica:

`news in -> brief -> draft -> human last mile -> published site`

## Objetivo operativo

Publicar una primera versión de sitio tipo “news outlet” que:

1. Lea artefactos compactos existentes.
2. Mantenga `media_monitor` como source-of-truth editorial.
3. Sea desplegable de forma incremental (PRs pequeños, reversibles, con evidencia runtime).

---

## Supuestos y seam canónico

### Source-of-truth

- Pipeline y buses/indexes en este repo.
- No CMS nuevo.
- No DB editorial nueva para gobernanza.

### Seams mínimos a consumir (ya existentes)

- `storage/indexes/news_recent_refs_latest.jsonl`
- `storage/indexes/news_recent_groups_latest.jsonl`
- `storage/indexes/editorial_latest.json`

> Si alguna corrida no produjo uno de estos artefactos, el PR correspondiente debe incluir fallback explícito (`empty state`) y un check de precondición en scripts.

---

## PR-1 — Bootstrap de `apps/news_site` con adapter local

### Goal

Crear una app Next.js mínima (App Router) que renderice portada desde snapshots locales sin inventar modelo editorial nuevo.

### Why now

Sin bootstrap real no hay superficie para validar skin, slugs ni loop de publicación.

### Scope

- Crear `apps/news_site/` con estructura mínima:
  - `app/layout.tsx`
  - `app/page.tsx`
  - `app/(site)/tema/[slug]/page.tsx` (shell)
  - `app/(ops)/ops/page.tsx` (placeholder privado)
  - `components/` (cards/listas básicas)
  - `lib/adapter/` (lectura + mapping de índices compactos)
- Implementar adapter **read-only** que mapee los índices compactos a view models (`FrontpageItem`, `TopicBlock`, etc.).
- Agregar `README` operativo en `apps/news_site/README.md` con comandos `dev` y precondiciones de datos.

### Non-goals

- Sin Sanity.
- Sin autenticación completa.
- Sin API nueva todavía.

### Done criteria

- `npm run dev` en `apps/news_site` levanta portada funcional.
- La portada muestra al menos 10 ítems desde `news_recent_refs_latest.jsonl`.
- Si faltan índices, se muestra `empty state` claro (sin crash).

### Riesgos

- Variabilidad de shape en JSONL/JSON.
- Slugs inconsistentes en topic labels.

### Checks sugeridos

- `node -e "JSON.parse(require('fs').readFileSync('../../storage/indexes/editorial_latest.json','utf8'))"`
- Script de validación de índices previo a `next dev`.

---

## PR-2 — Newspaper skin (público)

### Goal

Pasar de “demo blog” a layout editorial (hero, latest rail, topic blocks, article shell).

### Why now

Con datos reales ya conectados, la mejora visual desbloquea review de producto y lectura humana.

### Scope

- `app/page.tsx`: hero + latest rail + bloques por topic.
- `app/(site)/tema/[slug]/page.tsx`: listado por tema.
- `app/(site)/articulo/[id]/page.tsx`: artículo shell usando view model derivado.
- Componentes de UI selectivos inspirados en templates externos (copiados de forma puntual, con pruning documentado).

### Non-goals

- No migrar tema completo de Stablo.
- No meter librerías de CMS.

### Done criteria

- Navegación portada -> tema -> artículo funcionando.
- Densidad visual tipo medio (no blog personal).
- Lista explícita en PR de componentes reutilizados vs descartados.

### Riesgos

- Sobre-importar componentes muertos.
- Regressions en responsive.

### Checks sugeridos

- `npm run build` en `apps/news_site`.
- Capturas de `/`, `/tema/<slug>`, `/articulo/<id>`.

---

## PR-3 — Superficie editorial/ops

### Goal

Agregar vista interna para handoff editorial con foco en “última milla humana”.

### Why now

Es la capa que convierte drafts automáticos en publicación controlada.

### Scope

- `app/(ops)/ops/page.tsx` con lectura de `editorial_latest.json`.
- Tabla/listado con señales mínimas:
  - prioridad
  - candidato de historia
  - estado de draft
  - señal YT-first (si existe)
- Acciones iniciales solo informativas (sin mutate).

### Non-goals

- No workflow de aprobación completo.
- No auth enterprise (solo guardrail básico si aplica).

### Done criteria

- Vista ops renderiza handoff con empty/error states.
- Queda documentado cómo usa `editorial_latest.json`.

### Riesgos

- Contrato de `editorial_latest.json` incompleto.
- Mezclar vista interna con rutas públicas.

### Checks sugeridos

- `npm run dev` + validación manual en `/ops`.
- Snapshot JSON de ejemplo para test local controlado.

---

## PR-4 (condicional) — FastAPI read surface y switch de fuente

### Goal

Crear seam HTTP estable para que frontend deje de leer archivos directos en runtime y pase a consumir read API.

### Cuándo activar este PR condicional

Activar solo si se cumple al menos uno:

- deploy bloqueado por dependencia de filesystem local
- necesidad real de caching/TTL desacoplado del renderer
- segundo consumidor productivo (además del site)

### Why now

Permite desacoplar despliegue web de filesystem local y prepara publicación continua, pero no debe adelantarse a la estabilización de contrato + adapter.

### Scope

- Nueva app API mínima (ej. `apps/news_api/`) con endpoints read-only:
  - `GET /api/frontpage`
  - `GET /api/stories/latest`
  - `GET /api/editorial/handoff`
  - `GET /api/story/{id}`
  - `GET /api/topic/{slug}`
- Adapter compartido o duplicación mínima controlada para mapear índices -> payloads API.
- Cambiar `apps/news_site` para usar fetch a API (con fallback local opcional detrás de flag).

### Non-goals

- Sin publish automation final.
- Sin persistencia nueva en DB.

### Done criteria

- Frontend renderiza contenido desde API.
- Contratos de respuesta documentados (tipos + ejemplo JSON).
- Errores 404/500 con respuestas coherentes.

### Riesgos

- Duplicación de mapping en site y API.
- Caching ambiguo entre Next y FastAPI.

### Checks sugeridos

- `uvicorn ...` + `curl` a endpoints.
- `npm run build` del sitio consumiendo API local.

---


## Comparativa directa vs `shadcn/next-contentlayer`

Referencia comparada: plantilla `Next.js + Contentlayer` de `shadcn/next-contentlayer` (app dir, MDX file-source, Tailwind, dark mode).

### Qué encaja bien (reusar)

- Estructura App Router (`app/`, `layout.tsx`, rutas dinámicas).
- Setup base de Tailwind y tema.
- Convención de componentes de presentación y MDX rendering opcional para páginas estáticas.

### Qué no encaja como source-of-truth (adaptar o descartar)

- `contentlayer.config.js` y `content/posts/**/*.mdx` como autoridad editorial primaria.
- Uso de `allPosts`/`allPages` generado por Contentlayer para poblar home/story en runtime productivo.
- Rutas y slugs derivados de flattened paths de MDX como identificador canónico.

### Gap analysis (template vs objetivo del repo)

1. **Modelo de datos**
   - Template: MDX local (`Post`, `Page`) con campos mínimos (title/description/date).
   - Este repo: artefactos compactos (`news_recent_refs`, `news_recent_groups`, `editorial_latest`) como seam canónico.

2. **Flujo editorial**
   - Template: publicación manual por archivo.
   - Este repo: pipeline semi-automático + handoff humano de última milla.

3. **Contrato público**
   - Template: implícito en tipos Contentlayer.
   - Este repo: debe ser explícito y mínimo (`frontpage/topic/story/editorial_handoff`).

4. **Ops surface**
   - Template: no incluye panel de handoff editorial.
   - Este repo: `/ops` es requisito para priorización humana.

### Decisión de implementación

- Usar `shadcn/next-contentlayer` como **shell de UI/estructura**, no como cerebro editorial.
- Mantener Contentlayer sólo para contenido estático auxiliar (ej. about/FAQ), nunca para feed/editorial truth.
- Forzar adapter único desde índices compactos hacia view models públicos.

### Mapping de archivos del template (keep/adapt/discard)

- **Keep/Adapt**
  - `app/layout.tsx`
  - `app/globals.css`
  - `components/theme-provider.tsx`
  - `components/mode-toggle.tsx`

- **Discard para ruta canónica de noticias**
  - `content/posts/**/*.mdx`
  - `app/posts/[...slug]/page.tsx` (si depende de `allPosts`)
  - `contentlayer.config.js` como fuente de historias de portada

- **Optional**
  - `components/mdx-components.tsx` solo para páginas estáticas no editoriales


## Reglas transversales (desde PR-1)

1. **PR pequeño y reversible**: objetivo único, diff acotado.
2. **Sin drift de source-of-truth**: nunca mover gobernanza editorial al frontend.
3. **Evidencia runtime obligatoria**: comando + salida + screenshot cuando aplique UI.
4. **Pruning continuo**: todo componente importado debe justificar existencia.
5. **Compatibilidad contracts-first**: si cambia mapping, documentar en el PR y en README del app.

---

## Definition of Done del milestone completo

> Regla de cierre: si para entender el estado operativo hacen falta múltiples scripts/runbooks fuera del README canónico, el milestone no está cerrado.


- Existe frontend público funcional con estilo de medio.
- Existe superficie ops mínima para handoff humano.
- El frontend puede operar primero con archivos y luego con API read-only sin rediseño.
- No se introdujo CMS ni DB editorial paralela.
- Queda un “golden path” claro de ejecución local para demo en menos de 10 minutos.
