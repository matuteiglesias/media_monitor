# 🗞️ Media Monitor

`media_monitor` es un **sistema desplegado y gobernado de inteligencia de noticias y publicación editorial** orientado a una ruta operativa simple:

**fuentes → ingesta → contratos versionados → índices deterministas → briefs/drafts → aprobación humana → publicación → snapshot versionado → health → deploy**.

El sistema separa explícitamente señales monitoreadas de análisis editorial propio. La generación asistida por IA nunca equivale a aprobación: sólo `published_article.v1` atravesado por el gate humano puede entrar a la capa editorial pública.

## 🌐 Superficies públicas canónicas

- **Outlet público:** https://mediamonitor-psi.vercel.app
- **Health público:** https://mediamonitor-psi.vercel.app/api/health
- **Documentación:** https://github.com/matuteiglesias/media_monitor/tree/main/docs
- **Repositorio:** https://github.com/matuteiglesias/media_monitor
- **Owner / portfolio:** https://main.matuteiglesias.link

La identidad pública de máquina vive en
[`apps/news_site/config/public_identity.json`](apps/news_site/config/public_identity.json).
El outlet anterior o cualquier otra URL de preview/deploy no es una identidad pública
canónica. La aplicación publica `canonical_url` en `/api/health` y usa la misma
fuente para metadata/canonical HTML.

**“Live” no significa simplemente que una URL responda.** La superficie sólo debe describirse como corriente cuando el health público reporta `freshness_status=FRESH`, `is_current=true` y `within_target=true`. La frescura se evalúa en request time sobre las señales monitoreadas, no sobre la edad de un análisis editorial.

## 🔎 Evidencia pública de ingeniería

La cadena actualmente inspeccionable es:

1. **Source ingestion / sensing** → `apps/news_acquire` y bundles de corrida inmutables.
2. **Contratos versionados** → `contracts/schemas/` y buses JSON/JSONL estables.
3. **Índices deterministas** → builders de access indexes y compaction sin dependencia del frontend.
4. **Generación editorial** → `apps/news_editorial` produce briefs y drafts, no publicaciones.
5. **Gate humano explícito** → [`scripts/promote_draft_to_published.py`](scripts/promote_draft_to_published.py) exige aprobación humana para producir `published_article.v1`.
6. **Snapshot de deployment** → [`site_snapshot.v2`](contracts/schemas/site_snapshot.v2.json) separa `publication` de `signals` y conserva artículos/citas/fuentes aprobados.
7. **Freshness health** → `/api/health` expone identidad de snapshot, conteos y `publication_health.v1`.
8. **Operación programada** → [Scheduled public refresh](.github/workflows/scheduled-publication.yml) ejecuta sensing, guard pre-deploy, roll y verificación pública anónima.
9. **Publicación desplegada** → el proyecto canónico `media-monitor` en Vercel materializa `apps/news_site`; la homepage del repositorio apunta al mismo outlet.

Evidencia concreta:

