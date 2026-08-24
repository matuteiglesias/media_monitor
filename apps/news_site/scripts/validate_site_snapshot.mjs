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
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(`${label} must be an object`);
  return value;
}

function requireArray(value, label) {
  if (!Array.isArray(value)) fail(`${label} must be an array`);
  return value;
}

function requireString(value, label) {
  if (typeof value !== "string" || !value.trim()) fail(`${label} must be a non-empty string`);
  return value.trim();
}

function requireInteger(value, label) {
  if (!Number.isInteger(value) || value < 0) fail(`${label} must be a non-negative integer`);
  return value;
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableValue(value[key])]));
  }
  return value;
}

function calculateSnapshotId(snapshot) {
  const canonicalPayload = structuredClone(snapshot);
  delete canonicalPayload.snapshot_id;
  delete canonicalPayload.generated_at;
  return crypto.createHash("sha256").update(JSON.stringify(stableValue(canonicalPayload)), "utf8").digest("hex");
}

function validateUrl(value, label) {
  const text = requireString(value, label);
  try {
    const parsed = new URL(text);
    if (!["http:", "https:"].includes(parsed.protocol)) fail(`${label} must use http or https`);
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
  if (Number.isNaN(Date.parse(item.published_at))) fail(`${label}.published_at is not a valid timestamp`);
}

function validateCurated(item, label, expectedRank) {
  validateSignal(item, label);
  if (requireInteger(item.rank, `${label}.rank`) !== expectedRank) fail(`${label}.rank must be contiguous and ordered`);
  if (!Number.isInteger(item.score)) fail(`${label}.score must be an integer`);
  const components = requireObject(item.score_components, `${label}.score_components`);
  for (const key of ["topic_priority", "freshness", "first_source_bonus", "first_topic_bonus", "repeat_source_penalty", "repeat_topic_penalty"]) {
    if (!Number.isInteger(components[key])) fail(`${label}.score_components.${key} must be an integer`);
  }
  const reasons = requireArray(item.reason_codes, `${label}.reason_codes`);
  if (!reasons.length) fail(`${label}.reason_codes must not be empty`);
  reasons.forEach((reason, index) => requireString(reason, `${label}.reason_codes[${index}]`));
}

function validatePublishedArticle(article, label, expectedSlug) {
  requireObject(article, label);
  if (article.schema_name !== "published_article.v1") fail(`${label}.schema_name must be published_article.v1`);
  if (article.status !== "published") fail(`${label}.status must be published`);
  const slug = requireString(article.slug, `${label}.slug`);
  if (expectedSlug && slug !== expectedSlug) fail(`${label}.slug does not match articles key`);
  for (const key of ["article_id", "draft_id", "digest_at", "story_group_id", "title", "summary", "body_md", "topic", "review_status", "published_at", "updated_at"]) {
    requireString(article[key], `${label}.${key}`);
  }
  if (Number.isNaN(Date.parse(article.published_at))) fail(`${label}.published_at is invalid`);
  if (Number.isNaN(Date.parse(article.updated_at))) fail(`${label}.updated_at is invalid`);
  const sourceLinks = requireArray(article.source_links, `${label}.source_links`);
  if (!sourceLinks.length) fail(`${label}.source_links must not be empty`);
  sourceLinks.forEach((url, index) => validateUrl(url, `${label}.source_links[${index}]`));
  requireArray(article.citations, `${label}.citations`).forEach((citation, index) => {
    requireObject(citation, `${label}.citations[${index}]`);
    for (const key of ["citation_id", "claim_text", "source_ref_id"]) requireString(citation[key], `${label}.citations[${index}].${key}`);
    validateUrl(citation.url, `${label}.citations[${index}].url`);
  });
}

function publicationRef(article) {
  return Object.fromEntries(["article_id", "slug", "title", "summary", "topic", "published_at", "updated_at"].map((key) => [key, article[key]]));
}

const siteId = process.env.SITE_ID || "argentina-general";
const requestedDigest = process.env.DIGEST_AT;
if (!requestedDigest) fail("DIGEST_AT is required");

const snapshotPath = path.join(APP_ROOT, "public", "data", "site_snapshot.json");
const configPath = path.join(REPO_ROOT, "sites", `${siteId}.json`);
const snapshot = requireObject(readJson(snapshotPath, "site snapshot"), "site snapshot");
const config = requireObject(readJson(configPath, "site configuration"), "site configuration");
const schema = snapshot.schema_name;
const isV3 = schema === "site_snapshot.v3";
const isV2 = schema === "site_snapshot.v2";
if (!isV3 && !isV2 && schema !== "site_snapshot.v1") fail(`unexpected schema_name: ${schema}`);
if (snapshot.status !== "ok") fail(`snapshot status must be ok, got: ${snapshot.status}`);

const snapshotSite = requireObject(snapshot.site, "site");
if (requireString(snapshotSite.site_id, "site.site_id") !== siteId) fail("snapshot site_id does not match SITE_ID");
if (requireString(config.site_id, "config.site_id") !== siteId) fail("configuration site_id does not match SITE_ID");
if (requireString(snapshot.digest_at, "digest_at") !== requestedDigest) fail("snapshot digest_at does not match DIGEST_AT");

const selection = requireObject(config.selection, "config.selection");
const presentation = requireObject(config.presentation, "config.presentation");
const minimumItems = requireInteger(selection.minimum_items, "config.selection.minimum_items");
const maxItems = requireInteger(selection.max_items, "config.selection.max_items");
const latestCount = requireInteger(presentation.latest_count, "config.presentation.latest_count");
const signalProjection = isV2 || isV3 ? requireObject(snapshot.signals, "signals") : snapshot;
const latest = requireArray(signalProjection.latest, "signals.latest");
const sections = requireArray(signalProjection.sections, "signals.sections");
const metrics = requireObject(snapshot.metrics, "metrics");
const itemCount = requireInteger(metrics.item_count, "metrics.item_count");
const sectionCount = requireInteger(metrics.section_count, "metrics.section_count");
if (latest.length !== Math.min(itemCount, latestCount)) fail("signals.latest length does not match item_count/latest_count");
if (sections.length !== sectionCount) fail("signals.sections length does not match section_count");
if (itemCount < minimumItems || itemCount > maxItems) fail("item_count outside configured selection bounds");
latest.forEach((item, index) => validateSignal(item, `signals.latest[${index}]`));
validateSignal(signalProjection.hero, "signals.hero");
if (signalProjection.hero.index_id !== latest[0].index_id) fail("signals.hero must be first signals.latest item");
sections.forEach((section, index) => {
  requireObject(section, `signals.sections[${index}]`);
  requireString(section.topic, `signals.sections[${index}].topic`);
  requireInteger(section.article_count, `signals.sections[${index}].article_count`);
  requireArray(section.top_titles, `signals.sections[${index}].top_titles`);
});

let curatedSignalCount = 0;
if (isV3) {
  const curated = requireArray(signalProjection.curated, "signals.curated");
  curatedSignalCount = requireInteger(metrics.curated_signal_count, "metrics.curated_signal_count");
  if (!curatedSignalCount || curated.length !== curatedSignalCount) fail("signals.curated length does not match curated_signal_count");
  curated.forEach((item, index) => validateCurated(item, `signals.curated[${index}]`, index + 1));
}

let publishedArticleCount = 0;
if (isV2 || isV3) {
  const publication = requireObject(snapshot.publication, "publication");
  const publicationLatest = requireArray(publication.latest, "publication.latest");
  const articles = requireObject(snapshot.articles, "articles");
  publishedArticleCount = requireInteger(metrics.published_article_count, "metrics.published_article_count");
  const articleSlugs = Object.keys(articles);
  if (articleSlugs.length !== publishedArticleCount) fail("articles count does not match published_article_count");
  articleSlugs.forEach((slug) => validatePublishedArticle(articles[slug], `articles.${slug}`, slug));
  if (publicationLatest.length !== Math.min(publishedArticleCount, latestCount)) fail("publication.latest length mismatch");
  if (publishedArticleCount === 0) {
    if (publication.featured !== null || publicationLatest.length) fail("empty publication must have featured=null and latest=[]");
  } else {
    if (JSON.stringify(stableValue(publication.featured)) !== JSON.stringify(stableValue(publicationLatest[0]))) fail("publication.featured must equal first publication.latest entry");
    publicationLatest.forEach((ref, index) => {
      const slug = requireString(ref.slug, `publication.latest[${index}].slug`);
      const article = articles[slug];
      if (!article) fail(`publication.latest references missing article ${slug}`);
      if (JSON.stringify(stableValue(ref)) !== JSON.stringify(stableValue(publicationRef(article)))) fail(`publication.latest[${index}] does not match article`);
    });
  }
}

const snapshotId = requireString(snapshot.snapshot_id, "snapshot_id");
if (!/^[a-f0-9]{64}$/.test(snapshotId)) fail("snapshot_id must be a lowercase SHA256 digest");
if (snapshotId !== calculateSnapshotId(snapshot)) fail("snapshot_id mismatch");

console.log(JSON.stringify({
  status: "ok",
  schema_name: schema,
  site_id: siteId,
  digest_at: requestedDigest,
  snapshot_id: snapshotId,
  item_count: itemCount,
  section_count: sectionCount,
  published_article_count: publishedArticleCount,
  curated_signal_count: curatedSignalCount,
}, null, 2));
