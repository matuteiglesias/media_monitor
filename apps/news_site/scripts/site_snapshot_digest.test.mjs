import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { resolveRequestedDigest } from "./site_snapshot_digest.mjs";

function writeSnapshot(payload) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "site-snapshot-digest-"));
  const snapshotPath = path.join(directory, "site_snapshot.json");
  fs.writeFileSync(snapshotPath, `${JSON.stringify(payload)}\n`, "utf8");
  return { directory, snapshotPath };
}

function withSnapshot(payload, callback) {
  const { directory, snapshotPath } = writeSnapshot(payload);
  try {
    callback(snapshotPath);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

test("uses the generated snapshot digest when DIGEST_AT is absent", () => {
  withSnapshot({ digest_at: "20260804T14" }, (snapshotPath) => {
    assert.equal(
      resolveRequestedDigest({ snapshotPath, requestedDigest: undefined }),
      "20260804T14",
    );
  });
});

test("accepts a matching caller digest assertion", () => {
  withSnapshot({ digest_at: "20260804T14" }, (snapshotPath) => {
    assert.equal(
      resolveRequestedDigest({
        snapshotPath,
        requestedDigest: "20260804T14",
      }),
      "20260804T14",
    );
  });
});

test("rejects a mismatching caller digest assertion", () => {
  withSnapshot({ digest_at: "20260804T14" }, (snapshotPath) => {
    assert.throws(
      () =>
        resolveRequestedDigest({
          snapshotPath,
          requestedDigest: "20260804T13",
        }),
      /does not match DIGEST_AT/,
    );
  });
});

test("rejects malformed JSON", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "site-snapshot-digest-"));
  const snapshotPath = path.join(directory, "site_snapshot.json");
  fs.writeFileSync(snapshotPath, "{not-json\n", "utf8");
  try {
    assert.throws(
      () => resolveRequestedDigest({ snapshotPath }),
      /not valid JSON/,
    );
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});

test("rejects a snapshot without a usable digest", () => {
  withSnapshot({ digest_at: "" }, (snapshotPath) => {
    assert.throws(
      () => resolveRequestedDigest({ snapshotPath }),
      /digest_at must be a non-empty string/,
    );
  });
});
