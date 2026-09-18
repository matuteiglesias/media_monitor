import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDir, "..");
const snapshotPath = path.join(appRoot, "public", "data", "site_snapshot.json");
const presentationPath = path.join(appRoot, "config", "site_presentation.json");
const outputPath = path.join(appRoot, "public", "data", "article_visuals.json");

function fail(message) {
  throw new Error(`materialize_article_visuals: ${message}`);
}

const snapshot = JSON.parse(fs.readFileSync(snapshotPath, "utf8"));
const presentation = JSON.parse(fs.readFileSync(presentationPath, "utf8"));
if (snapshot?.schema_name !== "site_snapshot.v4") fail("expected site_snapshot.v4");
if (presentation?.schema_name !== "site_presentation.v1") fail("expected site_presentation.v1");

const palettes = [
  ["#f6d44a", "#e95d4f", "#2f6f68", "#f4efe2"],
  ["#7fc6b5", "#ef8b4a", "#5c4c8a", "#f5e6c8"],
  ["#e7bf5a", "#b64b4b", "#3f6b8a", "#f1ead9"],
  ["#d7e55c", "#ef6c57", "#496b55", "#eee3cb"],
];

const projection = {};
for (const [slug, article] of Object.entries(snapshot.articles ?? {})) {
  const digest = crypto.createHash("sha256").update(slug).digest("hex");
  const seed = Number.parseInt(digest.slice(0, 8), 16);
  const palette = palettes[seed % palettes.length];
  projection[slug] = {
    kind: presentation.mode === "publication" ? "cutpaper_generated" : "editorial_card",
    seed,
    palette,
    alt: presentation.mode === "publication"
      ? `Ilustración original de Southland para: ${article.title}`
      : `Tarjeta editorial para: ${article.title}`,
  };
}

const payload = {
  schema_name: "article_visuals.v1",
  articles: Object.fromEntries(Object.entries(projection).sort(([a], [b]) => a.localeCompare(b))),
};

fs.mkdirSync(path.dirname(outputPath), { recursive: true });
const tmp = `${outputPath}.tmp`;
fs.writeFileSync(tmp, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
fs.renameSync(tmp, outputPath);
console.log(JSON.stringify({ status: "ok", article_count: Object.keys(payload.articles).length, output: outputPath }));
