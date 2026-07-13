#!/usr/bin/env bash
set -euo pipefail

DIGEST_AT="${DIGEST_AT:-$(date -u +%Y%m%dT%H)}"
export DIGEST_AT
MANIFEST="${PUBLISH_MANIFEST:-apps/news_site/public/data/publish_manifest.json}"
PYTHON_BIN="${PYTHON:-}"

if [ -z "${PYTHON_BIN}" ]; then
  if [ -x ./.venv/bin/python ]; then
    PYTHON_BIN="./.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "[publish-news-site] ERROR: no project Python found (tried PYTHON, ./.venv/bin/python, python3, python)" >&2
    exit 2
  fi
fi
export PYTHON="${PYTHON_BIN}"

echo "[publish-news-site] digest_at=${DIGEST_AT}"
make build-news-access-indexes DIGEST_AT="${DIGEST_AT}" PYTHON="${PYTHON_BIN}"
make build-editorial-access-indexes DIGEST_AT="${DIGEST_AT}"
make validate-publish-surface DIGEST_AT="${DIGEST_AT}" PYTHON="${PYTHON_BIN}"
npm --prefix apps/news_site run refresh-data
SMOKE_OUTPUT="$(npm --prefix apps/news_site run --silent smoke:public-data)"
export SMOKE_OUTPUT
echo "${SMOKE_OUTPUT}"
npm --prefix apps/news_site run build

node -e '
const fs = require("fs");
const cp = require("child_process");
const manifestPath = process.argv[1];
const smoke = process.env.SMOKE_OUTPUT || "";
const jsonStart = smoke.indexOf("{");
const validation = jsonStart >= 0 ? JSON.parse(smoke.slice(jsonStart)) : null;
const manifest = {
  generated_at: new Date().toISOString(),
  digest_at: process.env.DIGEST_AT,
  git_sha: cp.execSync("git rev-parse HEAD", {encoding:"utf8"}).trim(),
  validation,
};
fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
console.log(`[publish-news-site] manifest=${manifestPath}`);
' "${MANIFEST}"
