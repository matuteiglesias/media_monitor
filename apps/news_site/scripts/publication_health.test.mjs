import assert from "node:assert/strict";
import test from "node:test";

import {
  buildPublicationHealth,
  freshnessLead,
} from "../lib/publication_health.mjs";

function snapshot(times) {
  const latest = times.map((published_at, index) => ({
    index_id: `id-${index}`,
    title: `Title ${index}`,
    topic: "All Topics",
    published_at,
    link: `https://example.test/${index}`,
    source: "Example",
  }));
  return {
    schema_name: "site_snapshot.v1",
    snapshot_id: "a".repeat(64),
    digest_at: "20260824T17",
    site: { site_id: "argentina-general" },
    hero: latest[0],
    latest,
  };
}

function snapshotV2(times) {
  const legacy = snapshot(times);
  return {
    schema_name: "site_snapshot.v2",
    snapshot_id: legacy.snapshot_id,
    digest_at: legacy.digest_at,
    site: legacy.site,
    signals: { hero: legacy.hero, latest: legacy.latest, sections: [] },
    publication: { featured: null, latest: [] },
    articles: {},
  };
}

function snapshotV3(times) {
  const value = snapshotV2(times);
  return {
    ...value,
    schema_name: "site_snapshot.v3",
    signals: {
      ...value.signals,
      curated: [
        {
          ...value.signals.latest[0],
          published_at: "2025-01-01T00:00:00Z",
          rank: 1,
          score: 1,
          score_components: {},
          reason_codes: ["test"],
        },
      ],
    },
  };
}

function snapshotV4(times) {
  const value = snapshotV3(times);
  return {
    ...value,
    schema_name: "site_snapshot.v4",
    story_contexts: {
      [value.signals.latest[0].index_id]: {
        schema_name: "story_context.v1",
        coverage_latest_published_at: "2024-01-01T00:00:00Z",
      },
    },
  };
}

test("fresh publication is current and within target", () => {
  const health = buildPublicationHealth(
    snapshot(["2026-08-24T16:00:00Z"]),
    "2026-08-24T17:00:00Z",
  );
  assert.equal(health.schema_name, "publication_health.v1");
  assert.equal(health.age_minutes, 60);
  assert.equal(health.freshness_status, "FRESH");
  assert.equal(health.within_target, true);
  assert.equal(health.is_current, true);
  assert.equal(freshnessLead(health), "Actualizado");
});

test("v2 freshness is derived only from monitored signals", () => {
  const value = snapshotV2(["2026-08-24T16:30:00Z"]);
  value.publication = {
    featured: { published_at: "2025-01-01T00:00:00Z" },
    latest: [{ published_at: "2025-01-01T00:00:00Z" }],
  };
  const health = buildPublicationHealth(value, "2026-08-24T17:00:00Z");
  assert.equal(health.newest_item_at, "2026-08-24T16:30:00.000Z");
  assert.equal(health.age_minutes, 30);
  assert.equal(health.within_target, true);
});

test("v3 freshness follows chronological wire rather than curated ranking", () => {
  const value = snapshotV3(["2026-08-24T16:40:00Z"]);
  const health = buildPublicationHealth(value, "2026-08-24T17:00:00Z");
  assert.equal(health.newest_item_at, "2026-08-24T16:40:00.000Z");
  assert.equal(health.age_minutes, 20);
  assert.equal(health.within_target, true);
});

test("v4 freshness ignores story-context timestamps", () => {
  const value = snapshotV4(["2026-08-24T16:45:00Z"]);
  const health = buildPublicationHealth(value, "2026-08-24T17:00:00Z");
  assert.equal(health.newest_item_at, "2026-08-24T16:45:00.000Z");
  assert.equal(health.age_minutes, 15);
  assert.equal(health.within_target, true);
});

test("target miss can remain fresh without claiming target compliance", () => {
  const health = buildPublicationHealth(
    snapshot(["2026-08-24T14:30:00Z"]),
    "2026-08-24T17:00:00Z",
  );
  assert.equal(health.age_minutes, 150);
  assert.equal(health.freshness_status, "FRESH");
  assert.equal(health.within_target, false);
  assert.equal(health.is_current, true);
  assert.equal(freshnessLead(health), "Última actualización");
});

test("publication degrades after three hours", () => {
  const health = buildPublicationHealth(
    snapshot(["2026-08-24T13:00:00Z"]),
    "2026-08-24T17:00:00Z",
  );
  assert.equal(health.freshness_status, "DEGRADED");
  assert.equal(health.is_current, false);
  assert.equal(freshnessLead(health), "Actualización demorada");
});

test("publication is stale after six hours and cannot claim current copy", () => {
  const health = buildPublicationHealth(
    snapshot(["2026-08-24T10:00:00Z"]),
    "2026-08-24T17:00:00Z",
  );
  assert.equal(health.age_minutes, 420);
  assert.equal(health.freshness_status, "STALE");
  assert.equal(health.is_current, false);
  assert.equal(freshnessLead(health), "Actualización temporalmente demorada");
  assert.notEqual(freshnessLead(health), "Actualizado");
});

test("newest monitored item wins even when latest is unsorted", () => {
  const health = buildPublicationHealth(
    snapshot([
      "2026-08-24T12:00:00Z",
      "2026-08-24T16:30:00Z",
      "2026-08-24T15:00:00Z",
    ]),
    "2026-08-24T17:00:00Z",
  );
  assert.equal(health.newest_item_at, "2026-08-24T16:30:00.000Z");
  assert.equal(health.age_minutes, 30);
  assert.equal(health.freshness_status, "FRESH");
});

test("missing monitored items fail closed", () => {
  assert.throws(
    () => buildPublicationHealth({ site: { site_id: "x" }, snapshot_id: "s", digest_at: "d", latest: [] }),
    /no monitored items/,
  );
  assert.throws(
    () => buildPublicationHealth({ schema_name: "site_snapshot.v4", site: { site_id: "x" }, snapshot_id: "s", digest_at: "d", signals: { latest: [] } }),
    /no monitored items/,
  );
});
