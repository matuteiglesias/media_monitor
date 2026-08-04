import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { resolveRequestedDigest } from "./site_snapshot_digest.mjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDir, "..");
const snapshotPath = path.join(appRoot, "public", "data", "site_snapshot.json");

try {
  process.env.DIGEST_AT = resolveRequestedDigest({
    snapshotPath,
    requestedDigest: process.env.DIGEST_AT,
  });
  await import("./validate_site_snapshot.mjs");
} catch (error) {
  console.error(`validate_site_snapshot_for_build: ERROR: ${error.message}`);
  process.exit(1);
}
