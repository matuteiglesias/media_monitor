# media_monitor documentation quality and acceptance v0.1

## Canonical page requirements

- audience, status, owner, and verification commit;
- capability-oriented title;
- exact scope and non-goals;
- current source/test/contract/artifact pointers;
- commands executed or marked illustrative;
- observable success evidence;
- writer/reader authority where state is involved;
- failure, replay, recovery, and stop rules;
- security and mutation boundaries;
- links instead of duplicated golden paths;
- honest local/cloud/deployment status.

## Seniority signals

Documentation should make these engineering properties visible:

- domain ownership and compatibility boundaries;
- stable identities and contract versioning;
- provenance and digest consistency;
- immutable facts vs mutable pointers;
- deterministic compaction and replay selection;
- single-writer authority;
- least-authority IAM and expected denial;
- independent reconciliation across S3, logs, manifests, and indexes;
- human approval boundaries;
- failure isolation, rollback, teardown, retention, and cost;
- clear legacy/deprecation strategy.

## Evidence ladder

| Level | Meaning |
|---|---|
| Designed | architecture/contract accepted |
| Implemented | source exists |
| Locally validated | focused tests/smokes passed |
| Deployment-ready | image, adapter, IaC, and runbook exist |
| Deployed | provider resources and execution evidence exist |
| Operated | repeated runs, recovery, scheduling/observability evidence exist |

## Acceptance checklist

- [ ] Only active PR scope.
- [ ] Current commit recorded.
- [ ] Links checked.
- [ ] Commands executed or labeled.
- [ ] No pipeline semantics changed.
- [ ] One canonical owner per procedure.
- [ ] Artifact writer/reader claims verified.
- [ ] AWS/Vercel status reviewed.
- [ ] Historical knowledge preserved.
- [ ] Closure note and proposed carry update present.

## Review questions

1. Can the reader reach this page from the root?
2. Is this a current capability page or a historical PR narrative?
3. Does the page identify the authoritative writer?
4. Does success rely only on process exit, or on reconciled evidence?
5. Can replay or retry corrupt state?
6. What operation must be denied?
7. What happens when an upstream artifact is missing or stale?
8. Which source change creates a documentation update obligation?
