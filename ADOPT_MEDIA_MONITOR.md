# Adopt / deploy Media Monitor

> **Status:** adopter/evaluator front door · evidence-calibrated · **not a price sheet, software license, SLA or warranty**

Media Monitor is a deployed, governed media-intelligence and editorial publishing system. It keeps monitored evidence, deterministic prioritization, observed context, assisted editorial generation, human approval and publication as distinct states instead of collapsing them into one opaque AI workflow.

The reusable proposition is not "use the Argentina news site." It is:

> **Bring your sources or signal stream, watch priorities, brand and editorial authority. Media Monitor provides a governed path from monitored evidence to prioritized/contextualized intelligence and, where desired, human-approved delivery or publication.**

## Who this can fit

The strongest early fits are organizations that already understand a monitoring or intelligence problem and want to avoid rebuilding the governed machinery around it, for example:

- media-intelligence and monitoring operators;
- communications / public-affairs agencies;
- publishers or specialist intelligence desks;
- research, risk or policy teams;
- vertical information products;
- organizations that already own a source/clip stream and need a governed downstream decision or publication layer.

Media Monitor does **not** need to replace an adopter's acquisition stack. A future adopter may use the repository's acquisition path or supply compatible monitored signals through an adapter boundary.

## What you provide / what a pilot should produce

| You provide | A credible first pilot should produce |
|---|---|
| use case and intended recipient | an isolated, configured preview |
| source strategy or existing signal feed | provenance-preserving monitored and selected state |
| topics / watch priorities | deterministic prioritization policy |
| geography and languages | contextualized intelligence/read models |
| brand and public/private preference | a separately identified adopter surface |
| who has approval authority | explicit human authority for editorial publication |
| desired deliverable and cadence | the agreed recipient-facing artifact or surface |
| acceptance criteria | health/freshness and bounded acceptance evidence |

The first pilot may be concierge-operated. Media Monitor does not require a multi-tenant SaaS control plane, billing system or self-service onboarding to prove value for an adopter.

## Four conversations Media Monitor can support

### 1. Bounded pilot

A small instance around one organization or use case, with agreed inputs, watch policy, operator flow, deliverable and acceptance criteria. This is the most direct way to discover whether the system fits a real workflow.

### 2. Managed white-label deployment

A separately branded instance using reusable Media Monitor machinery while the adopter keeps its customer/editorial identity and commercial relationship. Early deployments can remain isolated rather than introducing premature multi-tenancy.

### 3. Technology / license partnership

An adopter integrates or operates the governed compiler around its own source/data infrastructure. The repository currently does **not** state a general software/commercial license; exact licensing and support terms require an explicit agreement.

### 4. Strategic technology transfer

A buyer can evaluate the code, contracts, deployment assets, documentation and operating know-how as a transferable technical asset. Transfer scope, rights and handoff terms are not predeclared by this page.

## What is proven today

The repository currently provides evidence for:

- a deployed canonical Media Monitor outlet and public health endpoint;
- a deterministic offline demo (`bin/media demo`);
- versioned integration contracts and CI acceptance;
- deterministic editorial selection and story-context builders;
- human-gated article promotion/publication semantics;
- public snapshot, freshness, crawler and social-surface verification;
- a configurable second-outlet fixture that compiles through the generic selection/context/snapshot machinery without adopter-specific edits to those core builders;
- deployment and operator tooling for the existing Media Monitor instance.

Start with:

- [root README](README.md) — product path and quick proof;
- [EVIDENCE.md](EVIDENCE.md) — what counts as production, rehearsal and demo evidence;
- [build another outlet](examples/outlet/README.md) — current reusable-instance boundary;
- [documentation map](docs/README.md) — architecture, contracts and operations;
- [adoption program](docs/adoption/README.md) — the bounded work program for closing remaining adopter friction.

## What is **not** proven or productized yet

Do not infer that Media Monitor already has:

- a live external customer/adopter instance;
- self-service onboarding;
- generic multi-tenant customer administration;
- a private multi-user newsroom CMS;
- enterprise SSO/RBAC;
- a universal connector library for monitoring vendors;
- established SLA/support commitments;
- a repository-level general software/commercial license;
- generic billing/checkout;
- every reporting or notification channel.

Those are possible adopter requirements, not current claims.

## What happens after "this might fit us"

A useful first conversation does not require a specification document. Bring the following, even roughly:

1. **use case / recipient** — who needs the intelligence and what decision does it support?;
2. **source mode** — public feeds, an existing monitoring provider, files/API, or undecided?;
3. **watch policy** — topics, entities, geography, languages and urgency;
4. **authority** — who can approve anything presented as your organization's analysis?;
5. **delivery** — site, brief/report, feed/API, alert, or another existing workflow?;
6. **privacy** — public, private or mixed?;
7. **success** — what would make a small pilot worth continuing?

The structured version of this intake lives in [`docs/adoption/04_adopter_intake_contract.md`](docs/adoption/04_adopter_intake_contract.md).

## Contact

For a pilot, managed/white-label deployment, technology partnership or strategic-transfer conversation:

- **Matías Iglesias** — `matuteiglesias@gmail.com`
- Portfolio: https://main.matuteiglesias.link
- LinkedIn: https://www.linkedin.com/in/matiasiglesias/

A useful subject line is **"Media Monitor — adoption / partnership"** and a short note covering the seven intake points above is enough to begin.

## Product boundary

Adoption work does not get to weaken Media Monitor's core authority rule:

```text
monitored ≠ selected ≠ generated ≠ approved ≠ published
```

A commercial deployment is only useful if the evidence, authority and operational boundaries remain inspectable.