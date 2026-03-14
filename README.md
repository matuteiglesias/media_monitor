# 🗞️ Media Monitor

`media_monitor` es un backend editorial semiautónomo orientado a una ruta operativa simple:

**news in → brief → draft → human last mile**.

Hoy el foco no es agregar capas, sino mantener viva la ruta útil y reducir ambigüedad operacional.

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
  - `python scripts/06_scrape_enrich.py`

Entrypoint único por lane:

```bash
bin/run_minimal_loop_once.sh --lane sensing
bin/run_minimal_loop_once.sh --lane editorial
bin/run_minimal_loop_once.sh --lane enrich
```

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
- La UI consume primero `web/data/editorial_latest.json` (snapshot público) y cae a `storage/indexes/editorial_latest.json` solo para desarrollo local.
- Snapshot generado por `scripts/publish_last_mile_snapshot.py` con shape mínima y sanitizada para evitar exponer campos no necesarios.
- `vercel.json` aplica headers de seguridad (`CSP`, `X-Frame-Options`, `nosniff`) y `no-store` para JSON de estado.


### news_site deploy-safe snapshots

`apps/news_site` no lee `storage/indexes` en runtime; consume snapshots públicos en `apps/news_site/public/data`.

Refrescar snapshots para la portada:

```bash
mkdir -p apps/news_site/public/data
cp storage/indexes/news_recent_refs_latest.jsonl apps/news_site/public/data/news_recent_refs_latest.jsonl
cp storage/indexes/news_recent_groups_latest.jsonl apps/news_site/public/data/news_recent_groups_latest.jsonl
cp storage/indexes/editorial_latest.json apps/news_site/public/data/editorial_latest.json
```

Si los artefactos aún no existen en `storage/indexes`, `news_site` renderiza fallback vacío sin romper build/deploy.

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

Para más detalle operativo: ver `docs/runbooks/pr5-minimal-autonomous-loop.md`.
