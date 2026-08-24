export type ArticleRelationKind = "source" | "group" | "topic";

export type RelatedApprovedArticle = {
  article: any;
  relation: ArticleRelationKind;
};

function relationKind(story: any, context: any, article: any): ArticleRelationKind | null {
  if (
    Array.isArray(article?.source_links) &&
    article.source_links.includes(story?.link)
  ) {
    return "source";
  }

  if (
    context &&
    Array.isArray(context.group_ids) &&
    context.group_ids.includes(article?.story_group_id)
  ) {
    return "group";
  }

  if (article?.topic && article.topic === story?.topic) {
    return "topic";
  }

  return null;
}

const RELATION_WEIGHT: Record<ArticleRelationKind, number> = {
  source: 3,
  group: 2,
  topic: 1,
};

export function relatedApprovedArticles(
  story: any,
  context: any,
  articles: Record<string, any> | undefined,
  limit = 3,
): RelatedApprovedArticle[] {
  return Object.values(articles ?? {})
    .filter(
      (article: any) =>
        article?.schema_name === "published_article.v1" &&
        article?.status === "published" &&
        article?.review_status === "human_approved",
    )
    .map((article: any) => {
      const relation = relationKind(story, context, article);
      return relation ? { article, relation } : null;
    })
    .filter((value): value is RelatedApprovedArticle => value !== null)
    .sort((left, right) => {
      const relationDelta =
        RELATION_WEIGHT[right.relation] - RELATION_WEIGHT[left.relation];
      if (relationDelta) return relationDelta;
      const dateDelta = String(right.article.published_at).localeCompare(
        String(left.article.published_at),
      );
      if (dateDelta) return dateDelta;
      return String(left.article.article_id).localeCompare(
        String(right.article.article_id),
      );
    })
    .slice(0, Math.max(0, limit));
}

export function articleRelationLabel(kind: ArticleRelationKind) {
  if (kind === "source") return "Cita esta fuente";
  if (kind === "group") return "Misma cobertura agrupada";
  return "Mismo tema";
}
