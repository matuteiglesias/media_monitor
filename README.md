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
- `makefile` → wiring de stages.
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
