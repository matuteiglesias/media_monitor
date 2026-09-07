# Adopter intake contract v1

> **Status:** implemented adoption contract · schema-validated and plan-compilable · **not self-service onboarding or a commercial agreement**

## Objective

A serious adopter should be able to describe what they want without understanding Media Monitor's internal buses, scripts or deployment archaeology.

The intake is precise enough to separate:

- adopter-specific configuration;
- required adapter work;
- reusable platform requirements;
- genuine unknowns requiring human judgment;
- requests that violate the adoption program's scope or authority rules.

Canonical surfaces:

- [`adopter_intake.schema.json`](adopter_intake.schema.json) — JSON Schema 2020-12 authority for v1;
- [`adopter_intake.example.yaml`](adopter_intake.example.yaml) — representative validated example;
- [`scripts/adopter_intake.py`](../../scripts/adopter_intake.py) — validator and deterministic intake-to-plan compiler.

## Fast path

Validate a YAML intake:

```bash
python scripts/adopter_intake.py docs/adoption/adopter_intake.example.yaml
```

Compile its bounded implementation plan:

```bash
python scripts/adopter_intake.py \
  docs/adoption/adopter_intake.example.yaml \
  --plan --format markdown
```

The plan is advisory. It does not activate work, deploy infrastructure, invent pricing, or choose license/privacy/support terms.

## Required sections

### 1. Organization and use case

Capture:

- organization / team;
- primary operator;
- primary recipient;
- use case class: monitoring intelligence, editorial outlet, executive brief, risk watch, research radar, other;
- pilot versus intended recurring use.

### 2. Source mode

Choose one:

- Media Monitor acquisition from configured public feeds;
- adopter-provided files;
- adopter-provided feed;
- adopter/provider API;
- mixed mode;
- undecided.

For adopter-provided data, specify interface, cadence, authentication, provenance requirements and retention constraints. An unresolved external source boundary is surfaced as a human decision and/or AP3 adapter requirement rather than hidden inside core code.

### 3. Watch policy

Capture:

- topics/entities/keywords;
- geography;
- languages;
- priority rules;
- freshness horizon;
- diversity/repetition expectations;
- explicit exclusions.

This maps to configuration where possible rather than source changes.

### 4. Authority and editorial policy

Capture:

- who may review;
- whether assisted generation is disabled, optional or required;
- who may approve publication/delivery;
- public/private mode;
- evidence/source-link requirements.

The v1 schema deliberately requires:

```text
auto_publish_generated_text: false
```

That makes the seed authority boundary executable rather than merely advisory: generated content cannot silently become approved/published content through adopter intake.

### 5. Identity and branding

Capture:

- outlet/product name;
- locale;
- domain/hosting expectation;
- public/editor identity;
- attribution posture;
- optional logo/theme notes.

### 6. Deliverables

Capture the actual recipient artifact:

- web outlet;
- HTML/email brief;
- downloadable report;
- feed/API;
- webhook/alert;
- other.

Specify cadence and, where useful, delivery window, target item count and freshness target.

### 7. Privacy, security and deployment

Capture:

- public/private/mixed mode;
- authentication expectation;
- deployment account ownership;
- whether sensitive data is expected;
- retention constraints;
- allowed external services;
- geographic/organizational restrictions;
- audit/evidence expectations.

An intake does not create privacy or security commitments. Unresolved choices remain `HUMAN_DECISION_REQUIRED`.

### 8. Integration

Capture:

- inbound owner;
- outbound owner;
- required identifiers;
- expected failure/retry behavior;
- systems of record.

### 9. Pilot acceptance

Define observable success before implementation:

- duration;
- maximum acceptable freshness delay;
- operator flow acceptance;
- recipient deliverable acceptance;
- minimum successful scheduled cycles;
- documented exclusions;
- optional termination/handoff test.

Avoid subjective "looks good" as the only gate.

### 10. Commercial path

Record the path being evaluated:

- paid pilot;
- managed white-label deployment;
- technology/license partnership;
- strategic transfer;
- exploratory/undecided.

The schema deliberately requires both `price` and `license_terms` to remain `human_decision_required`. The intake program cannot manufacture those decisions.

## Intake-to-plan classification

A validated intake compiles into exactly these buckets:

```text
CONFIG_ONLY
ADAPTER_REQUIRED
REUSABLE_PLATFORM_REQUIREMENT
HUMAN_DECISION_REQUIRED
OUT_OF_SCOPE
```

The current deterministic compiler uses known Media Monitor boundaries rather than sales optimism. Examples:

- watch policy / preview identity / acceptance thresholds → `CONFIG_ONLY`;
- adopter-owned feed/API inputs → `ADAPTER_REQUIRED`, pointing toward AP3;
- recipient surfaces not currently productized, such as email brief/report/webhook → `REUSABLE_PLATFORM_REQUIREMENT`, pointing toward AP5;
- private/mixed operation → reusable AP4/AP6 work plus any unresolved authentication decision;
- pricing, licensing and unresolved attribution/account ownership → `HUMAN_DECISION_REQUIRED`;
- authority requests that collapse generated content directly into publication are rejected by schema before planning.

Every future adopter request should land in one of these buckets before engineering begins.

## Evidence level

AP1 currently has **L1 — internally exercised** evidence through the validated representative intake and CI tests. It reaches L2 only when a first-time outsider can complete the intake and receive a useful bounded plan with at most one clarification round.
