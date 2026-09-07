# AP4 closure — minimal analyst/reviewer operation

> **Status:** implemented internal evidence · L1 · non-developer/L2 exercise pending

## Objective

Make Media Monitor's existing human editorial authority usable through a small adopter/operator surface without introducing a newsroom CMS or weakening publication controls.

## Implemented surface

`scripts/adopter_review.py` adds two bounded operations:

1. `materialize` turns one or more explicit `news_article_draft.v1` files into a readable review packet (`review_queue.json` + `review_queue.md`) containing draft text, source links, structured citations, fact-check flags, revision notes, draft identity and SHA-256 provenance.
2. `decide` records `hold`, `revise`, `reject`, or `approve` in an append-preserving decision journal.

Non-approval decisions have no publication effect.

Approval remains delegated to the existing `scripts/promote_draft_to_published.py` authority and requires both:

- the explicit `--approve-human` flag; and
- an explicit `--published-bus-dir` for adopter/operator rehearsals.

The promoter now accepts an optional explicit published-bus target while preserving the existing canonical bus as its default for normal repository operation. AP4 itself never chooses the canonical target for an adopter rehearsal.

## Internal acceptance evidence

Focused tests exercise:

- materialization of a review queue with source/citation/fact-check/revision evidence;
- no mutation from queue materialization;
- auditable `hold` with no publication effect;
- refusal of approval without `--approve-human`;
- refusal of adopter approval without an explicit isolated published bus;
- successful explicit approval into the selected isolated bus;
- decision journal linkage to the resulting published article; and
- refusal of a second approval for the same draft in the same decision journal.

## Authority invariants

AP4 preserves these boundaries:

- reading/reviewing is not approval;
- generated/draft content is not published content;
- hold/revise/reject cannot publish;
- approval is an explicit human action;
- adopter rehearsal publication must name its isolated target;
- review evidence identifies the exact draft bytes reviewed;
- AP4 does not create authentication, RBAC, a collaborative editor, or a multi-tenant CMS.

## Evidence level

This is **L1 / internally exercised** only.

The provisional analyst/operator-readiness estimate may move from the 25% seed baseline to roughly **50–55%**, because the repository now has a bounded operator workflow rather than only storage-level/editorial commands. Do not claim the 60–70% target band until a non-developer operator completes the cycle independently.

## Remaining AP4 acceptance

A real or representative non-developer operator must:

1. receive a prepared queue without repository archaeology;
2. understand the evidence and authority distinction;
3. record at least one non-publication decision;
4. explicitly approve one safe representative draft into an isolated bus when appropriate;
5. recover from one deliberate validation/refusal case using the documented error; and
6. report whether direct storage/database intervention was needed.

If direct storage/database surgery or developer interpretation is required for the normal cycle, AP4 is not L2.

## Next packet

Proceed to **AP5 — client/boss deliverable**. Reuse approved/publication contracts and adopter identity; do not build a channel suite. The representative intake currently asks for an HTML/email brief, so AP5 may implement a deterministic recipient package and delivery-evidence contract while keeping actual email sending/provider credentials as a human/provider boundary.