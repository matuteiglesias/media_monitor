import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(appRoot, "../..");
const source = path.join(repoRoot, "contracts", "tests", "fixtures", "site_snapshot.v4.example.json");
const target = path.join(appRoot, "public", "data", "site_snapshot.json");

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableValue(value[key])]));
  }
  return value;
}

const snapshot = JSON.parse(fs.readFileSync(source, "utf8"));
const canonical = structuredClone(snapshot);
delete canonical.snapshot_id;
delete canonical.generated_at;
snapshot.snapshot_id = crypto
  .createHash("sha256")
  .update(JSON.stringify(stableValue(canonical)), "utf8")
  .digest("hex");

fs.mkdirSync(path.dirname(target), { recursive: true });
fs.writeFileSync(target, `${JSON.stringify(snapshot, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ status: "ok", snapshot_id: snapshot.snapshot_id, output: target }));