- [Outlet canónico](https://mediamonitor-psi.vercel.app)
- [Health público](https://mediamonitor-psi.vercel.app/api/health)
- [Documentación](https://github.com/matuteiglesias/media_monitor/tree/main/docs)
- [Runtime contracts — ejecución de referencia](https://github.com/matuteiglesias/media_monitor/actions/runs/32770941754)
- [P0-C3 — rehearsal del primer tranche editorial y prueba del gate humano](https://github.com/matuteiglesias/media_monitor/pull/64)

No se enlaza todavía un “artículo representativo” como si estuviera human-approved: C3 probó de extremo a extremo la maquinaria de promoción/indexación en un bus aislado, pero preservó deliberadamente la frontera de aprobación real. La primera pieza editorial pública deberá aparecer aquí sólo después de una decisión humana explícita.

**Mapa de documentación:** [`docs/README.md`](docs/README.md) reúne rutas por
audiencia, capacidad y estado de madurez. Este README conserva solamente la ruta
operativa corta.

---

## ✅ Ruta canónica (operativa)

La ejecución recomendada es por lanes independientes vía `bin/run_minimal_loop_once.sh`:

- **sensing** (obligatoria, cada 60m)
  - `make s01`
  - `make s02`
  - `make s03`
  - `make export-pr3a`
  - `make build-news-access-indexes`
- **editorial** (recomendada, cada 6h)
  - `make s04`
  - `make s06`
  - `make s05`
  - `make build-editorial-access-indexes`
- **enrich** (opcional, queue/on-demand)
  - `bin/run_minimal_loop_once.sh --lane enrich`

Entrypoint único por lane:

```bash
bin/run_minimal_loop_once.sh --lane sensing
bin/run_minimal_loop_once.sh --lane editorial
bin/run_minimal_loop_once.sh --lane enrich
```

> La lane `enrich` conserva el contrato histórico mediante
> `scripts/06_scrape_enrich.py`, un wrapper fino que delega en el entrypoint del
> módulo propietario con `MODE=batch`. Para operación especializada siguen
> disponibles los modos de `apps/news_enrich/entrypoints/run_enrich_owner.sh`.

### DoD mínimo del sprint (cierre operacional)

Un sprint se considera **cerrado** solo si se cumple este mínimo:

- `home` viva (ruta principal visible y utilizable sin arqueología documental).
- `story` viva (al menos una historia recorre la ruta completa y queda accionable).
- handoff panel simple vivo (`storage/indexes/editorial_latest.json` como superficie de decisión).
- README canónico corto actualizado (este archivo como golden path).

Criterio de rechazo explícito:

- Si para entender el flujo básico hacen falta múltiples runbooks/scripts en paralelo, el sprint **no** se cierra.

Evidencia obligatoria por PR:

- Comandos ejecutados (copiables) y resultado observable.
- Capturas de la superficie afectada cuando el cambio sea visual/operativo.
- Validación de no duplicación de mapping entre frontend/API/scripts (o `N/A` justificado si una capa no existe en el repo).

---

## 📰 Last mile (página simple de publicación)

Generar snapshot público hardened para la web:

```bash
make build-editorial-access-indexes DIGEST_AT=$(date -u +%Y%m%dT%H)
make publish-last-mile-snapshot
```

Abrir vista local:

```bash
python -m http.server 8000
# abrir http://localhost:8000/web/
```

Deploy en Vercel (online):

```bash
vercel --prod
```

Hardening aplicado:
- La UI consume `web/data/editorial_latest.json` (snapshot público hardened para publicación estática).
- Snapshot generado por `scripts/publish_last_mile_snapshot.py` con shape mínima y sanitizada para evitar exponer campos no necesarios.
- `vercel.json` aplica headers de seguridad (`CSP`, `X-Frame-Options`, `nosniff`) y `no-store` para JSON de estado.


### news_site deploy (golden path)

Source of truth (news_site): **runtime truth = `storage/indexes` → deploy truth = refreshed snapshot in `apps/news_site/public/data`**.

```bash
# 1) generar índices, validar storage, refrescar public/data, smoke-test y build Next
make s01 s02 s03 export-pr3a DIGEST_AT=$(date -u +%Y%m%dT%H)
make publish-news-site DIGEST_AT=$(date -u +%Y%m%dT%H)

# 2) deploy del proyecto Next apps/news_site
vercel --prod
```

Notas del refresh:
- Falla con error si faltan `news_recent_refs_latest.jsonl` o `news_recent_groups_latest.jsonl`, si están vacíos o si no parsean como JSONL.
- En producción, `storage/indexes/editorial_latest.json` es obligatorio. El fallback editorial sólo se permite para previews locales con `ALLOW_EDITORIAL_FALLBACK=1`.
- `scripts/publish_news_site.sh` usa los scripts npm `refresh-data` y
  `smoke:public-data` definidos por `apps/news_site/package.json`; cualquier
  error en refresh, validación o build interrumpe la publicación antes de escribir
  el manifest final.

---

## 🚀 Quickstart

1. Verificar runtime:

```bash
make preflight-runtime
```

2. Ejecutar una corrida de sensing (dry run):

```bash
make s01 DRY_RUN=1
make s02 DRY_RUN=1
make s03 DRY_RUN=1
```

3. Levantar heartbeat de sensing:

```bash
make heartbeat-start INTERVAL_SEC=3600
make heartbeat-status
```

---

## 🧭 Estructura (high-level)

- `bin/` → entrypoints de operación.
- `Makefile` → wiring de stages.
- `apps/news_acquire|news_editorial|news_enrich` → ownership por dominio.
- `legacy/` y algunos `scripts/` → compat wrappers aún activos.
- `contracts/schemas/` → contratos interoperables.
- `storage/buses/` y `storage/indexes/` → superficies exportables.
- `docs/runbooks/` → runbooks de operación, migración y pruning.

---

## 📌 Notas de consolidación

- Evitar nuevas capas/orquestadores sin consumidor real.
- Priorizar claridad de entrypoints sobre expansión de superficies.
- Tratar artefactos intermedios (`data/pf_out`, `data/drafts`, `data/quarantine`) como internos, no contratos públicos.

Para elegir la guía vigente sin depender de nombres de PR, comenzar en el
[`mapa de documentación`](docs/README.md).
