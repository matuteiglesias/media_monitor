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

function writeRequiredNews(repoRoot) {
  fs.writeFileSync(
    path.join(repoRoot, "storage", "indexes", "news_recent_refs_latest.jsonl"),
    '{"digest_at":"20260713T19","title":"Fresh","topic":"All Topics","published_at":"2026-07-13T19:00:00Z","link":"https://example.com/a"}\n',
    "utf-8",
  );
  fs.writeFileSync(
    path.join(repoRoot, "storage", "indexes", "news_recent_groups_latest.jsonl"),
    '{"digest_at":"20260713T19","window_type":"1h_window","topic":"All Topics","group_number":1,"article_count":1,"top_titles":["Fresh"]}\n',
    "utf-8",
  );
}

test("copies required snapshots and requires editorial by default", () => {
  const repoRoot = mkRepo();
  ensureDirs(repoRoot);
  writeRequiredNews(repoRoot);

  assert.throws(
    () => refreshPublicData({ repoRoot }),
    /Missing required editorial snapshot/,
  );
});

test("writes editorial fallback only when explicitly allowed", () => {
  const repoRoot = mkRepo();
  ensureDirs(repoRoot);
  writeRequiredNews(repoRoot);

  const oldValue = process.env.ALLOW_EDITORIAL_FALLBACK;
  process.env.ALLOW_EDITORIAL_FALLBACK = "1";
  try {
    const result = refreshPublicData({ repoRoot });
    assert.equal(result.editorial, "fallback_written");
  } finally {
    if (oldValue === undefined) delete process.env.ALLOW_EDITORIAL_FALLBACK;
    else process.env.ALLOW_EDITORIAL_FALLBACK = oldValue;
  }

  const fallback = JSON.parse(
    fs.readFileSync(path.join(repoRoot, "apps", "news_site", "public", "data", "editorial_latest.json"), "utf-8"),
  );
  assert.equal(fallback.status, "missing_editorial_index");
  assert.equal(fallback.source, "editorial_fallback");
});

test("fails loudly when required snapshots are missing", () => {
  const repoRoot = mkRepo();
  ensureDirs(repoRoot);

  assert.throws(
    () => refreshPublicData({ repoRoot }),
    /Missing required snapshot/,
  );
});

test("does not clobber the public snapshot when the source is invalid", () => {
  const repoRoot = mkRepo();
  ensureDirs(repoRoot);
  const publicRefs = path.join(repoRoot, "apps", "news_site", "public", "data", "news_recent_refs_latest.jsonl");
  fs.writeFileSync(publicRefs, '{"digest_at":"old","title":"Old"}\n', "utf-8");
  fs.writeFileSync(path.join(repoRoot, "storage", "indexes", "news_recent_refs_latest.jsonl"), "", "utf-8");
  fs.writeFileSync(path.join(repoRoot, "storage", "indexes", "news_recent_groups_latest.jsonl"), '{}\n', "utf-8");

  assert.throws(
    () => refreshPublicData({ repoRoot }),
    /Required snapshot is empty/,
  );
  assert.equal(fs.readFileSync(publicRefs, "utf-8"), '{"digest_at":"old","title":"Old"}\n');
});
