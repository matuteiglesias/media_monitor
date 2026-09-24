# Historical `news_ref` archive investigation closure

- **Status:** reviewable design/evidence; no cleanup authorized
- **Scope:** read-only census tooling, bounded sample evidence, and canonical archive strategy

The legacy corpus was not changed. C2 remains the current-runtime solution;
the archive is a prerequisite for a future, separately approved C3 deletion
plan. The exact local legacy glob was 3,330 JSONL files / 38,393,640,146 bytes.
The supplied analyzer must complete its full-estate run and the proposed archive
must pass replay/checksum verification before carry state or cleanup eligibility
changes.

Proposed carry-state addition: record this design as supporting C3 evidence,
keep historical `news_ref` at `UNKNOWN_NEEDS_JUDGMENT`, and set no cleanup
action until `audit -> construct archive -> verify archive/replay -> deletion
plan -> human review` is complete.
