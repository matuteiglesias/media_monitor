# media_monitor documentation charter v0.1

## Mission

Turn the repository's accumulated product knowledge, runbooks, contracts,
migration records, and cloud retrofit evidence into one coherent documentation
system.

A reader should be able to understand:

- the product path from sensing to human-approved publication;
- lane and owner-module boundaries;
- the canonical artifact ladder and state writers;
- local operation, publication, replay, recovery, and cloud deployment paths;
- contract and identity guarantees;
- what is current, transitional, legacy, historical, deployed, or merely ready.

Documentation should demonstrate seniority through architecture, ownership,
failure semantics, security, provenance, and operational honesty.

## Readers and routes

| Reader | First need | Route |
|---|---|---|
| Evaluator | Understand product and engineering depth | root README → architecture → case studies |
| Operator | Run a lane or publish safely | docs router → canonical golden path |
| Contributor | Change one owner module safely | architecture → owner guide → contracts/tests |
| Agent | Resolve ownership and source truth | AGENTS → docs router → component/reference |
| Maintainer | Detect drift and migration debt | canonicality map → maintenance policy |

## Principles

1. Keep the root README a concise golden-path front door.
2. Capability-oriented documentation supersedes PR-era navigation.
3. One canonical owner per operational procedure.
4. The artifact ladder and writer authority must be explicit.
5. Local and cloud execution paths are related but distinct.
6. Runbooks include preflight, independent verification, replay identity,
   failure recovery, denied operations, and teardown where relevant.
7. Contracts and identities are first-class reference material.
8. Legacy and migration history remain available but visibly noncanonical.
9. Mermaid diagrams require text explanations.
10. Status uses the evidence ladder: designed, implemented, locally validated,
    deployment-ready, deployed, operated.

## Program definition of done

- root and docs front doors agree;
- lane/component ownership is unambiguous;
- sensing → enrich → editorial → publication is diagrammed and source-backed;
- buses, indexes, snapshots, identities, and state writers are cataloged;
- local and AWS sensing runbooks are canonical and noncontradictory;
- article approval/publication and news-site deployment have clear golden paths;
- PR-era and notes documentation is classified/migrated;
- documentation checks enforce links, metadata, and canonicality expectations;
- AWS and publishing case studies remain evidence-based.
