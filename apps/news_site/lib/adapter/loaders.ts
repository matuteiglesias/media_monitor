import fs from "node:fs";
import path from "node:path";
import { PUBLIC_DATA } from "./paths";

export function fileExists(pathname: string) {
  return fs.existsSync(pathname);
}

export function readJson(pathname: string) {
  return JSON.parse(fs.readFileSync(pathname, "utf-8"));
}

export function readJsonl(pathname: string) {
  return fs
    .readFileSync(pathname, "utf-8")
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

export function loadRecentRefs() {
  const pathname = path.join(PUBLIC_DATA, "news_recent_refs_latest.jsonl");
  if (!fileExists(pathname)) return [];
  return readJsonl(pathname);
}

export function loadRecentGroups() {
  const pathname = path.join(PUBLIC_DATA, "news_recent_groups_latest.jsonl");
  if (!fileExists(pathname)) return [];
  return readJsonl(pathname);
}

export function loadEditorialLatest() {
  const pathname = path.join(PUBLIC_DATA, "editorial_latest.json");
  if (!fileExists(pathname)) {
    return {
      status: "missing_public_snapshot",
      message: "Missing apps/news_site/public/data/editorial_latest.json",
      generated_at: null,
      digest_at: null,
      source: pathname,
    };
  }

  return readJson(pathname);
}
