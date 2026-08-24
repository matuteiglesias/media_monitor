import { loadSiteSnapshot } from "./loaders";

export function loadOutlet() {
  const snapshot = loadSiteSnapshot();
  if (snapshot?.schema_name === "site_snapshot.v2") {
    return {
      ...snapshot,
      publication: snapshot.publication,
      articles: snapshot.articles,
      signals: snapshot.signals,
    };
  }

  return {
    ...snapshot,
    publication: { featured: null, latest: [] },
    articles: {},
    signals: {
      hero: snapshot.hero,
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

export function findArticle(slug: string) {
  const outlet = loadOutlet();
  const article = outlet.articles?.[slug] ?? null;
  return article?.status === "published" ? article : null;
}
