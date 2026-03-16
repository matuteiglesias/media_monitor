#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/home/matias/repos/media_monitor"
BRANCH="main"
DIGEST_AT="${DIGEST_AT:-$(date -u +%Y%m%dT%H)}"

cd "$REPO_ROOT"

git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

make build-news-access-indexes DIGEST_AT="$DIGEST_AT"
make build-editorial-access-indexes DIGEST_AT="$DIGEST_AT"

npm --prefix apps/news_site run refresh-data

git add apps/news_site/public/data

if git diff --cached --quiet; then
  echo "[news-site-refresh] no public snapshot changes"
  exit 0
fi

git commit -m "Refresh deployable public data snapshots"
git push origin "$BRANCH"

echo "[news-site-refresh] pushed updated public snapshots"
