import type { MetadataRoute } from "next";
import { loadOutlet } from "@/lib/adapter/mappers";
import { EDITORIAL_IDENTITY } from "@/lib/editorial_identity";
import { canonicalUrl } from "@/lib/seo";

export default function sitemap(): MetadataRoute.Sitemap {
  const outlet = loadOutlet();
  const generated = outlet.generated_at ? new Date(outlet.generated_at) : new Date();
  const staticPaths = [
    "/",
    "/about",
    EDITORIAL_IDENTITY.routes.author,
    EDITORIAL_IDENTITY.routes.methodology,
    EDITORIAL_IDENTITY.routes.journalists,
    "/latest",
  ];

  const entries: MetadataRoute.Sitemap = staticPaths.map((pathname) => ({
    url: canonicalUrl(pathname),
    lastModified: generated,
    changeFrequency: pathname === "/" || pathname === "/latest" ? "hourly" : "monthly",
    priority: pathname === "/" ? 1 : pathname === EDITORIAL_IDENTITY.routes.author ? 0.8 : 0.6,
  }));

  for (const article of Object.values(outlet.articles ?? {}) as any[]) {
    if (article?.status !== "published" || article?.review_status !== "human_approved") continue;
    entries.push({
      url: canonicalUrl(`/articles/${article.slug}`),
      lastModified: new Date(article.updated_at),
      changeFrequency: "monthly",
      priority: 0.9,
    });
  }

  for (const signal of outlet.signals?.latest ?? []) {
    entries.push({
      url: canonicalUrl(`/story/${signal.index_id}`),
      lastModified: new Date(signal.published_at),
      changeFrequency: "never",
      priority: 0.4,
    });
  }

  for (const section of outlet.signals?.sections ?? []) {
    entries.push({
      url: canonicalUrl(`/topic/${encodeURIComponent(section.topic)}`),
      lastModified: generated,
      changeFrequency: "hourly",
      priority: 0.5,
    });
  }

  return entries;
}
