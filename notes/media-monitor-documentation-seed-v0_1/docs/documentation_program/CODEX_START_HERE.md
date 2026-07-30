# Codex start here — media_monitor documentation program

## Execution contract

1. Read the charter, inventory, target stack, phased plan, and carry state.
2. Inspect current main. Existing docs may describe a past PR state.
3. Execute only `next_pr`.
4. Keep the PR documentation-only.
5. Preserve the root design constraint: the main operational route must remain
   understandable without opening many competing runbooks.
6. Do not move or delete PR-era, legacy, notes, or retrofit documents before
   canonical replacements exist and inbound links are checked.
7. Every claim must point to source, schema, test, infrastructure, artifact, or
   runtime evidence.
8. Commands must be executed or labeled unverified.
9. Preserve exact status language. The AWS sensing substrate is merged and
   deployment-ready; provider-side operation is not yet evidenced.
10. Add a closure note and propose carry state. Human review accepts.
11. Stop when the active PR is bounded and reviewable.

## Required PR description

- Reader problem solved
- Canonical pages affected
- Source truth inspected
- Exact scope and non-goals
- Commands/links verified
- Stale or contradictory docs discovered
- Migration/status changes
- Risks
- Closure-note path
- Proposed next PR

## Program identity

- Repository: `matuteiglesias/media_monitor`
- Program: `media_monitor_documentation`
- Initial PR: `PR-MD0`

## Hard exclusions

- No pipeline refactor.
- No AWS deployment.
- No Vercel deployment.
- No deletion of legacy or notes in the inventory phase.
- No new documentation site framework.
- No new permanent PR-numbered runbooks.
