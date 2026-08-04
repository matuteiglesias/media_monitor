import fs from "node:fs";

export function readSnapshotDigest(snapshotPath) {
  if (!fs.existsSync(snapshotPath)) {
    throw new Error(`site snapshot does not exist: ${snapshotPath}`);
  }

  let snapshot;
  try {
    snapshot = JSON.parse(fs.readFileSync(snapshotPath, "utf8"));
  } catch (error) {
    throw new Error(`site snapshot is not valid JSON: ${error.message}`);
  }

  if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot)) {
    throw new Error("site snapshot must be an object");
  }

  const digestAt = snapshot.digest_at;
  if (typeof digestAt !== "string" || !digestAt.trim()) {
    throw new Error("site snapshot digest_at must be a non-empty string");
  }

  return digestAt.trim();
}

export function resolveRequestedDigest({ snapshotPath, requestedDigest }) {
  const snapshotDigest = readSnapshotDigest(snapshotPath);
  const assertion = requestedDigest?.trim() || null;

  if (assertion && assertion !== snapshotDigest) {
    throw new Error(
      `snapshot digest_at ${snapshotDigest} does not match DIGEST_AT ${assertion}`,
    );
  }

  return snapshotDigest;
}
