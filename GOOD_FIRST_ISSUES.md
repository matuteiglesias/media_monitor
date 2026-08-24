# Bounded starter contributions

These are intentionally small contribution shapes, not a mandate to create work for its own sake.

## 1. Schema the demo manifest

**Scope:** add a JSON Schema for `media_monitor_demo.v1` and validate `bin/media demo` output against it.

**DoD:** schema + validation test; no demo semantics change.

## 2. Add RSS escaping adversarial cases

**Scope:** extend feed tests with titles/descriptions containing `&`, `<`, `>` and quotes.

**DoD:** both editorial and monitored-signal feeds remain valid XML; no feed semantics change.

## 3. Add one second example selection policy

**Scope:** add an alternative policy under `examples/` and demonstrate deterministic ranking changes without changing core builder code.

**DoD:** fixed fixtures, deterministic expected order, core generic builders unchanged.

## 4. Improve demo output ergonomics

**Scope:** add a concise terminal summary after `bin/media demo` showing snapshot ID and the three files a newcomer should inspect.

**DoD:** JSON output remains available/stable; no production commands are invoked.

## 5. Add accessibility regression coverage for public labels

**Scope:** test that monitored-signal/editorial-approval distinctions remain present in accessible text on key pages.

**DoD:** bounded frontend test only; no redesign required.
