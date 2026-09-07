# Adoption-loop work packets

> **Status:** seed execution plan · each packet requires explicit human activation before implementation

## Packet discipline

One packet should fit one reviewable objective. Do not bundle commercial-front copy, runtime adapters, operator UX and legal decisions into one giant PR.

A packet may end with documentation/configuration only. Code is justified only when it removes demonstrated adopter friction through a reusable seam.

## AP0 — Offer and evaluator front door

**Goal:** raise offer clarity without making unsupported commercial claims.

**Seed inputs:** [commercial-front seed](05_commercial_front_seed.md), root README, `EVIDENCE.md`, public deployment and second-outlet example.

**Candidate outputs:**

- concise adopter-facing page such as `ADOPT_MEDIA_MONITOR.md` or an equivalent docs/public route;
- one restrained link from the existing evaluator front door after review;
- explicit distinction among pilot, managed white-label, technology/license partnership and strategic transfer;
- evidence-backed "what exists now" and "what a first adopter pilot would prove" sections.

**Non-goals:** pricing page, checkout, CRM, lead forms, inflated customer claims.

**Done when:** a first-time evaluator can explain the offer and choose the relevant conversation path without architecture archaeology.

**Expected score movement:** offer clarity.

---

## AP1 — Adopter intake and manifest

**Goal:** convert fuzzy interest into bounded implementation inputs.

**Seed inputs:** [adopter intake contract](04_adopter_intake_contract.md) and example YAML.

**Candidate outputs:**

- validated intake schema or strongly documented manifest;
- human-friendly questionnaire;
- conversion from intake to an implementation/acceptance plan;
- explicit distinction between adopter configuration and reusable-platform requirement.

**Non-goals:** self-service onboarding UI, customer database.

**Done when:** one realistic adopter scenario can be specified without oral archaeology and produces a deterministic list of required adapters/configuration/unknowns.

**Expected score movement:** requirements intake; preview readiness.

---

## AP2 — Real adopter bootstrap

**Goal:** make "give me one for X" operationally boring.

**Prerequisite:** AP1 has a stable enough intake/config boundary.

**Candidate outputs:**

- a command or documented builder that materializes a new outlet workspace/config from an adopter manifest;
- isolated preview deployment path;
- identity/branding leakage tests;
- acceptance manifest recording commit/config/source identity and preview URL/status.

**Hard rule:** a new outlet must not require adopter-name/topic conditions inside generic selection/context/site builders.

**Non-goals:** multi-tenant runtime, dynamic tenant provisioning service.

**Done when:** a second real or representative adopter reaches preview with documented seams and no outlet-specific core edits.

**Expected score movement:** live preview; requirements intake.

---

## AP3 — Bring-your-own signal boundary

**Goal:** let an adopter keep its own acquisition/monitoring system.

**Candidate outputs:**

- explicit external monitored-signal import contract;
- file/API adapter with validation and quarantine semantics;
- identity/provenance requirements;
- fixture proving another producer can feed the generic downstream compiler;
- trust-boundary documentation.

**Non-goals:** replacing every source vendor, generic connector marketplace, scraping every medium.

**Done when:** an external signal producer can satisfy the boundary without importing `apps/news_acquire` internals.

**Expected score movement:** preview readiness; strategic partner fit.

---

## AP4 — Minimal analyst/reviewer operation

**Goal:** make existing human authority usable by an adopter operator.

**Candidate outputs:**

- smallest review queue or operator route necessary to inspect evidence/draft state;
- approve / reject / revise-or-hold actions through governed commands or UI;
- provenance visible at decision time;
- failure/recovery instructions;
- role boundary documented.

**Non-goals:** full newsroom CMS, collaborative document editor, enterprise RBAC unless demanded.

**Done when:** a non-developer can perform the standard review cycle without direct storage/database surgery.

**Expected score movement:** analyst/operator comfort.

---

## AP5 — Client/boss deliverable

**Goal:** close the gap between internal intelligence state and the artifact the adopter's recipient actually consumes.

**Candidate first deliverables:**

- scheduled HTML/email briefing;
- branded downloadable report;
- stable feed/API/webhook output where the adopter already owns presentation.

Choose the smallest deliverable validated by a real adopter. PDF, WhatsApp, Slack and other channels are follow-on requirements, not seed assumptions.

**Done when:** a real recipient receives an agreed artifact on the agreed cadence and the system records freshness/provenance/delivery evidence.

**Expected score movement:** client/boss deliverable; transaction confidence.

---

## AP6 — Procurement and trust packet

**Goal:** make technical/commercial diligence answerable without repository archaeology.

**Required decision surfaces:**

- repository/code licensing status and intended commercial licensing model;
- third-party dependency/license inventory;
- data-source responsibility boundary;
- secrets and deployment-account ownership;
- storage/retention/durability policy status;
- authentication/private-mode status;
- incident/failure/support boundary;
- uptime/freshness claims and what evidence supports them;
- backup/recovery limitations;
- export/termination/handoff behavior.

**Important current gap:** there is no repository-level `LICENSE` file on the seed baseline. AP6 must resolve or explicitly govern that fact; do not imply an open-source or commercial license that has not been chosen.

**Non-goals:** fabricated certifications, enterprise controls with no buyer requirement.

**Done when:** remaining questions require human commercial/legal choices rather than technical archaeology.

**Expected score movement:** procurement clarity.

---

## AP7 — Transaction and transfer closure

**Goal:** make at least one commercial path executable.

**Candidate paths:**

- bounded paid pilot;
- managed deployment/service;
- technology/software license;
- strategic asset/technology transfer.

**Candidate outputs:**

- scope and acceptance template;
- responsibility matrix;
- support/handoff assumptions;
- inventory of transferable code/config/deployment assets;
- customer/adopter exit/export behavior;
- human-approved commercial terms stored outside code where appropriate.

**Non-goals:** Stripe/billing implementation before needed.

**Done when:** the owner can respond to "we want to proceed" with a concrete next document/action rather than inventing the mechanism live.

**Expected score movement:** transaction closure; procurement clarity.

---

## AP8 — First real adopter acceptance

**Goal:** replace simulated buyer pressure with observed adopter evidence.

**Required evidence:**

- completed intake;
- preview/production identity;
- actual source/input mode;
- operator/reviewer path exercised;
- agreed deliverable received;
- acceptance criteria result;
- deviations that required bespoke intervention;
- closure-score update;
- reusable requirements promoted to core backlog;
- adopter-specific requirements kept outside generic core.

**Done when:** the first adoption cycle leaves the second one materially easier.

**Expected score movement:** all dimensions, based on actual evidence rather than estimation.

## Activation rule

Default next packet is **AP0**, but `carry_state.yaml` is advisory and does not supersede the repository-level agent contract. A human executor may deliberately choose AP1 first if an actual inbound adopter appears and requirements capture becomes the highest-value move.
