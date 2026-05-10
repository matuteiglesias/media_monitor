# Diagnóstico semáforo por módulo (2026-03-13)

## Alcance
Chequeo rápido para separar **arquitectura declarada** vs **ruta operativa efectiva**.

## Checks ejecutados
1. `find storage -maxdepth 3 -type f`
2. `rg --files docs/runbooks`
3. `sed -n '1,220p' storage/README.md`
4. `sed -n '1,220p' bin/run_hour.sh`
5. `sed -n '1,240p' makefile`
6. `du -sh apps/news_* backend legacy flow contracts storage docs notes scripts bin`
7. `rg --files | rg 'master_ref|master_index|digest_map|pf_out|quarantine|run_hour|stage0[1-5]\\.py|backend/0[1-5]\\.py|scripts/0[3-6]\\.py'`

## Semáforo por dominio

### 1) Acquire — 🟡 Amarillo
- Ruta operativa principal sigue invocando `legacy.stage01_digests` vía `make s01`.
- Existe capa `backend/01_digests.py`, pero el orchestration por defecto no la usa directamente.
- `apps/news_acquire` está como ownership placeholder (README).

### 2) Editorial — 🟡 Amarillo
- PromptFlow corre desde `make s04`/`bin/run_hour.sh` con artefactos en `data/pf_out`.
- `flow/` y `legacy.stage04/05` siguen vigentes como tramo activo.
- Hay backend destino (`backend/04_promptflow_run.py`, `backend/05_explode_pf_outputs.py`) pero no es el entrypoint canónico en `make`.

### 3) Enrich — 🟡 Amarillo
- Hay scripts/workers de enriquecimiento (`scripts/06_scrape_enrich.py`, `worker_scrape.py`) y app placeholder.
- Falta una ruta única evidente de ejecución integrada en targets canónicos de `make` (01..05 están centrados en legacy).

### 4) Contracts — 🟢 Verde (diseño), 🟡 Amarillo (adopción runtime)
- `contracts/` ya tiene peso real (tests + schemas).
- Aun así, la ruta canónica en `make` sigue orientada a `legacy/*` y `data/*`, por lo que la adopción completa de contratos en runtime es parcial.

### 5) Storage — 🟡 Amarillo tirando a rojo
- `storage/` existe con estructura completa (`raw`, `buses`, `indexes`, `snapshots`).
- Contenido real hoy: principalmente `.gitkeep` + README; no hay buses/indexes poblados.
- `storage/README.md` explicita que PR2 es scaffolding y que runtime legacy sigue operativo.

### 6) Observability/Operación — 🟡 Amarillo
- Hay runbooks de evidencia runtime (`docs/runbooks/runtime-evidence-*`) y lock de concurrencia en `bin/run_hour.sh`.
- Falta evidencia en este checkout de índices operativos poblados en `storage/indexes` para inspección rápida “single pane”.

## Respuestas a los 4 checks críticos

1. **¿`storage/buses` e `storage/indexes` tienen archivos reales?**
   - No; solo `.gitkeep` y estructura base.
2. **¿PR3a estable adapters aplicado o solo documentado?**
   - No aparece `docs/runbooks/pr3a-stable-adapters.md` en este árbol.
   - Lo observable en repo apunta a estado de scaffolding + ruta legacy activa.
3. **¿Por qué `master_ref.csv` quedó en 0 bytes?**
   - En este checkout no existe `data/` (ni `data/master_ref.csv`), por lo que no se puede validar aquí.
4. **¿Ruta de producción hoy?**
   - `bin/run_hour.sh` → `make s01/s02/s03/s05`.
   - Esos targets ejecutan `legacy.stage01..05` (s04 por CLI PF y copia output a `data/pf_out`).

## Conclusión
Estado global: **transición congestionada pero coherente**.
- Lo nuevo (apps/contracts/storage/backend) está montado.
- Lo operativo canónico sigue centrado en `legacy/*` + `data/*`.
- Próximo hito de impacto: poblar `storage/buses`/`storage/indexes` con outputs reales y mover orchestration canónica fuera de legacy.
