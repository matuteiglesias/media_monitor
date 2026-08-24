import { loadSiteSnapshot } from "./loaders";
import { PUBLIC_IDENTITY } from "@/lib/public_identity";

function canonicalSite(site: any) {
  return {
    ...site,
    name: PUBLIC_IDENTITY.outlet_name,
    tagline: PUBLIC_IDENTITY.outlet_tagline,
  };
}

export function loadOutlet() {
  const snapshot = loadSiteSnapshot();
  if (["site_snapshot.v2", "site_snapshot.v3", "site_snapshot.v4"].includes(snapshot?.schema_name)) {
    return {
      ...snapshot,
      site: canonicalSite(snapshot.site),
      publication: snapshot.publication,
      articles: snapshot.articles,
      story_contexts:
        snapshot.schema_name === "site_snapshot.v4" && snapshot.story_contexts
          ? snapshot.story_contexts
          : {},
      signals: {
        ...snapshot.signals,
        curated:
          ["site_snapshot.v3", "site_snapshot.v4"].includes(snapshot.schema_name) &&
          Array.isArray(snapshot.signals?.curated)
            ? snapshot.signals.curated
            : [],
      },
    };
  }

  return {
    ...snapshot,
    site: canonicalSite(snapshot.site),
    publication: { featured: null, latest: [] },
    articles: {},
    story_contexts: {},
    signals: {
      hero: snapshot.hero,
      curated: [],
      latest: snapshot.latest,
      sections: snapshot.sections,
    },
  };
}

// Compatibility alias for code that still expects the source-news projection.
export function loadSourceSite() {
  const outlet = loadOutlet();
  return {
    ...outlet,
    hero: outlet.signals.hero,
    latest: outlet.signals.latest,
    sections: outlet.signals.sections,
  };
}

export function findStory(id: string) {
  const outlet = loadOutlet();
  return outlet.signals.latest.find((item: any) => item.index_id === id) ?? null;
}

export function findStoryContext(id: string) {
  const outlet = loadOutlet();
  const context = outlet.story_contexts?.[id] ?? null;
  return context?.schema_name === "story_context.v1" ? context : null;
}

export function findArticle(slug: string) {
  const outlet = loadOutlet();
  const article = outlet.articles?.[slug] ?? null;
  return article?.status === "published" ? article : null;
}
