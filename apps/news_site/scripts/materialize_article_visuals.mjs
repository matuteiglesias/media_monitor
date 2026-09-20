import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import {
  deriveArticleVisualTags,
  rankSouthlandVisualAssets,
  resolvePublicAssetPath,
} from "./lib/southland_visual_matcher.mjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(appRoot, "..", "..");
const snapshotPath = path.join(appRoot, "public", "data", "site_snapshot.json");
const presentationPath = path.join(appRoot, "config", "site_presentation.json");
const outputPath = path.join(appRoot, "public", "data", "article_visuals.json");

function fail(message) {
  throw new Error(`materialize_article_visuals: ${message}`);
}

function readJson(filePath, label) {
  if (!fs.existsSync(filePath)) fail(`missing ${label}: ${filePath}`);
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function repoFile(relativePath, label) {
  const resolved = path.resolve(repoRoot, relativePath);
  if (!resolved.startsWith(`${repoRoot}${path.sep}`)) fail(`${label} escapes repository root`);
  if (!fs.existsSync(resolved)) fail(`missing ${label}: ${relativePath}`);
  return resolved;
}

const snapshot = readJson(snapshotPath, "site snapshot");
const presentation = readJson(presentationPath, "site presentation");
if (snapshot?.schema_name !== "site_snapshot.v4") fail("expected site_snapshot.v4");
if (presentation?.schema_name !== "site_presentation.v1") fail("expected site_presentation.v1");

const southlandCurated =
  presentation?.theme === "southland" &&
  presentation?.mode === "publication";

let payload;

if (southlandCurated) {
  const registryPath = repoFile(
    presentation.visual_asset_registry ?? "config/southland_visual_assets.v1.json",
    "Southland visual asset registry",
  );
  const rulesPath = repoFile(
    presentation.visual_tag_rules ?? "config/southland_visual_tag_rules.v1.json",
    "Southland visual tag rules",
  );
  const registry = readJson(registryPath, "Southland visual asset registry");
  const rules = readJson(rulesPath, "Southland visual tag rules");
  if (registry?.schema_name !== "southland_visual_assets.v1") {
    fail("expected southland_visual_assets.v1");
  }

  const maxMatches = Number.isInteger(presentation.visual_max_matches)
    ? presentation.visual_max_matches
    : 2;
  if (maxMatches < 0 || maxMatches > 2) fail("visual_max_matches must be between 0 and 2");

  const projection = {};
  let matchedArticleCount = 0;
  let missingFileCount = 0;

  const fileExists = (asset) => {
    const resolved = resolvePublicAssetPath(appRoot, asset?.public_path);
    if (!resolved || !fs.existsSync(resolved)) {
      missingFileCount += 1;
      return false;
    }
    return true;
  };

  for (const [slug, article] of Object.entries(snapshot.articles ?? {})) {
    const articleTags = deriveArticleVisualTags(article, rules);
    const matches = rankSouthlandVisualAssets({
      articleTags,
      assets: registry.assets,
      maxMatches,
      fileExists,
    });
    if (matches.length) matchedArticleCount += 1;
    projection[slug] = {
      kind: "curated_asset_matches",
      article_tags: articleTags,
      matches,
    };
  }

  payload = {
    schema_name: "article_visuals.v2",
    strategy: "southland_tag_match_v1",
    max_matches: maxMatches,
    articles: Object.fromEntries(
      Object.entries(projection).sort(([a], [b]) => a.localeCompare(b)),
    ),
    metrics: {
      article_count: Object.keys(projection).length,
      matched_article_count: matchedArticleCount,
      unmatched_article_count: Object.keys(projection).length - matchedArticleCount,
      missing_asset_file_observations: missingFileCount,
    },
  };
} else {
  const palettes = [
    ["#f6d44a", "#e95d4f", "#2f6f68", "#f4efe2"],
    ["#7fc6b5", "#ef8b4a", "#5c4c8a", "#f5e6c8"],
    ["#e7bf5a", "#b64b4b", "#3f6b8a", "#f1ead9"],
    ["#d7e55c", "#ef6c57", "#496b55", "#eee3cb"],
  ];

  const projection = {};
  for (const [slug, article] of Object.entries(snapshot.articles ?? {})) {
    const digest = crypto.createHash("sha256").update(slug).digest("hex");
    const seed = Number.parseInt(digest.slice(0, 8), 16);
    const palette = palettes[seed % palettes.length];
    projection[slug] = {
      kind: presentation.mode === "publication" ? "cutpaper_generated" : "editorial_card",
      seed,
      palette,
      alt: presentation.mode === "publication"
        ? `Ilustración original de Southland para: ${article.title}`
        : `Tarjeta editorial para: ${article.title}`,
    };
  }

  payload = {
    schema_name: "article_visuals.v1",
    articles: Object.fromEntries(
      Object.entries(projection).sort(([a], [b]) => a.localeCompare(b)),
    ),
  };
}

fs.mkdirSync(path.dirname(outputPath), { recursive: true });
const tmp = `${outputPath}.tmp`;
fs.writeFileSync(tmp, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
fs.renameSync(tmp, outputPath);
console.log(JSON.stringify({
  status: "ok",
  schema_name: payload.schema_name,
  article_count: Object.keys(payload.articles).length,
  matched_article_count: payload.metrics?.matched_article_count ?? null,
  output: outputPath,
}));
