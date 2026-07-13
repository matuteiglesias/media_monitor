import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function readJsonlChecked(filePath) {
  const raw = fs.readFileSync(filePath, "utf-8");
  if (!raw.trim()) {
    throw new Error(`Required snapshot is empty: ${filePath}`);
  }

  const rows = raw
    .split("\n")
    .filter(Boolean)
    .map((line, idx) => {
      try {
        return JSON.parse(line);
      } catch (error) {
        throw new Error(`Invalid JSONL at ${filePath}:${idx + 1}: ${String(error)}`);
      }
    });

  if (!rows.length) {
    throw new Error(`Required snapshot has no parseable rows: ${filePath}`);
  }

  return rows;
}

function readJsonChecked(filePath) {
  const raw = fs.readFileSync(filePath, "utf-8");
  if (!raw.trim()) {
    throw new Error(`JSON file is empty: ${filePath}`);
  }
  return JSON.parse(raw);
}

function copyFileWithValidation(src, dst, kind) {
  const sourcePayload = kind === "jsonl" ? readJsonlChecked(src) : readJsonChecked(src);

  const tmp = `${dst}.tmp`;
  fs.copyFileSync(src, tmp);

  const copiedPayload = kind === "jsonl" ? readJsonlChecked(tmp) : readJsonChecked(tmp);
  assertCopiedFromStorage(src, tmp, kind, sourcePayload, copiedPayload);

  fs.renameSync(tmp, dst);
}

function digestSetFromJsonl(rows) {
  return [...new Set(rows.map((row) => row?.digest_at).filter((value) => typeof value === "string" && value.trim()))].sort();
}

function assertCopiedFromStorage(src, dst, kind, sourcePayload, copiedPayload) {
  const sourceRaw = fs.readFileSync(src, "utf-8");
  const copiedRaw = fs.readFileSync(dst, "utf-8");
  if (sourceRaw !== copiedRaw) {
    throw new Error(`Copied public snapshot differs from storage source: ${dst} != ${src}`);
  }

  if (kind === "jsonl") {
    const sourceDigests = digestSetFromJsonl(sourcePayload);
    const copiedDigests = digestSetFromJsonl(copiedPayload);
    if (JSON.stringify(sourceDigests) !== JSON.stringify(copiedDigests)) {
      throw new Error(`Copied public snapshot digest_at mismatch: ${dst} != ${src}`);
    }
    return;
  }

  const sourceDigest = sourcePayload?.digest_at ?? null;
  const copiedDigest = copiedPayload?.digest_at ?? null;
  if (sourceDigest !== copiedDigest) {
    throw new Error(`Copied public JSON digest_at mismatch: ${dst} != ${src}`);
  }
}

function defaultEditorialFallback() {
  return {
    status: "missing_editorial_index",
    message: "storage/indexes/editorial_latest.json was missing during refresh_public_data",
    generated_at: null,
    digest_at: null,
    items: [],
  };
}

export function refreshPublicData(options = {}) {
  const repoRoot = options.repoRoot ?? path.resolve(__dirname, "../../..");
  const sourceDir = path.join(repoRoot, "storage", "indexes");
  const targetDir = path.join(repoRoot, "apps", "news_site", "public", "data");

  const required = [
    "news_recent_refs_latest.jsonl",
    "news_recent_groups_latest.jsonl",
  ];

  ensureDir(targetDir);

  for (const filename of required) {
    const src = path.join(sourceDir, filename);
    const dst = path.join(targetDir, filename);

    if (!fs.existsSync(src)) {
      throw new Error(`Missing required snapshot: ${src}`);
    }

    copyFileWithValidation(src, dst, "jsonl");
  }

  const editorialSrc = path.join(sourceDir, "editorial_latest.json");
  const editorialDst = path.join(targetDir, "editorial_latest.json");

  if (fs.existsSync(editorialSrc)) {
    copyFileWithValidation(editorialSrc, editorialDst, "json");
  } else if (process.env.ALLOW_EDITORIAL_FALLBACK === "1") {
    const fallback = {
      ...defaultEditorialFallback(),
      source: "editorial_fallback",
      generated_at: new Date().toISOString(),
    };
    fs.writeFileSync(editorialDst, `${JSON.stringify(fallback, null, 2)}\n`, "utf-8");
    readJsonChecked(editorialDst);
  } else {
    throw new Error(`Missing required editorial snapshot: ${editorialSrc}. Set ALLOW_EDITORIAL_FALLBACK=1 only for local emergency previews.`);
  }

  return {
    repoRoot,
    sourceDir,
    targetDir,
    copied: required,
    editorial: fs.existsSync(editorialSrc) ? "copied" : "fallback_written",
  };
}

function isMain() {
  return process.argv[1] && path.resolve(process.argv[1]) === __filename;
}

if (isMain()) {
  try {
    const result = refreshPublicData();
    console.log("refresh_public_data: ok");
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    console.error("refresh_public_data: failed");
    console.error(String(error));
    process.exit(1);
  }
}
