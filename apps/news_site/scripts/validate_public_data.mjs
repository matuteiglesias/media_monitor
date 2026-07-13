import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const JSONL_REQUIRED_FIELDS = {
  "news_recent_refs_latest.jsonl": ["digest_at", "title", "topic", "published_at", "link"],
  "news_recent_groups_latest.jsonl": ["digest_at", "window_type", "topic", "group_number", "article_count", "top_titles"],
};

const PUBLISHED_ARTICLE_FIELDS = [
  "schema_name",
  "article_id",
  "draft_id",
  "digest_at",
  "story_group_id",
  "slug",
  "title",
  "summary",
  "body_md",
  "topic",
  "source_links",
  "citations",
  "status",
  "review_status",
  "published_at",
  "updated_at",
];

function readJsonl(filePath) {
  const raw = fs.readFileSync(filePath, "utf-8");
  if (!raw.trim()) throw new Error(`empty file: ${filePath}`);
  return raw.split("\n").filter(Boolean).map((line, idx) => {
    try {
      const row = JSON.parse(line);
      if (!row || typeof row !== "object" || Array.isArray(row)) {
        throw new Error("expected object row");
      }
      return row;
    } catch (error) {
      throw new Error(`${filePath}:${idx + 1}: invalid JSONL: ${String(error)}`);
    }
  });
}

function readJson(filePath) {
  const raw = fs.readFileSync(filePath, "utf-8");
  if (!raw.trim()) throw new Error(`empty file: ${filePath}`);
  const payload = JSON.parse(raw);
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error(`expected object root: ${filePath}`);
  }
  return payload;
}

