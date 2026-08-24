import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { findArticle, loadOutlet } from "@/lib/adapter/mappers";
import { EDITORIAL_IDENTITY } from "@/lib/editorial_identity";
import { articleJsonLd, articleMetadata, serializeJsonLd } from "@/lib/seo";

function ArticleBody({ body }: { body: string }) {
  const blocks = body.split(/\n{2,}/).map((block) => block.trim()).filter(Boolean);
  return (
    <div className="mt-8 space-y-5 text-[1.05rem] leading-8 text-neutral-800">
      {blocks.map((block, index) => {
        if (block.startsWith("### ")) return <h3 key={index} className="pt-2 text-xl font-semibold">{block.slice(4)}</h3>;
        if (block.startsWith("## ")) return <h2 key={index} className="pt-3 text-2xl font-semibold">{block.slice(3)}</h2>;
        if (block.startsWith("# ")) return <h2 key={index} className="pt-3 text-2xl font-semibold">{block.slice(2)}</h2>;
        const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
        if (lines.length && lines.every((line) => line.startsWith("- "))) {
          return <ul key={index} className="list-disc space-y-2 pl-6">{lines.map((line, lineIndex) => <li key={lineIndex}>{line.slice(2)}</li>)}</ul>;
        }
        return <p key={index} className="whitespace-pre-line">{block}</p>;
      })}
    </div>
  );
}

export function generateMetadata({ params }: { params: { slug: string } }): Metadata {
  const article = findArticle(params.slug);
  if (!article) return { title: `Artículo no encontrado | Media Monitor`, robots: { index: false } };
  return articleMetadata(article);
}

export default function ArticlePage({ params }: { params: { slug: string } }) {
  const article = findArticle(params.slug);
  if (!article) notFound();
  const outlet = loadOutlet();
  const editor = EDITORIAL_IDENTITY.editor;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: serializeJsonLd(articleJsonLd(article)) }} />
      <Link href="/" className="text-sm underline">← Volver a la portada</Link>
      <article className="mt-8">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">Análisis editorial · aprobado</p>
        <p className="mt-3 text-sm text-neutral-500">{outlet.site.name} · {article.topic}</p>
        <h1 className="mt-3 text-4xl font-semibold leading-tight">{article.title}</h1>
        <p className="mt-4 text-xl leading-8 text-neutral-700">{article.summary}</p>
        <p className="mt-5 text-sm text-neutral-700">
          Por <Link href={EDITORIAL_IDENTITY.routes.author} className="font-medium underline">{editor.name}</Link> · {editor.role}
        </p>
        <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 border-y py-4 text-sm text-neutral-600">
          <span>Publicado: {article.published_at}</span>
          <span>Actualizado: {article.updated_at}</span>
          <span>Estado: {article.review_status}</span>
          <span>Edición: {outlet.site.name}</span>
        </div>

        <ArticleBody body={article.body_md} />

        <section className="mt-12 border-t pt-8">
          <h2 className="text-2xl font-semibold">Evidencia y citas</h2>
          {article.citations.length ? (
            <ol className="mt-5 space-y-5">
              {article.citations.map((citation: any) => (
                <li key={citation.citation_id} className="border-l-4 border-neutral-300 pl-4">
                  <p className="text-sm text-neutral-700">{citation.claim_text}</p>
                  <a href={citation.url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-sm underline">Abrir fuente citada</a>
                </li>
              ))}
            </ol>
          ) : <p className="mt-4 text-sm text-neutral-600">Sin citas estructuradas adicionales.</p>}
        </section>

        <section className="mt-10 border-t pt-8">
          <h2 className="text-xl font-semibold">Fuentes utilizadas</h2>
          <ul className="mt-4 space-y-2">
            {article.source_links.map((url: string) => (
              <li key={url}><a href={url} target="_blank" rel="noreferrer" className="break-all text-sm underline">{url}</a></li>
            ))}
          </ul>
        </section>
      </article>
    </main>
  );
}
