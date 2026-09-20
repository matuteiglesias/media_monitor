import Link from "next/link";
import { ArticleVisual, hasArticleVisual } from "@/components/ArticleVisual";
import { SITE_PRESENTATION } from "@/lib/site_presentation";
import { formatPublicDate } from "@/lib/format";

function ArticleBody({ body }: { body: string }) {
  const blocks = body.split(/\n{2,}/).map((block) => block.trim()).filter(Boolean);
  return (
    <div className="st-article-body">
      {blocks.map((block, index) => {
        if (block.startsWith("### ")) return <h3 key={index}>{block.slice(4)}</h3>;
        if (block.startsWith("## ")) return <h2 key={index}>{block.slice(3)}</h2>;
        if (block.startsWith("# ")) return <h2 key={index}>{block.slice(2)}</h2>;
        const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
        if (lines.length && lines.every((line) => line.startsWith("- "))) {
          return <ul key={index}>{lines.map((line, lineIndex) => <li key={lineIndex}>{line.slice(2)}</li>)}</ul>;
        }
        return <p key={index}>{block}</p>;
      })}
    </div>
  );
}

export function SouthlandArticle({
  article,
  outlet,
  editor,
}: {
  article: any;
  outlet: any;
  editor: any;
}) {
  return (
    <article className="st-article">
      <Link href="/" className="st-back-link">← Portada</Link>

      <header className="st-article-header">
        <p className="st-kicker">{article.topic}</p>
        <h1>{article.title}</h1>
        <p className="st-article-dek">{article.summary}</p>
        <div className="st-byline-row">
          <span>Por <Link href="/authors/matias-iglesias">{editor.name}</Link></span>
          <span>Publicado {formatPublicDate(article.published_at, outlet.site.locale)}</span>
          {article.updated_at !== article.published_at ? (
            <span>Actualizado {formatPublicDate(article.updated_at, outlet.site.locale)}</span>
          ) : null}
        </div>
      </header>

      {hasArticleVisual(article.slug) ? (
        <ArticleVisual
          slug={article.slug}
          title={article.title}
          className="st-article-hero"
        />
      ) : null}

      <aside className="st-reality-note">
        <strong>Realidad / Southland</strong>
        <span>
          El evento de partida y sus fuentes son reales. La narración, los nombres paródicos y las exageraciones pertenecen al universo ficticio de Southland Times.
        </span>
        <Link href="/methodology">Cómo se construye →</Link>
      </aside>

      <ArticleBody body={article.body_md} />

      {hasArticleVisual(article.slug, 1) ? (
        <ArticleVisual
          slug={article.slug}
          title={article.title}
          slot={1}
          className="st-article-secondary-visual"
        />
      ) : null}

      <section className="st-evidence" aria-labelledby="evidence-title">
        <div className="st-evidence-heading">
          <p className="st-kicker">Realidad documentada</p>
          <h2 id="evidence-title">Fuentes del evento real</h2>
          <p>{SITE_PRESENTATION.source_disclosure}</p>
        </div>

        {article.citations.length ? (
          <ol className="st-citation-grid">
            {article.citations.map((citation: any, index: number) => (
              <li key={citation.citation_id}>
                <span>Fuente {String(index + 1).padStart(2, "0")}</span>
                <p>{citation.claim_text}</p>
                <a href={citation.url} target="_blank" rel="noreferrer">Abrir fuente ↗</a>
              </li>
            ))}
          </ol>
        ) : null}

        {article.source_links.length ? (
          <div className="st-source-links">
            {article.source_links.map((url: string) => {
              let label = url;
              try { label = new URL(url).hostname.replace(/^www\./, ""); } catch {}
              return (
                <a key={url} href={url} target="_blank" rel="noreferrer">
                  {label} ↗
                </a>
              );
            })}
          </div>
        ) : null}
      </section>
    </article>
  );
}
