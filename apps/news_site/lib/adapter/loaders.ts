import fs from "node:fs";
import path from "node:path";

export const PUBLIC_DATA = path.join(process.cwd(), "public", "data");
export type SiteSnapshot = any;

export function loadSiteSnapshot(): SiteSnapshot {
  const pathname = path.join(PUBLIC_DATA, "site_snapshot.json");
  if (!fs.existsSync(pathname)) throw new Error("Missing required site_snapshot.json");
  return JSON.parse(fs.readFileSync(pathname, "utf-8"));
}
