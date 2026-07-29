# Codex Start Here

## Your execution contract

1. Read this file.
2. Read `00_embryo_plan_v0_1.md`.
3. Read `01_starting_context_v0_1.md`.
4. Read `carry_state_v0_1.yaml`.
5. Execute **only** the PR named by `next_pr`.
6. Do not implement later PRs “while you are here.”
7. Preserve product semantics unless the active PR explicitly changes them.
8. Add or update the PR closure note under `context/closures/`.
9. Propose the carry-state update, but do not mark the PR `ACCEPTED`; human review owns acceptance.
10. Stop when the active PR is reviewable.

## Required PR description

- Goal
- Why now
- Exact scope
- Non-goals
- Files/surfaces changed
- Tests and runtime evidence
- Risks
- Closure-note path
- Proposed next PR

## Scope discipline

When evidence invalidates the embryo plan, amend the plan explicitly in the current PR and record the decision. Do not silently grow the PR.

## Retrofit identity

- Retrofit: `aws_media_sensing`
- Repository: `matuteiglesias/media_monitor`
- Initial PR: `PR-A0`

## Hard exclusions

- Do not touch editorial, enrich, article promotion, `news_site`, or Vercel.
- Do not add boto3/Terraform/Docker changes in PR-A0.
- Do not migrate shared local state directly into S3.
- Do not redesign stable article/digest identities.
