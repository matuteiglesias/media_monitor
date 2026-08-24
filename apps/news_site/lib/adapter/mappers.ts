import { loadSiteSnapshot } from "./loaders";

export function loadSourceSite() {
  const snapshot = loadSiteSnapshot();
  if (snapshot?.schema_name === "site_snapshot.v2") {
    return {
      ...snapshot,
      // P0-C1 is contract migration only. Keep the current source-news renderer
      // unchanged until P0-C2 deliberately makes publication evidence primary.
      hero: snapshot.signals.hero,
      latest: snapshot.signals.latest,
      sections: snapshot.signals.sections,
    };
  }
  return snapshot;
}

export function findStory(id: string) {
  const snapshot = loadSiteSnapshot();
  const latest =
    snapshot?.schema_name === "site_snapshot.v2"
      ? snapshot.signals.latest
      : snapshot.latest;
  return latest.find((item: any) => item.index_id === id) ?? null;
}
