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
  if (!fs.existsSync(filePath)) {
    fail(`${label} does not exist: ${filePath}`);
  }

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
  if (!Array.isArray(value)) {
    fail(`${label} must be an array`);
  }
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
  if (!/^\d{8}T\d{2}$/.test(value)) {
    fail(`digest_at must match YYYYMMDDTHH: ${value}`);
  }

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
  if (Array.isArray(value)) {
    return value.map(stableValue);
  }

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

  const canonicalJson = JSON.stringify(stableValue(canonicalPayload));

  return crypto
    .createHash("sha256")
    .update(canonicalJson, "utf8")
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

function validateItem(item, label) {
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

const siteId = process.env.SITE_ID || "argentina-general";
const requestedDigest = process.env.DIGEST_AT;

if (!requestedDigest) {
  fail("DIGEST_AT is required");
}

const snapshotPath = path.join(APP_ROOT, "public", "data", "site_snapshot.json");
const configPath = path.join(REPO_ROOT, "sites", `${siteId}.json`);

const snapshot = requireObject(
  readJson(snapshotPath, "site snapshot"),
  "site snapshot",
);

const config = requireObject(
  readJson(configPath, "site configuration"),
  "site configuration",
);

if (snapshot.schema_name !== "site_snapshot.v1") {
  fail(`unexpected schema_name: ${snapshot.schema_name}`);
}

if (snapshot.status !== "ok") {
  fail(`snapshot status must be ok, got: ${snapshot.status}`);
}

const snapshotSite = requireObject(snapshot.site, "site");
const snapshotSiteId = requireString(snapshotSite.site_id, "site.site_id");
const configSiteId = requireString(config.site_id, "config.site_id");

if (snapshotSiteId !== siteId) {
  fail(`snapshot site_id ${snapshotSiteId} does not match SITE_ID ${siteId}`);
}

if (configSiteId !== siteId) {
  fail(`configuration site_id ${configSiteId} does not match SITE_ID ${siteId}`);
}

const digestAt = requireString(snapshot.digest_at, "digest_at");

if (digestAt !== requestedDigest) {
  fail(
    `snapshot digest_at ${digestAt} does not match DIGEST_AT ${requestedDigest}`,
  );
}

const digestDate = parseDigestAt(digestAt);

const selection = requireObject(config.selection, "config.selection");
const minimumItems = requireInteger(
  selection.minimum_items,
  "config.selection.minimum_items",
);
const maxItems = requireInteger(
  selection.max_items,
  "config.selection.max_items",
);
const maxAgeHours = Number(selection.max_age_hours);

if (!Number.isFinite(maxAgeHours) || maxAgeHours <= 0) {
  fail("config.selection.max_age_hours must be positive");
}

const nowText = process.env.SITE_SNAPSHOT_NOW;
const now = nowText ? new Date(nowText) : new Date();

if (Number.isNaN(now.getTime())) {
  fail(`SITE_SNAPSHOT_NOW is not a valid timestamp: ${nowText}`);
}

const ageHours = (now.getTime() - digestDate.getTime()) / 3_600_000;

if (ageHours < -1) {
  fail(`snapshot digest is unexpectedly in the future by ${-ageHours} hours`);
}

if (ageHours > maxAgeHours) {
  fail(
    `snapshot is stale: age=${ageHours.toFixed(2)}h max=${maxAgeHours}h digest=${digestAt}`,
  );
}

const latest = requireArray(snapshot.latest, "latest");
const sections = requireArray(snapshot.sections, "sections");
const metrics = requireObject(snapshot.metrics, "metrics");

const itemCount = requireInteger(metrics.item_count, "metrics.item_count");
const sectionCount = requireInteger(
  metrics.section_count,
  "metrics.section_count",
);

if (latest.length !== itemCount) {
  fail(
    `latest length ${latest.length} does not match metrics.item_count ${itemCount}`,
  );
}

if (sections.length !== sectionCount) {
  fail(
    `sections length ${sections.length} does not match metrics.section_count ${sectionCount}`,
  );
}

if (itemCount < minimumItems) {
  fail(`item_count ${itemCount} is below minimum_items ${minimumItems}`);
}

if (itemCount > maxItems) {
  fail(`item_count ${itemCount} exceeds max_items ${maxItems}`);
}

latest.forEach((item, index) => validateItem(item, `latest[${index}]`));

if (itemCount > 0) {
  validateItem(snapshot.hero, "hero");

  if (snapshot.hero.index_id !== latest[0].index_id) {
    fail("hero must be the first latest item");
  }
}

sections.forEach((section, index) => {
  requireObject(section, `sections[${index}]`);
  requireString(section.topic, `sections[${index}].topic`);
  requireInteger(
    section.article_count,
    `sections[${index}].article_count`,
  );
  requireArray(section.top_titles, `sections[${index}].top_titles`);
});

const snapshotId = requireString(snapshot.snapshot_id, "snapshot_id");

if (!/^[a-f0-9]{64}$/.test(snapshotId)) {
  fail("snapshot_id must be a lowercase SHA256 digest");
}

const calculatedId = calculateSnapshotId(snapshot);

if (snapshotId !== calculatedId) {
  fail(
    `snapshot_id mismatch: recorded=${snapshotId} calculated=${calculatedId}`,
  );
}

console.log(
  JSON.stringify(
    {
      status: "ok",
      site_id: snapshotSiteId,
      digest_at: digestAt,
      snapshot_id: snapshotId,
      item_count: itemCount,
      section_count: sectionCount,
      age_hours: Number(ageHours.toFixed(3)),
    },
    null,
    2,
  ),
);
