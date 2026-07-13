import { loadRecentGroups, loadRecentRefs, loadEditorialLatest, loadPublishedArticles, loadPublishedArticleBySlug } from "./loaders";

export function loadFrontpage() {
  const refs = loadRecentRefs();
  const groups = loadRecentGroups();
  const articles = loadPublishedArticles();

  return {
    hero: articles[0] ?? refs[0] ?? null,
    publishedArticles: articles,
    latest: refs.slice(0, 12),
    groups,
  };
}

export function loadHandoff() {
  return loadEditorialLatest();
}

export function loadArticle(slug: string) {
  return loadPublishedArticleBySlug(slug);
}
