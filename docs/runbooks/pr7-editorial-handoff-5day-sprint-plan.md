# PR7 — Sprint de 5 días: editorial handoff como producto principal

## Objetivo del sprint
Hacer que el archivo principal de operación humana sea `storage/indexes/editorial_latest.json`, con foco en decisión rápida de último tramo y prioridad de salida para guiones de YouTube.

## Alcance (sí entra)
- Consolidar `human_handoff` como primera superficie de lectura.
- Priorizar candidatos `yt_script` en cola de acción.
- Medir y endurecer uso de fallback legacy editorial.
- Seguir podando wrappers/superficies no consumidas con evidencia.

## Fuera de alcance (no entra)
- Publish automation completa.
- UI nueva/complex.
- Nuevos contratos sin consumidor real.
- Reorquestación mayor del runtime.


## DoD mínimo (gating de cierre)
- `home` viva.
- `story` viva.
- handoff panel simple vivo (`storage/indexes/editorial_latest.json`).
- README canónico corto (golden path) actualizado.

### Criterio de rechazo
- Si el flujo básico requiere consultar múltiples runbooks/scripts para entenderse, el sprint no se considera cerrado.

### Evidencia runtime obligatoria por PR
- Captura(s) de la superficie afectada (si aplica cambio visual/operativo).
- Lista de comandos ejecutados y su salida resumida.
- Validación explícita de no duplicación de mapping entre frontend/API/scripts (`N/A` justificado cuando una capa no existe).

## Entregables por día

### Día 1 — Baseline operacional
- Confirmar ruta canónica efectiva (`sensing -> editorial -> access`) con evidencia de run reciente.
- Establecer checklist de “archivo único”:
  - digest actual,
  - briefs,
  - drafts artículo,
  - drafts yt,
  - fallback/quarantine.

### Día 2 — Prioridad YT explícita
- `human_handoff.action_candidates` con prioridad YT primero.
- Briefs con `target_format` derivado de `format_candidates` cuando exista.
- Reglas de desempate simples y explicables.

### Día 3 — Cobertura de fallback
- Medir frecuencia de fallback stage05 en ventana reciente.
- Endurecer señal operacional cuando fallback ocurre (warning + evento estructurado).
- Definir umbral de “emergency-only” por evidencia de cobertura de briefs.

### Día 4 — Pruning guiado por consumo
- Revisar wrappers/helpers candidatos a unplug.
- Archivar/deprecar explícitamente lo que no tiene consumidor.
- Mantener compat solo donde exista evidencia de uso real.

### Día 5 — Cierre y decisión go/no-go
- Validar 4 checks de salida:
  1. runbooks + make apuntan a ruta principal,
  2. digest reciente recorre sensing→editorial→access sin ambigüedad,
  3. `editorial_latest.json` permite decidir sin inspección profunda,
  4. existe al menos un draft YT realmente utilizable.
- Publicar mini informe de estado + próximos cortes.

## Stop rules
- Si una poda toca runtime validado sin smoke checks, se frena.
- Si una remoción depende de intuición y no de evidencia de consumo, se posterga.
- Si la mejora aumenta superficies en vez de reducir ambigüedad, no se mergea.

## Métricas mínimas
- `% de corridas editoriales sin fallback`.
- `# action_candidates` por digest.
- `# yt_script draft-ready` por digest.
- `latencia digest -> first draft-ready`.
