import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDir, "..");
const snapshotPath = path.join(appRoot, "public", "data", "site_snapshot.json");
const outputPath = path.join(appRoot, "public", "data", "article_social_cards.json");

function fail(message) {
  throw new Error(`materialize_article_social_cards: ${message}`);
}

if (!fs.existsSync(snapshotPath)) fail(`missing ${snapshotPath}`);

const snapshot = JSON.parse(fs.readFileSync(snapshotPath, "utf8"));
if (snapshot?.schema_name !== "site_snapshot.v4") {
  fail(`expected site_snapshot.v4, got ${snapshot?.schema_name ?? "missing"}`);
}

const articles = snapshot?.articles;
if (!articles || typeof articles !== "object" || Array.isArray(articles)) {
  fail("snapshot articles must be an object");
}

const projection = {};
for (const [slug, article] of Object.entries(articles)) {
  if (!article || typeof article !== "object") fail(`article ${slug} must be an object`);
  if (article.schema_name !== "published_article.v1") fail(`article ${slug} has unexpected schema`);
  if (article.status !== "published" || article.review_status !== "human_approved") {
    fail(`article ${slug} is not human-approved published content`);
  }
  if (article.slug !== slug) fail(`article key/slug mismatch for ${slug}`);
  for (const field of ["title", "topic"]) {
    if (typeof article[field] !== "string" || !article[field].trim()) {
      fail(`article ${slug} is missing ${field}`);
    }
  }
  projection[slug] = { title: article.title.trim(), topic: article.topic.trim() };
}

const payload = {
  schema_name: "article_social_cards.v1",
  articles: Object.fromEntries(Object.entries(projection).sort(([a], [b]) => a.localeCompare(b))),
};

fs.mkdirSync(path.dirname(outputPath), { recursive: true });
const tempPath = `${outputPath}.tmp`;
fs.writeFileSync(tempPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
fs.renameSync(tempPath, outputPath);

console.log(JSON.stringify({ status: "ok", article_count: Object.keys(payload.articles).length, output: outputPath }));
