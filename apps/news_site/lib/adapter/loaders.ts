import fs from "node:fs";
import path from "node:path";
import { STORAGE_INDEXES } from "./paths";

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
  const pathname = path.join(STORAGE_INDEXES, "news_recent_refs_latest.jsonl");
  if (!fileExists(pathname)) return [];
  return readJsonl(pathname);
}

export function loadRecentGroups() {
  const pathname = path.join(STORAGE_INDEXES, "news_recent_groups_latest.jsonl");
  if (!fileExists(pathname)) return [];
  return readJsonl(pathname);
}

export function loadEditorialLatest() {
  const pathname = path.join(STORAGE_INDEXES, "editorial_latest.json");
  if (!fileExists(pathname)) return null;
  return readJson(pathname);
}
