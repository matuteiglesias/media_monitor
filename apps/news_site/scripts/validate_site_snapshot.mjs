import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const APP_ROOT = path.resolve(SCRIPT_DIR, "..");
const REPO_ROOT = path.resolve(APP_ROOT, "../..");

function fail(message) {
  console.error(`validate_site_snapshot: ERROR: ${message}`);
  process.exit(1);
}

function readJson(filePath, label) {
  if (!fs.existsSync(filePath)) fail(`${label} does not exist: ${filePath}`);
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    fail(`${label} is not valid JSON: ${error.message}`);
  }
}

function requireObject(value, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    fail(`${label} must be an object`);
  }
  return value;
}

function requireArray(value, label) {
  if (!Array.isArray(value)) fail(`${label} must be an array`);
  return value;
}

function requireString(value, label) {
  if (typeof value !== "string" || !value.trim()) {
    fail(`${label} must be a non-empty string`);
  }
  return value.trim();
}

function requireInteger(value, label) {
  if (!Number.isInteger(value) || value < 0) {
    fail(`${label} must be a non-negative integer`);
  }
  return value;
}

function parseDigestAt(value) {
  if (!/^\d{8}T\d{2}$/.test(value)) fail(`digest_at must match YYYYMMDDTHH: ${value}`);
  const year = Number(value.slice(0, 4));
  const month = Number(value.slice(4, 6));
  const day = Number(value.slice(6, 8));
  const hour = Number(value.slice(9, 11));
  const parsed = new Date(Date.UTC(year, month - 1, day, hour));
  if (
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() !== month - 1 ||
    parsed.getUTCDate() !== day ||
    parsed.getUTCHours() !== hour
  ) {
    fail(`digest_at is not a valid UTC hour: ${value}`);
  }
  return parsed;
}

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

function calculateSnapshotId(snapshot) {
  const canonicalPayload = structuredClone(snapshot);
  delete canonicalPayload.snapshot_id;
  delete canonicalPayload.generated_at;
  return crypto
    .createHash("sha256")
    .update(JSON.stringify(stableValue(canonicalPayload)), "utf8")
    .digest("hex");
}

function validateUrl(value, label) {
  const text = requireString(value, label);
  try {
    const parsed = new URL(text);
    if (!["http:", "https:"].includes(parsed.protocol)) {
      fail(`${label} must use http or https`);
    }
  } catch {
    fail(`${label} is not a valid URL`);
  }
}

function validateSignal(item, label) {
  requireObject(item, label);
  requireString(item.index_id, `${label}.index_id`);
  requireString(item.title, `${label}.title`);
  requireString(item.topic, `${label}.topic`);
  requireString(item.published_at, `${label}.published_at`);
  requireString(item.source, `${label}.source`);
  validateUrl(item.link, `${label}.link`);
  if (Number.isNaN(Date.parse(item.published_at))) {
    fail(`${label}.published_at is not a valid timestamp`);
  }
}

function validatePublishedArticle(article, label, expectedSlug) {
  requireObject(article, label);
  if (article.schema_name !== "published_article.v1") {
    fail(`${label}.schema_name must be published_article.v1`);
  }
  if (article.status !== "published") fail(`${label}.status must be published`);
  const slug = requireString(article.slug, `${label}.slug`);
  if (expectedSlug && slug !== expectedSlug) fail(`${label}.slug does not match articles key`);
  for (const key of [
    "article_id",
    "draft_id",
    "digest_at",
    "story_group_id",
    "title",
    "summary",
    "body_md",
    "topic",
    "review_status",
    "published_at",
    "updated_at",
  ]) {
    requireString(article[key], `${label}.${key}`);
  }
  if (Number.isNaN(Date.parse(article.published_at))) fail(`${label}.published_at is invalid`);
  if (Number.isNaN(Date.parse(article.updated_at))) fail(`${label}.updated_at is invalid`);
  const sourceLinks = requireArray(article.source_links, `${label}.source_links`);
  if (!sourceLinks.length) fail(`${label}.source_links must not be empty`);
  sourceLinks.forEach((url, index) => validateUrl(url, `${label}.source_links[${index}]`));
  requireArray(article.citations, `${label}.citations`).forEach((citation, index) => {
    requireObject(citation, `${label}.citations[${index}]`);
    for (const key of ["citation_id", "claim_text", "source_ref_id"]) {
      requireString(citation[key], `${label}.citations[${index}].${key}`);
    }
    validateUrl(citation.url, `${label}.citations[${index}].url`);
  });
}

function publicationRef(article) {
  return Object.fromEntries(
    ["article_id", "slug", "title", "summary", "topic", "published_at", "updated_at"].map(
      (key) => [key, article[key]],
    ),
  );
}

const siteId = process.env.SITE_ID || "argentina-general";
const requestedDigest = process.env.DIGEST_AT;
if (!requestedDigest) fail("DIGEST_AT is required");

const snapshotPath = path.join(APP_ROOT, "public", "data", "site_snapshot.json");
const configPath = path.join(REPO_ROOT, "sites", `${siteId}.json`);
const snapshot = requireObject(readJson(snapshotPath, "site snapshot"), "site snapshot");
const config = requireObject(readJson(configPath, "site configuration"), "site configuration");
const isV2 = snapshot.schema_name === "site_snapshot.v2";
if (!isV2 && snapshot.schema_name !== "site_snapshot.v1") {
  fail(`unexpected schema_name: ${snapshot.schema_name}`);
}
if (snapshot.status !== "ok") fail(`snapshot status must be ok, got: ${snapshot.status}`);

