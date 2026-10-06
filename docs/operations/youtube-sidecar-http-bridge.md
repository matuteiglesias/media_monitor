# Private YouTube sidecar HTTP bridge

## Purpose and scope

This service is a thin private HTTP projection over the existing governed Media Watch YouTube sidecar. It does not own follow state, channel watch membership, scheduling, upload-frontier discovery, or summary semantics.

Exact routes:

- `POST /v1/youtube/videos/ensure`
- `POST /v1/youtube/videos/inspect`
- `POST /v1/youtube/videos/summary`

Each POST accepts only:

```json
{"video_id":"abcdefghijk"}
```

Successful responses are the existing `youtube_video_sidecar.v1` object. The summary route therefore exposes the same `available`, `not_attempted`, `provider_limit`, and `failed` states already governed by Media Watch.

## Runtime configuration

The bridge uses these server-side variables:

| Variable | Requirement |
| --- | --- |
| `MEDIA_WATCH_STORE_ROOT` | Required on Cloud Run. Must point at the authoritative writable Media Watch filesystem state. |
| `YOUTUBE_API_KEY` | Required only when `ensure` receives a video not already present in governed state. |
| `GEMINI_API_KEY` | Required only when `summary` must generate a summary rather than reuse a cached artifact. |
| `GEMINI_MODEL` | Optional; existing Media Watch default applies when unset. |
| `PORT` | Cloud Run supplies this; defaults to `8080` for local/container execution. |
| `HOST` | Optional; defaults to `0.0.0.0`. |
| `LOG_LEVEL` | Optional; defaults to `INFO`. |

On Cloud Run the process refuses to silently fall back to the container-local default store when `MEDIA_WATCH_STORE_ROOT` is missing. The current `MediaWatchStore` is filesystem-backed, so a production deployment must mount the same durable POSIX-compatible state expected by Media Watch. An unmounted Cloud Run container filesystem is not an authoritative persistence layer.

The current store is not a transactional multi-writer backend. For this v1 bridge, deploy one instance with request concurrency 1 unless/until storage concurrency semantics are deliberately redesigned. The bridge also serializes mutation operations inside its process.

## Authentication boundary

Keep the Cloud Run service private and use Cloud Run IAM. Do not add an application bearer token or shared secret.

The calling `youtube-following` service identity should receive `roles/run.invoker` on this service and send a short-lived Google-signed identity token. The token audience should be the receiving service's `*.run.app` URL unless a Cloud Run custom audience is explicitly configured.

The application does not bind itself to a caller service-account name. IAM authorization remains a deployment concern outside the Python handler.

## Caller configuration

The current `youtube-following` adapter expects:

```text
MEDIA_MONITOR_SIDECAR_URL=https://<private-service>.<region>.run.app
MEDIA_MONITOR_SIDECAR_AUDIENCE=https://<private-service>.<region>.run.app
MEDIA_MONITOR_ENSURE_PATH=/v1/youtube/videos/ensure
MEDIA_MONITOR_INSPECT_PATH=/v1/youtube/videos/inspect
MEDIA_MONITOR_SUMMARY_PATH=/v1/youtube/videos/summary
```

`MEDIA_MONITOR_SIDECAR_AUDIENCE` may be omitted when the service URL origin is the intended audience, because the caller defaults the audience to that origin.

The caller currently uses a 30-second request timeout. This bridge deliberately keeps summary generation synchronous because that is the existing governed Media Watch behavior; rollout should verify that the selected summary path fits that caller timeout or adjust the caller separately.

## Failure semantics

Client-visible failures are bounded JSON objects:

```json
{"error":{"code":"video_not_found","message":"YouTube video was not found"}}
```

The bridge does not return API keys, provider payloads, exception messages, stack traces, or filesystem paths. Structured server logs include route, status/code, video ID when safe, and exception class only.

`inspect` never makes a provider call. `ensure` never generates a summary. `summary` reuses a cached summary before constructing a provider. Provider-limit and failed summary attempts remain governed sidecar states rather than partial summary artifacts.

## Deployment status

`Dockerfile.media-watch-sidecar` is the deployable container boundary. This repository change does not provision a Cloud Run service, IAM binding, persistent store, secret binding, or production traffic. Provider-side deployment and live private invocation require separate operator evidence.
