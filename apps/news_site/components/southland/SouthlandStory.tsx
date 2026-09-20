import Link from "next/link";
import { ArticleVisual, hasArticleVisual } from "@/components/ArticleVisual";
import { formatPublicDate } from "@/lib/format";

type Story = {
  article_id: string;
  slug: string;
  title: string;
  summary: string;
  topic: string;
  published_at: string;
};

export function SouthlandStory({
  story,
  locale,
  variant,
}: {
  story: Story;
  locale: string;
  variant: "lead" | "rail" | "grid";
}) {
  const visual = hasArticleVisual(story.slug);

  if (variant === "lead") {
    return (
      <article className={`st-lead-story ${visual ? "st-has-visual" : "st-text-only"}`}>
        {visual ? (
          <ArticleVisual
            slug={story.slug}
            title={story.title}
            className="st-lead-visual"
          />
        ) : null}
        <div className="st-story-copy">
          <p className="st-kicker">{story.topic}</p>
          <h1 className="st-lead-headline">
            <Link href={`/articles/${story.slug}`} className="article-link">
              {story.title}
            </Link>
          </h1>
          <p className="st-lead-dek">{story.summary}</p>
          <p className="st-story-date">{formatPublicDate(story.published_at, locale)}</p>
        </div>
      </article>
    );
  }

  if (variant === "rail") {
    return (
      <article className={`st-rail-story ${visual ? "st-has-visual" : "st-text-only"}`}>
        {visual ? (
          <ArticleVisual
            slug={story.slug}
            title={story.title}
            className="st-rail-visual"
          />
        ) : null}
        <p className="st-kicker">{story.topic}</p>
        <h2 className="st-rail-headline">
          <Link href={`/articles/${story.slug}`} className="article-link">
            {story.title}
          </Link>
        </h2>
        <p className="st-story-date">{formatPublicDate(story.published_at, locale)}</p>
      </article>
    );
  }

  return (
    <article className={`st-grid-story ${visual ? "st-has-visual" : "st-text-only"}`}>
      {visual ? (
        <ArticleVisual
          slug={story.slug}
          title={story.title}
          className="st-grid-visual"
        />
      ) : null}
      <p className="st-kicker">{story.topic}</p>
      <h2 className="st-grid-headline">
        <Link href={`/articles/${story.slug}`} className="article-link">
          {story.title}
        </Link>
      </h2>
      <p className="st-grid-dek">{story.summary}</p>
    </article>
  );
}
