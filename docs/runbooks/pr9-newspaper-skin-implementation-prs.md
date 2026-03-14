# PR9 — Newspaper skin implementation PRs

## Contexto

Este plan define la secuencia de PRs para implementar el newspaper skin sin forzar una API dedicada antes de tener señales operativas reales.

## Baseline milestone (obligatorio)

### PR-1 — Snapshot contract estable
- Formalizar el schema de snapshot consumido por frontend.
- Validar compatibilidad backward con `adapter` actual.

### PR-2 — Adapter único frontend
- Consolidar la lectura del snapshot detrás de un único adapter en frontend.
- Eliminar accesos directos dispersos a archivos/raw payloads.

### PR-3 — Render y estados de degradación
- Completar loading/error/empty states sobre snapshot.
- Asegurar que el render no dependa de disponibilidad de API runtime.

## Conditional milestone

> Se activa **solo** si hay gatillos concretos validados con evidencia.

### PR-4 — API layer para newspaper skin (condicional)

**Gatillos de activación (todos concretos y auditables):**
1. Deploy bloqueado por dependencia de filesystem local.
2. Necesidad de caching/TTL independiente del render web.
3. Requerimiento de consumo multi-cliente (site + otro consumidor real).

**Criterio explícito de no-activación:**
- Si **ningún gatillo** se cumple, el frontend sigue sobre snapshots + adapter único.
- En ese escenario, PR-4 se posterga y no se introduce API adicional.

## Regla de decisión

- La decisión de activar/postergar PR-4 se toma por evidencia operativa, no por preferencia arquitectónica.
- Cualquier activación debe registrarse en el decision log.

## Decision log

| Fecha | Gatillo | Evidencia | Decisión |
|---|---|---|---|
| YYYY-MM-DD | (1) filesystem / (2) caching-TTL / (3) multi-cliente | Link a incidente, métrica o ticket | Activar API / Postergar API |
