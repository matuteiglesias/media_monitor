import { loadSiteSnapshot } from "./loaders";

export function loadSourceSite() {
  return loadSiteSnapshot();
}

export function findStory(id: string) {
  const snapshot = loadSiteSnapshot();
  return snapshot.latest.find((item: any) => item.index_id === id) ?? null;
}
