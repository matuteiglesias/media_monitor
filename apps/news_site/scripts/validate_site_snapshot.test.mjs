import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, stableValue(value[key])]),
    );
  }

  return value;
}

function snapshotId(snapshot) {
  const payload = structuredClone(snapshot);
  delete payload.snapshot_id;
  delete payload.generated_at;

  return crypto
    .createHash("sha256")
    .update(JSON.stringify(stableValue(payload)), "utf8")
    .digest("hex");
}

test("canonical snapshot ID is deterministic", () => {
  const snapshot = {
    schema_name: "site_snapshot.v1",
    generated_at: "2026-07-21T19:39:40Z",
    status: "ok",
    digest_at: "20260721T18",
    site: {
      site_id: "argentina-general",
      name: "Actualidad Argentina",
      tagline: "Noticias recientes de Argentina",
      locale: "es-AR",
    },
    metrics: {
      item_count: 0,
      section_count: 0,
    },
    hero: null,
    latest: [],
    sections: [],
    provenance: {},
  };

  assert.equal(snapshotId(snapshot), snapshotId(structuredClone(snapshot)));

  const changedGeneratedAt = {
    ...snapshot,
    generated_at: "2026-07-21T20:00:00Z",
  };

  assert.equal(snapshotId(snapshot), snapshotId(changedGeneratedAt));
});
