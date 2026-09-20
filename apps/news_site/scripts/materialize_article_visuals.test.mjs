import test from "node:test";
import assert from "node:assert/strict";

import {
  deriveArticleVisualTags,
  rankSouthlandVisualAssets,
} from "./lib/southland_visual_matcher.mjs";

const rules = {
  schema_name: "southland_visual_tag_rules.v1",
  rules: [
    { tag: "character:javier_milei", kind: "character", keywords: ["javier milei", "javier mieli"] },
    { tag: "character:luis_caputo", kind: "character", keywords: ["luis caputo", "toto capuccino"] },
    { tag: "topic:politica", kind: "topic", keywords: ["politica", "gobierno"] },
    { tag: "scene:meeting", kind: "scene", keywords: ["reunion"] },
  ],
};

function asset(overrides = {}) {
  return {
    asset_id: "southland_asset",
    public_path: "/southland/visuals/a.png",
    created_at: "2026-09-20T00:00:00Z",
    status: "approved",
    identity_status: "confirmed",
    character_tags: [],
    institution_tags: [],
    topic_tags: [],
    scene_tags: [],
    motif_tags: [],
    alt: "asset",
    ...overrides,
  };
}

test("article visual tags are deterministic and recognize Southland aliases", () => {
  const tags = deriveArticleVisualTags(
    {
      title: "Javier Mieli llegó al gobierno",
      summary: "Una reunión política.",
      body_md: "Texto",
      topic: "Política",
    },
    rules,
  );
  assert.deepEqual(tags, [
    "character:javier_milei",
    "scene:meeting",
    "topic:politica",
  ]);
});

test("wrong named character is rejected despite generic topic overlap", () => {
  const result = rankSouthlandVisualAssets({
    articleTags: ["character:javier_milei", "topic:politica"],
    assets: [
      asset({
        asset_id: "wrong",
        character_tags: ["character:luis_caputo"],
        topic_tags: ["topic:politica"],
      }),
    ],
  });
  assert.deepEqual(result, []);
});

test("character match outranks generic asset, then tag count, then recency", () => {
  const result = rankSouthlandVisualAssets({
    articleTags: ["character:javier_milei", "topic:politica", "scene:meeting"],
    assets: [
      asset({
        asset_id: "generic-many",
        created_at: "2026-09-20T03:00:00Z",
        topic_tags: ["topic:politica"],
        scene_tags: ["scene:meeting"],
        identity_status: "generic",
      }),
      asset({
        asset_id: "character-old",
        created_at: "2026-09-19T03:00:00Z",
        character_tags: ["character:javier_milei"],
        topic_tags: ["topic:politica"],
      }),
      asset({
        asset_id: "character-new",
        created_at: "2026-09-20T02:00:00Z",
        character_tags: ["character:javier_milei"],
        topic_tags: ["topic:politica"],
      }),
    ],
    maxMatches: 2,
  });

  assert.deepEqual(result.map((row) => row.asset_id), [
    "character-new",
    "character-old",
  ]);
});

test("pending-lineage and missing-file assets are ineligible", () => {
  const result = rankSouthlandVisualAssets({
    articleTags: ["topic:politica"],
    assets: [
      asset({
        asset_id: "pending",
        identity_status: "pending_lineage",
        topic_tags: ["topic:politica"],
      }),
      asset({
        asset_id: "missing",
        identity_status: "generic",
        topic_tags: ["topic:politica"],
      }),
      asset({
        asset_id: "available",
        identity_status: "generic",
        topic_tags: ["topic:politica"],
      }),
    ],
    fileExists: (row) => row.asset_id === "available",
  });
  assert.deepEqual(result.map((row) => row.asset_id), ["available"]);
});

test("zero overlapping tags intentionally yields no visual", () => {
  const result = rankSouthlandVisualAssets({
    articleTags: ["topic:politica"],
    assets: [asset({ topic_tags: ["topic:economia"], identity_status: "generic" })],
  });
  assert.deepEqual(result, []);
});
