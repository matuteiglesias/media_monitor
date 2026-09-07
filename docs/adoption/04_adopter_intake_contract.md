# Adopter intake contract v0

> **Status:** seed requirements contract · not yet a runtime schema or self-service onboarding API

## Objective

A serious adopter should be able to describe what they want without understanding Media Monitor's internal buses, scripts or deployment archaeology.

The intake must be precise enough to separate:

- adopter-specific configuration;
- required adapter work;
- reusable platform requirements;
- genuine unknowns requiring human judgment.

The companion [`adopter_intake.example.yaml`](adopter_intake.example.yaml) is an illustrative shape, not yet a validated production schema.

## Required sections

### 1. Organization and use case

Capture:

- organization / team;
- primary operator;
- primary recipient;
- use case class: monitoring intelligence, editorial outlet, executive brief, risk watch, research radar, other;
- pilot versus intended recurring use.

### 2. Source mode

Choose one or more:

- Media Monitor acquisition from configured public feeds;
- adopter-provided files/feeds;
- adopter/provider API;
- mixed mode.

For adopter-provided data, specify fields, update cadence, authentication, provenance identifiers and permitted retention.

### 3. Watch policy

Capture:

- topics/entities/keywords;
- geography;
- languages;
- priority rules;
- freshness horizon;
- diversity/repetition expectations;
- explicit exclusions.

This should map to configurable policy where possible rather than source changes.

### 4. Authority and editorial policy

Capture:

- who may review;
- whether assisted generation is used;
- who may approve publication/delivery;
- public/private mode;
- whether generated text can ever be auto-delivered;
- evidence/source-link requirements.

Default Media Monitor semantics remain fail-closed: generated does not equal approved or published.

### 5. Identity and branding

Capture:

- outlet/product name;
- locale;
- domain/hosting expectations;
- public/editor identity;
- logo/theme requirements if any;
- whether Media Monitor attribution is visible, hidden or contractually defined.

### 6. Deliverables

Capture the actual recipient artifact:

- web outlet;
- email/HTML brief;
- report;
- feed/API;
- webhook/alert;
- other.

Specify cadence, expected item count/detail, freshness target and delivery window.

### 7. Privacy, security and deployment

Capture:

- public versus private;
- authentication expectation;
- deployment account ownership;
- data sensitivity;
- retention constraints;
- allowed external services;
- geographic/organizational restrictions;
- audit/evidence expectations.

### 8. Integration

Capture:

- inbound interface;
- outbound interface;
- required identifiers;
- expected failure/retry behavior;
- systems of record;
- who owns each boundary.

### 9. Pilot acceptance

Define observable success before implementation:

- source/input coverage;
- maximum acceptable freshness delay;
- expected shortlist/brief cadence;
- operator flow acceptance;
- recipient deliverable acceptance;
- required uptime or run count;
- known exclusions;
- termination/handoff test.

Avoid subjective "looks good" as the only gate.

### 10. Commercial path

The intake may record the path being evaluated:

- paid pilot;
- managed white-label deployment;
- license/technology partnership;
- strategic transfer;
- exploratory / undecided.

It must not embed invented prices or legal terms.

## Intake-to-plan output

AP1 should eventually turn an intake into a bounded plan containing:

```text
CONFIG_ONLY
ADAPTER_REQUIRED
REUSABLE_PLATFORM_REQUIREMENT
HUMAN_DECISION_REQUIRED
OUT_OF_SCOPE
```

Every requested feature should land in one of those buckets before engineering begins.
