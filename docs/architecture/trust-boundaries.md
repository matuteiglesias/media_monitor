# Trust and mutation boundaries

> **Status:** canonical architecture · **Verified against:** `bf04a74`

| Boundary | Trusted input | Allowed mutation | Required denial / validation |
|---|---|---|---|
| public RSS → acquire | configured HTTPS feeds | isolated workspace/run prefix | parse failures quarantine; feed data has no state authority |
| producer → local/S3 evidence | stage outputs and manifest | unique run prefix only | producer cannot write canonical generation/current state |
| compactor → canonical sensing | finalized checksum-valid bundles | generation then `current.json` | reject unsafe paths, checksum mismatch, invalid status/candidates |
| PostgreSQL queue → enrich | request identity/payload | enrich result and queue status under worker semantics | credentials stay in environment; no public snapshot exposure |
| LLM/PromptFlow → editorial | raw model output | quarantine or schema-valid brief/draft artifacts | raw output cannot become published content directly |
| editorial → publication | exactly one valid draft | published bus only after explicit approval | command refuses without `--approve-human` |
| internal state → public data | named validated indexes/contracts | allowlisted snapshot | strip internal paths/state and fail missing/invalid inputs |
| repository → AWS | immutable image digest, saved Terraform plan | declared ECR/ECS/S3/log/network resources | least-authority producer denial probe; teardown confirmation |
| repository → Vercel | validated prebuilt snapshot | deployment only | health response must reconcile snapshot identity; no source mutation |
| browser → site | public snapshot/routes | none | browser never receives storage credentials or write authority |

## Secrets and sensitive state

`PG_DSN`, AWS credentials/profile, and provider tokens remain environment/provider inputs and must not be committed or copied into snapshots. Public projections expose only contract fields needed for rendering. Logs and observability records may contain operational context and are evidence surfaces, not public content.

## Maturity boundary

The AWS packet is implemented, locally validated, and deployment-ready. Repository evidence does not prove deployed or operated state. Vercel tooling and runbooks exist, but live project configuration and repeated operation are likewise not established here.