const snapshotSite = requireObject(snapshot.site, "site");
const snapshotSiteId = requireString(snapshotSite.site_id, "site.site_id");
const configSiteId = requireString(config.site_id, "config.site_id");
if (snapshotSiteId !== siteId) fail(`snapshot site_id ${snapshotSiteId} does not match SITE_ID ${siteId}`);
if (configSiteId !== siteId) fail(`configuration site_id ${configSiteId} does not match SITE_ID ${siteId}`);

const digestAt = requireString(snapshot.digest_at, "digest_at");
if (digestAt !== requestedDigest) {
  fail(`snapshot digest_at ${digestAt} does not match DIGEST_AT ${requestedDigest}`);
}
const digestDate = parseDigestAt(digestAt);
const selection = requireObject(config.selection, "config.selection");
const presentation = requireObject(config.presentation, "config.presentation");
const minimumItems = requireInteger(selection.minimum_items, "config.selection.minimum_items");
const maxItems = requireInteger(selection.max_items, "config.selection.max_items");
const latestCount = requireInteger(presentation.latest_count, "config.presentation.latest_count");
const maxAgeHours = Number(selection.max_age_hours);
if (!Number.isFinite(maxAgeHours) || maxAgeHours <= 0) {
  fail("config.selection.max_age_hours must be positive");
}

const nowText = process.env.SITE_SNAPSHOT_NOW;
const now = nowText ? new Date(nowText) : new Date();
if (Number.isNaN(now.getTime())) fail(`SITE_SNAPSHOT_NOW is not a valid timestamp: ${nowText}`);
const ageHours = (now.getTime() - digestDate.getTime()) / 3_600_000;
if (ageHours < -1) fail(`snapshot digest is unexpectedly in the future by ${-ageHours} hours`);
if (ageHours > maxAgeHours) {
  fail(`snapshot is stale: age=${ageHours.toFixed(2)}h max=${maxAgeHours}h digest=${digestAt}`);
}

const signalProjection = isV2 ? requireObject(snapshot.signals, "signals") : snapshot;
const latest = requireArray(signalProjection.latest, "signals.latest");
const sections = requireArray(signalProjection.sections, "signals.sections");
const metrics = requireObject(snapshot.metrics, "metrics");
const itemCount = requireInteger(metrics.item_count, "metrics.item_count");
const sectionCount = requireInteger(metrics.section_count, "metrics.section_count");
if (latest.length !== Math.min(itemCount, latestCount)) {
  fail(`signals.latest length ${latest.length} does not match expected ${Math.min(itemCount, latestCount)}`);
}
if (sections.length !== sectionCount) fail(`signals.sections length ${sections.length} does not match section_count ${sectionCount}`);
if (itemCount < minimumItems) fail(`item_count ${itemCount} is below minimum_items ${minimumItems}`);
if (itemCount > maxItems) fail(`item_count ${itemCount} exceeds max_items ${maxItems}`);
latest.forEach((item, index) => validateSignal(item, `signals.latest[${index}]`));
validateSignal(signalProjection.hero, "signals.hero");
if (signalProjection.hero.index_id !== latest[0].index_id) fail("signals.hero must be the first signals.latest item");
sections.forEach((section, index) => {
  requireObject(section, `signals.sections[${index}]`);
  requireString(section.topic, `signals.sections[${index}].topic`);
  requireInteger(section.article_count, `signals.sections[${index}].article_count`);
  requireArray(section.top_titles, `signals.sections[${index}].top_titles`);
});

let publishedArticleCount = 0;
if (isV2) {
  const publication = requireObject(snapshot.publication, "publication");
  const publicationLatest = requireArray(publication.latest, "publication.latest");
  const articles = requireObject(snapshot.articles, "articles");
  publishedArticleCount = requireInteger(
    metrics.published_article_count,
    "metrics.published_article_count",
  );
  const articleSlugs = Object.keys(articles);
  if (articleSlugs.length !== publishedArticleCount) {
    fail(`articles count ${articleSlugs.length} does not match published_article_count ${publishedArticleCount}`);
  }
  articleSlugs.forEach((slug) => validatePublishedArticle(articles[slug], `articles.${slug}`, slug));
  if (publicationLatest.length !== Math.min(publishedArticleCount, latestCount)) {
    fail("publication.latest length does not match publication count/latest_count");
  }
  if (publishedArticleCount === 0) {
    if (publication.featured !== null || publicationLatest.length) {
      fail("empty publication must have featured=null and latest=[]");
    }
  } else {
    if (JSON.stringify(stableValue(publication.featured)) !== JSON.stringify(stableValue(publicationLatest[0]))) {
      fail("publication.featured must equal first publication.latest entry");
    }
    publicationLatest.forEach((ref, index) => {
      const slug = requireString(ref.slug, `publication.latest[${index}].slug`);
      const article = articles[slug];
      if (!article) fail(`publication.latest[${index}] references missing article ${slug}`);
      const expected = publicationRef(article);
      if (JSON.stringify(stableValue(ref)) !== JSON.stringify(stableValue(expected))) {
        fail(`publication.latest[${index}] does not match articles.${slug}`);
      }
    });
  }
}

const snapshotId = requireString(snapshot.snapshot_id, "snapshot_id");
if (!/^[a-f0-9]{64}$/.test(snapshotId)) fail("snapshot_id must be a lowercase SHA256 digest");
const calculatedId = calculateSnapshotId(snapshot);
if (snapshotId !== calculatedId) {
  fail(`snapshot_id mismatch: recorded=${snapshotId} calculated=${calculatedId}`);
}

console.log(
  JSON.stringify(
    {
      status: "ok",
      schema_name: snapshot.schema_name,
      site_id: snapshotSiteId,
      digest_at: digestAt,
      snapshot_id: snapshotId,
      item_count: itemCount,
      section_count: sectionCount,
      published_article_count: publishedArticleCount,
      age_hours: Number(ageHours.toFixed(3)),
    },
    null,
    2,
  ),
);
