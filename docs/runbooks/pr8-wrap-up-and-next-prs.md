# PR8 — Wrap-up final + próximos PRs sugeridos

Estado actual (resumen): la ruta canónica ya es visible, wrappers legacy están más controlados y `editorial_latest.json` evolucionó hacia handoff humano.

Este documento propone el cierre de ciclo y la siguiente secuencia de PRs para consolidar, no expandir.

---

## Cierre de milestone (lo que ya quedó logrado)

- Ruta canónica operativa por lanes (`sensing`, `editorial`, `enrich`) con entrypoints explícitos.
- Make stages principales apuntando a owner modules bajo `apps/*`.
- Wrappers legacy/scripts movidos a rol de compatibilidad (y parte del histórico archivado).
- `editorial_latest.json` como superficie de handoff humano (briefs, drafts, fallback).
- Fallback editorial explicitado como política (`emergency/off`) con evidencia en quarantine.

---

## Próximos PRs recomendados (orden sugerido)

## PR-9 — Canonical command contract (single source of truth)

**Objetivo:** que exista una sola fuente oficial de comandos operativos válidos.

**Entra:**
- Crear `docs/runbooks/canonical-commands.md`.
- Incluir shortlist final de comandos permitidos por lane.
- Marcar comandos legacy como `compat-only` o `historical`.
- Linkear desde `README.md`, `docs/runbooks/README.md`, y runbooks de owner.

**No entra:**
- Cambios de runtime.
- Nuevas superficies funcionales.

**Done when:**
- Un operador nuevo puede ejecutar el sistema siguiendo un solo archivo.
- No quedan comandos ambiguos “aparentemente válidos” sin clasificación.

---

## PR-10 — Editorial handoff quality gate (decision-ready)

**Objetivo:** garantizar que `editorial_latest.json` sea accionable sin inspección profunda.

**Entra:**
- Agregar bloque `decision_gate` en `human_handoff` con checks binarios:
  - hay briefs,
  - hay drafts article,
  - hay drafts yt,
  - fallback en ventana,
  - schema failures.
- Añadir ranking simple de top candidatos para intervención humana corta.
- Testear explícitamente el orden YT-first cuando haya material usable.

**No entra:**
- Publicación automática.
- UI.

**Done when:**
- Abrís un archivo y decidís “qué va hoy” en menos de 2 minutos.

---

## PR-11 — Runtime evidence window for unplug candidates

**Objetivo:** retirar peso muerto con evidencia real de no uso.

**Entra:**
- Medir 7 días de invocación de scripts wrappers/helpers candidatos.
- Mover a `archive/` o marcar `deprecated` lo no usado.
- Mantener compat solo en paths con evidencia de uso.

**No entra:**
- Borrado masivo por intuición.

**Done when:**
- Baja el número de entrypoints operativos “visibles”.
- Queda claro qué se conserva por compatibilidad real.

---

## PR-12 — Fallback demotion enforcement (editorial)

**Objetivo:** que fallback legacy sea red de seguridad y no muleta silenciosa.

**Entra:**
- Umbral explícito de fallback permitido por ventana (ej: 24h).
- Señal fuerte cuando se supera umbral (`fallback_policy_state=breach`).
- Recomendación automática de acción en `editorial_latest.json`.

**No entra:**
- Eliminar fallback completamente.

**Done when:**
- Tenés una señal objetiva de si el path nuevo ya gobierna editorial.

---

## Stop rules transversales (para todos los próximos PRs)

- Si aumenta ambigüedad operacional, no mergear.
- Si introduce superficie sin consumidor explícito, no mergear.
- Si toca runtime validado sin smoke tests, no mergear.
- Si mezcla refactor estructural con cambio funcional crítico, separar PR.

---

## Checklist de cierre final de etapa (go/no-go)

1. `make` y runbooks apuntan a la misma ruta principal.
2. Un digest reciente recorre `sensing -> editorial -> access` sin dudas operativas.
3. `editorial_latest.json` alcanza para decidir temas y formato.
4. Existe al menos un draft YT utilizable por ventana objetivo.
5. Fallback queda en modo emergencia observable, no default silencioso.

---

## Principio rector

El sistema ya existe.
Ahora la prioridad no es “hacer más pipeline”, sino **hacer dominante la ruta útil y minimizar todo lo que compita con ella**.
