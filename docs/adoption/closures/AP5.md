# AP5 closure — client/boss deliverable

> **Status:** implemented internal evidence · L1 · real-recipient/L2 delivery pending

## Objective

Make the first adopter recipient artifact concrete without adding a channel platform or inventing a delivery success claim.

The representative intake already selects `html_email_brief`, so AP5 implements only that recipient surface.

## Implemented

`scripts/adopter_delivery.py` provides three separated operations:

1. **prepare** — validated intake + validated `site_snapshot.v4` → branded `brief.html`, `brief.txt`, and `delivery_manifest.json`;
2. **authorize** — explicit human authorization bound to the exact manifest and brief hashes;
3. **record** — append delivery evidence supplied after an external sender/provider action.

The tool itself never sends email or calls a delivery provider.

## Content and acceptance invariants

- only `published_article.v1` content with `status=published` and `review_status=human_approved` is eligible;
- required source links remain visible in the recipient artifact;
- adopter identity comes from the intake rather than leaking the source snapshot brand;
- recipient email/address is not invented or persisted by the seed tooling;
- `target_item_count` is executable and preparation fails below the requested minimum;
- preparation cannot claim authorization, send, or delivery;
- delivery authorization requires `--approve-delivery-human`;
- authorization SHA-binds the exact manifest and rendered brief bytes;
- mutation after authorization invalidates receipt recording;
- `sent` and `delivered` receipts require a provider message/reference;
- receipt evidence is explicitly classified as human/provider-supplied evidence.

## Internal acceptance tests

Focused tests exercise:

- one approved publication becoming an adopter-branded HTML/text package;
- no source-brand leakage into the rendered HTML;
- refusal when approved content is below the requested item-count minimum;
- refusal of content that is published but not `human_approved`;
- refusal of delivery authorization without the explicit human flag;
- authorization without any external-send claim;
- receipt refusal after manifest tampering;
- provider-reference requirement for `sent` evidence; and
- a delivered receipt cryptographically bound to the authorized artifact.

## Evidence level

This is **L1 / internally exercised**.

Recipient-deliverable readiness may move provisionally from the 30% seed baseline to roughly **55%**. The 65–75% target band remains unavailable until a real/representative recipient actually receives an agreed artifact on the agreed cadence and the delivery evidence is recorded.

## Remaining AP5 acceptance

A human/provider must:

1. choose the real recipient/channel/address under the adopter's privacy and responsibility rules;
2. prepare a package meeting the real target item count and freshness requirement;
3. explicitly authorize those exact bytes for delivery;
4. send through the selected external channel/provider;
5. record provider/human evidence tied to the prepared manifest;
6. confirm the recipient received and could use the artifact; and
7. repeat enough cycles to support whatever cadence/reliability claim is eventually made.

## Next packet

Proceed to **AP6 — procurement and trust packet**.

AP6 should consolidate facts already evidenced in the repository and turn unresolved matters into explicit human decision fields. It must not choose licensing, pricing, SLA, warranty, privacy commitments, or certifications on the owner's behalf.