function sha256(filePath) {
  return createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function requireFields(row, fields, filePath, idx) {
  for (const field of fields) {
    if (!(field in row)) throw new Error(`${filePath}:${idx}: missing required field ${field}`);
    if (typeof row[field] === "string" && !row[field].trim()) {
      throw new Error(`${filePath}:${idx}: blank required field ${field}`);
    }
  }
}

function assertFreshEnough(storagePath, publicPath) {
  const storageStat = fs.statSync(storagePath);
  const publicStat = fs.statSync(publicPath);
  if (publicStat.mtimeMs + 1000 < storageStat.mtimeMs) {
    throw new Error(`public snapshot older than storage source: ${publicPath} < ${storagePath}`);
  }
}

function digestSet(rows) {
  return [...new Set(rows.map((row) => row?.digest_at).filter((value) => typeof value === "string" && value.trim()))].sort();
}

function assertSameStorageProjection(storagePath, publicPath) {
  const storageHash = sha256(storagePath);
  const publicHash = sha256(publicPath);
  if (storageHash !== publicHash) {
    throw new Error(`public snapshot is not derived from storage snapshot: ${publicPath} sha256=${publicHash} storage=${storageHash}`);
  }
}

function assertExpectedDigest(filename, digests, expectedDigestAt) {
  if (!digests.length) {
    throw new Error(`${filename}: no digest_at values found`);
  }
  if (digests.length !== 1) {
    throw new Error(`${filename}: mixed digest_at values: ${digests.join(", ")}`);
  }
  if (expectedDigestAt && digests[0] !== expectedDigestAt) {
    throw new Error(`${filename}: digest_at ${digests[0]} does not match requested ${expectedDigestAt}`);
  }
}

export function validatePublicData(options = {}) {
  const repoRoot = options.repoRoot ?? path.resolve(__dirname, "../../..");
  const allowEditorialFallback = options.allowEditorialFallback ?? process.env.ALLOW_EDITORIAL_FALLBACK === "1";
  const expectedDigestAt = options.digestAt ?? process.env.DIGEST_AT ?? null;
  const storageDir = path.join(repoRoot, "storage", "indexes");
  const publicDir = path.join(repoRoot, "apps", "news_site", "public", "data");
  const manifest = {
    validated_at: new Date().toISOString(),
    storage_dir: storageDir,
    public_dir: publicDir,
    files: {},
  };

  for (const [filename, fields] of Object.entries(JSONL_REQUIRED_FIELDS)) {
    const storagePath = path.join(storageDir, filename);
    const publicPath = path.join(publicDir, filename);
    if (!fs.existsSync(storagePath)) throw new Error(`missing storage snapshot: ${storagePath}`);
    if (!fs.existsSync(publicPath)) throw new Error(`missing public snapshot: ${publicPath}`);
    const storageRows = readJsonl(storagePath);
    const publicRows = readJsonl(publicPath);
    if (storageRows.length === 0 || publicRows.length === 0) throw new Error(`no rows in ${filename}`);
    publicRows.forEach((row, idx) => requireFields(row, fields, publicPath, idx + 1));
    assertSameStorageProjection(storagePath, publicPath);
    const digests = digestSet(publicRows);
    assertExpectedDigest(filename, digests, expectedDigestAt);
    assertFreshEnough(storagePath, publicPath);
    manifest.files[filename] = {
      storage_rows: storageRows.length,
      public_rows: publicRows.length,
      storage_sha256: sha256(storagePath),
      public_sha256: sha256(publicPath),
      digest_at: digests[0] ?? null,
    };
  }

  const publishedStorage = path.join(storageDir, "published_articles_latest.jsonl");
  const publishedPublic = path.join(publicDir, "published_articles_latest.jsonl");
  if (fs.existsSync(publishedStorage) || fs.existsSync(publishedPublic)) {
    if (!fs.existsSync(publishedStorage)) throw new Error(`missing storage published articles snapshot: ${publishedStorage}`);
    if (!fs.existsSync(publishedPublic)) throw new Error(`missing public published articles snapshot: ${publishedPublic}`);
    const storageRaw = fs.readFileSync(publishedStorage, "utf-8");
    const publicRaw = fs.readFileSync(publishedPublic, "utf-8");
    const storageRows = storageRaw.trim() ? readJsonl(publishedStorage) : [];
    const publicRows = publicRaw.trim() ? readJsonl(publishedPublic) : [];
    publicRows.forEach((row, idx) => {
      requireFields(row, PUBLISHED_ARTICLE_FIELDS, publishedPublic, idx + 1);
      if (row.schema_name !== "published_article.v1") throw new Error(`${publishedPublic}:${idx + 1}: expected published_article.v1`);
      if (row.status !== "published") throw new Error(`${publishedPublic}:${idx + 1}: expected status=published`);
      if (!Array.isArray(row.source_links) || row.source_links.length === 0) throw new Error(`${publishedPublic}:${idx + 1}: source_links must be non-empty`);
      if (!Array.isArray(row.citations)) throw new Error(`${publishedPublic}:${idx + 1}: citations must be an array`);
      const articlePath = path.join(publicDir, "articles", `${row.slug}.json`);
      if (!fs.existsSync(articlePath)) throw new Error(`missing per-slug article JSON: ${articlePath}`);
      const article = readJson(articlePath);
      if (article.article_id !== row.article_id) throw new Error(`article JSON mismatch for slug ${row.slug}`);
    });
    assertSameStorageProjection(publishedStorage, publishedPublic);
    assertFreshEnough(publishedStorage, publishedPublic);
    manifest.files["published_articles_latest.jsonl"] = {
      storage_rows: storageRows.length,
      public_rows: publicRows.length,
      storage_sha256: sha256(publishedStorage),
      public_sha256: sha256(publishedPublic),
      published_article_count: publicRows.length,
    };
    manifest.published_article_count = publicRows.length;
  } else {
    manifest.published_article_count = 0;
  }

  const editorialStorage = path.join(storageDir, "editorial_latest.json");
  const editorialPublic = path.join(publicDir, "editorial_latest.json");
  if (!fs.existsSync(editorialPublic)) throw new Error(`missing public snapshot: ${editorialPublic}`);
  const editorial = readJson(editorialPublic);
  const isFallback = editorial.status === "missing_editorial_index" || editorial.source === "editorial_fallback";
  if (isFallback && !allowEditorialFallback) {
    throw new Error("editorial_latest.json is fallback; set ALLOW_EDITORIAL_FALLBACK=1 only for local emergency previews");
  }
  if (!fs.existsSync(editorialStorage) && !allowEditorialFallback) {
    throw new Error(`missing storage editorial snapshot: ${editorialStorage}`);
  }
  if (fs.existsSync(editorialStorage)) {
    const storageEditorial = readJson(editorialStorage);
    if ((storageEditorial.digest_at ?? null) !== (editorial.digest_at ?? null)) {
      throw new Error(`editorial digest_at mismatch between public and storage snapshots: ${editorialPublic} != ${editorialStorage}`);
    }
    if (expectedDigestAt && editorial.digest_at !== expectedDigestAt) {
      throw new Error(`editorial_latest.json: digest_at ${editorial.digest_at} does not match requested ${expectedDigestAt}`);
    }
    assertSameStorageProjection(editorialStorage, editorialPublic);
    assertFreshEnough(editorialStorage, editorialPublic);
    manifest.files["editorial_latest.json"] = {
      storage_sha256: sha256(editorialStorage),
      public_sha256: sha256(editorialPublic),
      digest_at: editorial.digest_at ?? null,
      status: editorial.status ?? null,
    };
  } else {
    manifest.files["editorial_latest.json"] = { fallback: true, status: editorial.status ?? null };
  }

  return manifest;
}

if (path.resolve(process.argv[1] ?? "") === __filename) {
  try {
    const manifest = validatePublicData();
    console.log("validate_public_data: ok");
    console.log(JSON.stringify(manifest, null, 2));
  } catch (error) {
    console.error("validate_public_data: failed");
    console.error(String(error));
    process.exit(1);
  }
}
