# AP2 closure note — real adopter bootstrap

> **State:** bootstrap subset implemented · internal evidence L1 · live preview/deployment acceptance pending

## Goal

Make "give me one for X" operationally boring without introducing tenant infrastructure or adopter-specific conditionals into generic Media Monitor builders.

## Implemented bootstrap subset

`scripts/bootstrap_adopter_preview.py` accepts a validated `media_monitor_adopter_intake.v1` and produces an isolated representative preview package.

Example:

```bash
python scripts/bootstrap_adopter_preview.py \
  docs/adoption/adopter_intake.example.yaml \
  --output .demo/adopter-previews/example-desk
```

The package contains:

```text
adopter_intake.yaml
implementation_plan.json
preview_manifest.json
README.txt
sites/<generated-site-id>.json
config/editorial_selection.json
storage/indexes/...
site_snapshot.json
```

## What it proves

The bootstrap:

1. validates the AP1 intake;
2. derives a deterministic site identity from adopter identity + intake hash;
3. produces synthetic representative monitored signals from the adopter's configured topics;
4. creates adopter-specific site and selection configuration;
5. runs the existing generic builders:
   - `build_editorial_selection.py`;
   - `build_story_contexts.py`;
   - `build_site_snapshot.py`;
6. verifies the resulting snapshot uses the adopter name/locale;
7. fails if known Media Monitor owner/editor identity leaks into the adopter snapshot;
8. emits a manifest tying the preview to the exact intake SHA-256 and generated snapshot ID.

No adopter/topic conditional was added to the generic builders.

## Deliberate fixture boundary

Every preview manifest is marked:

```text
REPRESENTATIVE_FIXTURE_NOT_LIVE_ADOPTER
```

and records:

```text
deployment_status: not_attempted
live_source_status: not_attempted
customer_claim_allowed: false
```

The synthetic signals use `example.invalid` URLs and exist only to exercise the configuration/compiler path. This is not live news, source integration, a customer deployment, or evidence that the adopter's operator workflow works.

## Tests

`tests/test_adopter_preview_bootstrap.py` checks:

- a valid intake builds through the generic compiler path;
- adopter name and locale survive into `site_snapshot.v4`;
- known Argentina/owner identity does not leak;
- the same intake produces the same site ID, intake hash and snapshot ID;
- the preview package carries the AP1 implementation plan and explicit fixture caveat.

The test is included in Runtime contracts CI.

## Evidence and score effect

This raises **preview/bootstrap readiness** from the seed ~35% to a provisional **50%** at L1.

It does **not** earn the 70–80% target because no isolated provider preview URL or adopter-owned live/representative-real input has been exercised.

## Remaining AP2 acceptance

To close AP2 beyond the bootstrap subset:

1. select one real or representative adopter intake;
2. resolve source mode enough to provide live or representative-real input, or explicitly pair with AP3;
3. materialize the adopter workspace using the bootstrap;
4. create an isolated preview deployment without modifying the canonical Argentina deployment;
5. verify domain/identity/branding and no owner leakage from outside the build process;
6. record commit, intake hash, config identity, source identity and preview URL/status;
7. prove the preview was produced without adopter-specific edits to generic core builders.

Provider mutation and any real adopter identity/use require an explicit execution decision; this packet does not perform them automatically.

## Rejected overbuild

AP2 does not add:

- dynamic tenant provisioning;
- customer database;
- shared multi-tenant runtime;
- automatic Vercel project creation;
- live-source connector logic;
- private auth;
- billing.

Those belong only where later evidence earns them.
