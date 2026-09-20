import path from "node:path";

const FACETS = [
  "character_tags",
  "institution_tags",
  "topic_tags",
  "scene_tags",
  "motif_tags",
];

export function normalizeVisualText(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function containsKeyword(haystack, keyword) {
  const normalized = normalizeVisualText(keyword);
  if (!normalized) return false;
  return ` ${haystack} `.includes(` ${normalized} `);
}

export function deriveArticleVisualTags(article, rulesPayload) {
  if (rulesPayload?.schema_name !== "southland_visual_tag_rules.v1") {
    throw new Error("expected southland_visual_tag_rules.v1");
  }
  const source = [
    article?.title,
    article?.summary,
    article?.body_md,
    article?.topic,
  ]
    .map(normalizeVisualText)
    .filter(Boolean)
    .join(" ");

  const matched = [];
  for (const rule of rulesPayload.rules ?? []) {
    if (
      typeof rule?.tag !== "string" ||
      !Array.isArray(rule?.keywords) ||
      !rule.keywords.length
    ) {
      throw new Error("invalid visual tag rule");
    }
    if (rule.keywords.some((keyword) => containsKeyword(source, keyword))) {
      matched.push(rule.tag);
    }
  }
  return [...new Set(matched)].sort();
}

export function flattenAssetTags(asset) {
  return [...new Set(FACETS.flatMap((field) => asset?.[field] ?? []))].sort();
}

function characterTags(tags) {
  return tags.filter((tag) => tag.startsWith("character:"));
}

function intersection(left, right) {
  const rhs = new Set(right);
  return left.filter((value) => rhs.has(value));
}

export function resolvePublicAssetPath(appRoot, publicPath) {
  if (typeof publicPath !== "string" || !publicPath.startsWith("/")) return null;
  const publicRoot = path.resolve(appRoot, "public");
  const resolved = path.resolve(publicRoot, publicPath.slice(1));
  if (!resolved.startsWith(`${publicRoot}${path.sep}`)) return null;
  return resolved;
}

export function rankSouthlandVisualAssets({
  articleTags,
  assets,
  maxMatches = 2,
  fileExists = () => true,
}) {
  const articleCharacters = characterTags(articleTags);
  const ranked = [];

  for (const asset of assets ?? []) {
    if (asset?.status !== "approved") continue;
    if (asset?.identity_status === "pending_lineage") continue;
    if (!fileExists(asset)) continue;

    const tags = flattenAssetTags(asset);
    const matchedTags = intersection(tags, articleTags);
    if (!matchedTags.length) continue;

    const assetCharacters = characterTags(tags);
    const characterMatches = intersection(assetCharacters, articleCharacters);

    // If both sides name people, a generic topic overlap cannot override
    // a person mismatch.
    if (
      articleCharacters.length &&
      assetCharacters.length &&
      !characterMatches.length
    ) {
      continue;
    }

    ranked.push({
      asset_id: asset.asset_id,
      public_path: asset.public_path,
      alt: asset.alt,
      created_at: asset.created_at,
      matched_tags: matchedTags,
      character_match_count: characterMatches.length,
      match_count: matchedTags.length,
    });
  }

  ranked.sort((left, right) => {
    if (left.character_match_count !== right.character_match_count) {
      return right.character_match_count - left.character_match_count;
    }
    if (left.match_count !== right.match_count) {
      return right.match_count - left.match_count;
    }
    if (left.created_at !== right.created_at) {
      return String(right.created_at).localeCompare(String(left.created_at));
    }
    return String(left.asset_id).localeCompare(String(right.asset_id));
  });

  return ranked.slice(0, Math.max(0, maxMatches));
}
