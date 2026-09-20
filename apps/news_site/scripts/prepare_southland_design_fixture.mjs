import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const appRoot = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(appRoot, "../..");
const fixturePath = path.join(repoRoot, "contracts/tests/fixtures/site_snapshot.v4.example.json");
const sitePath = path.join(repoRoot, "sites/southland.json");
const publicIdentityPath = path.join(repoRoot, "config/outlets/southland/public_identity.json");
const editorialIdentityPath = path.join(repoRoot, "config/outlets/southland/editorial_identity.json");

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  }
  return value;
}

const site = JSON.parse(fs.readFileSync(sitePath, "utf8"));
const snapshot = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
const articleSeeds = [
  ["mieli-reunion", "Javier Mieli abre una reunión de gobierno en la portada de prueba", "Política", "Una pieza ficticia de diseño para probar el peso de una gran historia política con ilustración."],
  ["capuccino-presupuesto", "Toto Capuccino lleva el presupuesto a la mesa de pruebas", "Economía", "Fixture editorial para evaluar titulares económicos, imágenes y jerarquía secundaria."],
  ["bulldog-conferencia", "Patricia Bulldog prepara una conferencia para la maqueta", "Política", "Historia ficticia de diseño utilizada sólo para revisar composición editorial."],
  ["kicillofsky-despacho", "Kicillofsky entra al despacho de la edición experimental", "Provincias", "Fixture visual para comprobar el comportamiento de una historia con o sin imagen."],
  ["llavero-gobernadores", "Martín Llavero aparece entre gobernadores de la portada de prueba", "Provincias", "Historia de maqueta para revisar densidad y tipografía de las piezas de tercer nivel."],
  ["mieli-seguridad", "Mieli recorre un operativo completamente ficticio de diseño", "Política", "Fixture local no publicable para probar una segunda imagen y una pieza de seguridad."],
];

const articles = {};
const publication = [];
for (let i = 0; i < articleSeeds.length; i += 1) {
  const [slug, title, topic, summary] = articleSeeds[i];
  const publishedAt = `2026-09-20T0${8 - i}:00:00Z`;
  const article = {
    schema_name: "published_article.v1",
    article_id: `design-article-${i + 1}`,
    draft_id: `design-draft-${i + 1}`,
    digest_at: "20260920T08",
    story_group_id: `design-group-${i + 1}`,
    slug,
    title,
    summary,
    body_md: `# ${title}\n\nEste texto existe únicamente como fixture local de diseño para Southland Times. Permite evaluar longitud de línea, ritmo editorial y comportamiento de las ilustraciones sin alterar el runtime de publicación.`,
    topic,
    source_links: ["https://example.test/southland-design-fixture"],
    citations: [{
      citation_id: "design-c1",
      claim_text: "Fixture local de diseño; no representa una afirmación factual.",
      source_ref_id: "design-source",
      url: "https://example.test/southland-design-fixture",
    }],
    status: "published",
    review_status: "human_approved",
    published_at: publishedAt,
    updated_at: publishedAt,
  };
  articles[slug] = article;
  publication.push({
    article_id: article.article_id,
    slug,
    title,
    summary,
    topic,
    published_at: publishedAt,
    updated_at: publishedAt,
  });
}

const signals = Array.from({ length: 5 }, (_, i) => ({
  index_id: `design-signal-${i + 1}`,
  title: [
    "Cable de prueba: economía y política ocupan la agenda monitoreada",
    "Cable de prueba: gobernadores concentran otra señal externa",
    "Cable de prueba: una noticia institucional entra al monitoreo",
    "Cable de prueba: movimiento económico para revisar la grilla",
    "Cable de prueba: última señal de la maqueta local",
  ][i],
  topic: i % 2 === 0 ? "Política" : "Economía",
  published_at: `2026-09-20T0${9 - i}:15:00Z`,
  link: "https://example.test/external-signal",
  source: "Fuente externa de prueba",
}));

snapshot.site = {
  site_id: "southland",
  name: site.name,
  tagline: site.tagline,
  locale: site.locale,
};
snapshot.digest_at = "20260920T08";
snapshot.generated_at = "2026-09-20T08:30:00Z";
snapshot.publication = { featured: publication[0], latest: publication };
snapshot.articles = articles;
snapshot.signals = {
  hero: signals[0],
  curated: [],
  latest: signals,
  sections: [
    { topic: "Política", article_count: 3, top_titles: signals.filter((x) => x.topic === "Política").map((x) => x.title) },
    { topic: "Economía", article_count: 2, top_titles: signals.filter((x) => x.topic === "Economía").map((x) => x.title) },
  ],
};
snapshot.story_contexts = {};
snapshot.metrics = {
  item_count: signals.length,
  section_count: snapshot.signals.sections.length,
  published_article_count: publication.length,
  curated_signal_count: 0,
  story_context_count: 0,
};
const canonical = structuredClone(snapshot);
delete canonical.snapshot_id;
delete canonical.generated_at;
snapshot.snapshot_id = crypto.createHash("sha256").update(JSON.stringify(stable(canonical))).digest("hex");

fs.mkdirSync(path.join(appRoot, "public/data"), { recursive: true });
fs.mkdirSync(path.join(appRoot, "config"), { recursive: true });
fs.writeFileSync(path.join(appRoot, "public/data/site_snapshot.json"), JSON.stringify(snapshot, null, 2) + "\n");
fs.writeFileSync(path.join(appRoot, "config/site_presentation.json"), JSON.stringify({ schema_name: "site_presentation.v1", ...site.presentation }, null, 2) + "\n");
fs.copyFileSync(publicIdentityPath, path.join(appRoot, "config/public_identity.json"));
fs.copyFileSync(editorialIdentityPath, path.join(appRoot, "config/editorial_identity.json"));

console.log(JSON.stringify({
  status: "ok",
  warning: "LOCAL DESIGN FIXTURE ONLY — never publication state",
  snapshot_id: snapshot.snapshot_id,
  article_count: publication.length,
  signal_count: signals.length,
}));
