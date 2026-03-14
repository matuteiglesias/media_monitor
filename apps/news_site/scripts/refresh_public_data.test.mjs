import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { refreshPublicData } from "./refresh_public_data.mjs";

function mkRepo() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "news-site-refresh-"));
}

function ensureDirs(repoRoot) {
  fs.mkdirSync(path.join(repoRoot, "storage", "indexes"), { recursive: true });
  fs.mkdirSync(path.join(repoRoot, "apps", "news_site", "public", "data"), { recursive: true });
}

test("copies required snapshots and writes editorial fallback when missing", () => {
  const repoRoot = mkRepo();
  ensureDirs(repoRoot);

  fs.writeFileSync(
    path.join(repoRoot, "storage", "indexes", "news_recent_refs_latest.jsonl"),
    '{"id":"a"}\n',
    "utf-8",
  );
  fs.writeFileSync(
    path.join(repoRoot, "storage", "indexes", "news_recent_groups_latest.jsonl"),
    '{"topic":"x"}\n',
    "utf-8",
  );

  const result = refreshPublicData({ repoRoot });
  assert.equal(result.editorial, "fallback_written");

  const fallback = JSON.parse(
    fs.readFileSync(path.join(repoRoot, "apps", "news_site", "public", "data", "editorial_latest.json"), "utf-8"),
  );
  assert.equal(fallback.status, "missing_editorial_index");
});

test("fails loudly when required snapshots are missing", () => {
  const repoRoot = mkRepo();
  ensureDirs(repoRoot);

  assert.throws(
    () => refreshPublicData({ repoRoot }),
    /Missing required snapshot/,
  );
});
