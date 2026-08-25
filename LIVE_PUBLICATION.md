# Live publication golden path

Use this when the monitored outlet is stale and you want one command to acquire fresh source material and publish the exact resulting digest.

```bash
bin/media-refresh --target preview
```

After inspecting the preview:

```bash
bin/media-refresh --target production
```

`media-refresh` deliberately runs the live sensing lane first with network acquisition enabled, then passes the same UTC digest to the existing verified publication command. It never promotes editorial drafts and does not bypass the human publication gate.

## Why `bin/media publish` can fail on an old checkout/runtime state

`publish` assumes the leased sensing digest is already suitable for a current publication roll. Deterministic selection evaluates candidate `published_at` timestamps against the current time and the configured freshness window. If the newest sensing bundle is several hours or days old, selection correctly rejects the candidates as stale.

For a current outlet, prefer `bin/media-refresh`. Use `bin/media publish --digest-at ...` only when you intentionally already have fresh/coherent sensing artifacts for that digest.

## Local repository sync

If `git pull` says the current `main` has no tracking branch, repair it once:

```bash
git switch main
git branch --set-upstream-to=origin/main main
git pull --ff-only
```

Untracked local files are not removed by this operation. If a local tracked change prevents fast-forwarding, inspect/stash/commit it rather than forcing the branch.
