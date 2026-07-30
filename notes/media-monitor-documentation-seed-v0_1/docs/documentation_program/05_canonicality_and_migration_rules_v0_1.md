# media_monitor documentation canonicality and migration rules v0.1

## Classes

| Class | Purpose | Owns current commands? |
|---|---|---:|
| canonical | current reader truth | yes |
| supporting | detailed component/evidence context | only by link |
| historical | past PR, migration, or architecture state | no |
| generated | derived reference with named generator | only when designated |

## Directory policy

- `docs/` is the canonical documentation surface.
- `notes/`, `docs/notes/`, `legacy/notes/`, and retrofit bundles are not
  canonical reader entrances.
- `docs/runbooks/` may contain canonical runbooks only when named by capability,
  not by implementation PR.
- App-local READMEs should remain concise ownership summaries and link to
  canonical component/operation pages.
- `infra/*/README.md` may own infrastructure-adjacent details but must be linked
  from the canonical deployment runbook.

## Migration protocol

1. Inventory and classify.
2. Verify unique claims against source and evidence.
3. Create the capability-oriented canonical page.
4. Link supporting/module pages to it.
5. Mark old documents historical or superseded with timeframe/commit.
6. Check inbound links.
7. Preserve unique decisions, incidents, and migration evidence.
8. Delete only after human confirmation that no unique knowledge is lost.

## Immediate drift to address after inventory acceptance

The acquisition runbook's statement that Terraform remains future work must be
removed or converted into historical context because `infra/aws/sensing/`
exists on current main.

## Naming

Prefer:

- `aws-sensing-deployment.md`
- `sensing-compaction-and-recovery.md`
- `editorial-human-last-mile.md`

Avoid permanent canonical names such as:

- `pr5-minimal-autonomous-loop.md`
- `pr4c-news-acquire-code-migration.md`
- `latest-new-runbook.md`

## Update obligations

A PR changing any of these must name affected canonical docs:

- Make targets, scripts, or entrypoints;
- lane ownership;
- environment/configuration;
- schema or identity rules;
- bus/index/snapshot paths;
- mutable pointer or writer authority;
- AWS/Vercel infrastructure;
- approval/publication behavior;
- maturity/status claims.

A claimed `N/A` documentation impact requires a reason.
