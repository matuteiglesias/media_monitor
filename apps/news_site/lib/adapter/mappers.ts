import { loadRecentGroups, loadRecentRefs, loadEditorialLatest } from "./loaders";

export function loadFrontpage() {
  const refs = loadRecentRefs();
  const groups = loadRecentGroups();

  return {
    hero: refs[0] ?? null,
    latest: refs.slice(0, 12),
    groups,
  };
}

export function loadHandoff() {
  return loadEditorialLatest();
}
