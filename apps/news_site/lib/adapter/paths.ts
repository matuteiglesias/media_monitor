import path from "node:path";

export const APP_ROOT = process.cwd();
export const REPO_ROOT = path.resolve(APP_ROOT, "../..");
export const STORAGE_INDEXES = path.join(REPO_ROOT, "storage", "indexes");
