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
  fs.copyFileSync(src, dst);

  if (kind === "jsonl") {
    readJsonlChecked(dst);
  } else {
    readJsonChecked(dst);
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
  } else {
    fs.writeFileSync(editorialDst, `${JSON.stringify(defaultEditorialFallback(), null, 2)}\n`, "utf-8");
    readJsonChecked(editorialDst);
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
