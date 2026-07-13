import { notFound } from "next/navigation";
import { loadArticle } from "@/lib/adapter/mappers";

function renderMarkdown(markdown: string) {
  return markdown
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean)
    .map((block, idx) => {
      if (block.startsWith("# ")) {
        return <h2 key={idx} className="mt-8 text-2xl font-semibold">{block.replace(/^#\s+/, "")}</h2>;
      }
      if (block.startsWith("## ")) {
        return <h3 key={idx} className="mt-6 text-xl font-semibold">{block.replace(/^##\s+/, "")}</h3>;
      }
      return <p key={idx} className="mt-4 leading-7 text-neutral-800">{block}</p>;
    });
}

export default function ArticlePage({ params }: { params: { slug: string } }) {
  const article = loadArticle(params.slug);
  if (!article) notFound();

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <header className="border-b pb-8">
        <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">{article.topic}</div>
        <h1 className="mt-3 text-4xl font-semibold leading-tight">{article.title}</h1>
        <p className="mt-4 text-xl text-neutral-700">{article.summary}</p>
        <div className="mt-4 text-sm text-neutral-500">Publicado: {article.published_at}</div>
      </header>

      <article className="prose prose-neutral mt-8 max-w-none">{renderMarkdown(article.body_md)}</article>

      <section className="mt-10 rounded border bg-neutral-50 p-4 text-sm text-neutral-700">
        <h2 className="font-semibold text-neutral-900">Nota editorial</h2>
        <p className="mt-2">
          Artículo asistido por IA y publicado desde un borrador con estado de revisión: {article.review_status}.
        </p>
      </section>

      <section className="mt-10 border-t pt-6">
        <h2 className="text-xl font-semibold">Fuentes y citas</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm">
          {article.source_links.map((link: string) => (
            <li key={link}>
              <a href={link} className="underline" target="_blank" rel="noreferrer">{link}</a>
            </li>
          ))}
        </ul>
        {article.citations.length ? (
          <ol className="mt-6 list-decimal space-y-3 pl-5 text-sm text-neutral-700">
            {article.citations.map((citation: any) => (
              <li key={citation.citation_id}>
                <span className="font-medium">{citation.claim_text}</span>{" "}
                <a href={citation.url} className="underline" target="_blank" rel="noreferrer">Fuente</a>
              </li>
            ))}
          </ol>
        ) : null}
      </section>
    </main>
  );
}
