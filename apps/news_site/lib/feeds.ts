import { EDITORIAL_IDENTITY } from "@/lib/editorial_identity";
import { PUBLIC_IDENTITY } from "@/lib/public_identity";
import { canonicalUrl } from "@/lib/seo";

function escapeXml(value: unknown) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function rssDocument(title: string, description: string, selfPath: string, items: string[]) {
  return `<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n<title>${escapeXml(title)}</title>\n<link>${escapeXml(PUBLIC_IDENTITY.public_outlet_url)}</link>\n<description>${escapeXml(description)}</description>\n<language>es-ar</language>\n<atom:link href="${escapeXml(canonicalUrl(selfPath))}" rel="self" type="application/rss+xml" />\n${items.join("\n")}\n</channel>\n</rss>\n`;
}

export function approvedAnalysisRss(outlet: any) {
  const articles = Object.values(outlet.articles ?? {})
    .filter((article: any) => article?.schema_name === "published_article.v1" && article?.status === "published" && article?.review_status === "human_approved")
    .sort((a: any, b: any) => String(b.published_at).localeCompare(String(a.published_at)));
  const items = articles.map((article: any) => {
    const url = canonicalUrl(`/articles/${article.slug}`);
    return `<item>\n<title>${escapeXml(article.title)}</title>\n<link>${escapeXml(url)}</link>\n<guid isPermaLink="true">${escapeXml(url)}</guid>\n<description>${escapeXml(article.summary)}</description>\n<category>${escapeXml(article.topic)}</category>\n<author>${escapeXml(EDITORIAL_IDENTITY.editor.contact.email)} (${escapeXml(EDITORIAL_IDENTITY.editor.name)})</author>\n<pubDate>${new Date(article.published_at).toUTCString()}</pubDate>\n</item>`;
  });
  return rssDocument(
    `${PUBLIC_IDENTITY.outlet_name} — análisis`,
    "Análisis editorial human-approved de Media Monitor. No incluye titulares monitoreados de terceros.",
    "/feed.xml",
    items,
  );
}

export function monitoredSignalsRss(outlet: any) {
  const items = (outlet.signals?.latest ?? []).map((signal: any) => {
    const url = canonicalUrl(`/story/${signal.index_id}`);
    return `<item>\n<title>${escapeXml(signal.title)}</title>\n<link>${escapeXml(url)}</link>\n<guid isPermaLink="true">${escapeXml(url)}</guid>\n<description>${escapeXml(`Señal monitoreada de fuente externa: ${signal.source}. No constituye análisis editorial propio.`)}</description>\n<category>${escapeXml(signal.topic)}</category>\n<pubDate>${new Date(signal.published_at).toUTCString()}</pubDate>\n</item>`;
  });
  return rssDocument(
    `${PUBLIC_IDENTITY.outlet_name} — señales monitoreadas`,
    "Cable de señales detectadas en fuentes externas. Esta fuente no representa análisis editorial propio.",
    "/signals.xml",
    items,
  );
}
