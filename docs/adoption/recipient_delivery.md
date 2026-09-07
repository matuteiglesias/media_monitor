# Recipient delivery boundary

> **Status:** AP5 internal implementation · preparation/evidence tooling only · no sender/provider integration

## Purpose

Close the gap between Media Monitor's governed internal/publication state and the artifact an adopter's recipient actually consumes, without turning the repository into an omnichannel notification system.

The first supported adoption deliverable is the `html_email_brief` already requested by the representative adopter intake.

## Authority model

AP5 separates three operations:

```text
validated intake + site_snapshot.v4
        |
        | human-approved published_article.v1 only
        v
prepare
        |
        +--> brief.html
        +--> brief.txt
        +--> delivery_manifest.json
        |
        | no send claim
        v
explicit human delivery authorization
        |
        +--> delivery_authorization.json
        |
        | external sender/provider acts outside this repository tool
        v
record provider/human delivery evidence
        |
        +--> delivery_receipts.jsonl
```

`prepare` never sends anything. `authorize` never sends anything. `record` never contacts a provider; it records externally supplied evidence after an external sender/provider action.

## Content authority

The recipient brief is built only from articles that are already:

- `published_article.v1`;
- `status=published`; and
- `review_status=human_approved`.

The AP5 package does not deliver arbitrary drafts, raw LLM output, or deterministic monitored-signal selection as if it were human-approved editorial content.

If the intake requires evidence links, every included article must expose source links.

## Item-count acceptance

`target_item_count` from the adopter intake is an executable constraint.

Accepted forms are:

- integer, such as `5`; or
- range, such as `5-10`.

Preparation fails if there are fewer approved items than the requested minimum. When more than the requested maximum exist, the package uses the first approved items in snapshot publication order up to that maximum.

This prevents a one-item fixture from masquerading as an accepted 5–10 item executive brief.

## Recipient identity and privacy

The prepared package records only the **recipient role** from the intake. It deliberately does not invent or persist a recipient email address.

Actual recipient addressing belongs to the external sender/provider or later adopter-specific configuration after the relevant human/privacy decision.

Brand identity comes from the adopter intake, not from the source snapshot's public-site brand.

## Commands

Prepare only:

```bash
python scripts/adopter_delivery.py prepare \
  --intake docs/adoption/adopter_intake.example.yaml \
  --snapshot <validated-site-snapshot.json> \
  --out <isolated-delivery-dir>
```

Explicitly authorize the exact manifest bytes:

```bash
python scripts/adopter_delivery.py authorize \
  --manifest <isolated-delivery-dir>/delivery_manifest.json \
  --authorization <isolated-delivery-dir>/delivery_authorization.json \
  --reviewer <human-role-or-name> \
  --note '<review note>' \
  --approve-delivery-human
```

After a real external sender/provider action, record evidence:

```bash
python scripts/adopter_delivery.py record \
  --manifest <isolated-delivery-dir>/delivery_manifest.json \
  --authorization <isolated-delivery-dir>/delivery_authorization.json \
  --receipts <isolated-delivery-dir>/delivery_receipts.jsonl \
  --status delivered \
  --actor <human-or-provider-operator> \
  --provider-message-ref <provider-reference> \
  --note '<delivery evidence note>'
```

## Integrity rules

- authorization SHA-binds the exact prepared manifest;
- authorization also binds the HTML/text artifact hashes;
- any manifest mutation after authorization invalidates later receipt recording;
- `sent`/`delivered` receipts require a non-empty provider message/reference;
- the receipt names its evidence source as human/provider-supplied evidence;
- no code path in AP5 performs the network send.

## What AP5 proves

Internally, AP5 can prove that a validated adopter requirement can become a branded recipient-ready HTML/text artifact from governed, human-approved content, with enough cryptographic linkage to record a later delivery truthfully.

It does **not** prove that a recipient has received the artifact. That requires an actual external send plus receipt evidence and remains the L2 acceptance step.

## Non-goals

- SMTP/provider integration before a real adopter selects it;
- recipient-address database;
- WhatsApp/Slack/PDF channel suite;
- automatic delivery authorization;
- treating generated drafts as delivered content;
- claiming delivery from artifact preparation alone.