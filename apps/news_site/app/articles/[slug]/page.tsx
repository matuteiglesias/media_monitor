import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { findArticle, loadOutlet } from "@/lib/adapter/mappers";
import { EDITORIAL_IDENTITY } from "@/lib/editorial_identity";
import { formatPublicDate } from "@/lib/format";
import { articleJsonLd, articleMetadata, serializeJsonLd } from "@/lib/seo";

function ArticleBody({ body }: { body: string }) {
  const blocks = body.split(/\n{2,}/).map((block) => block.trim()).filter(Boolean);
  return (
    <div className="prose-editorial mt-9 space-y-6 text-stone-800">
      {blocks.map((block, index) => {
        if (block.startsWith("### ")) return <h3 key={index} className="pt-3 text-2xl font-semibold">{block.slice(4)}</h3>;
        if (block.startsWith("## ")) return <h2 key={index} className="pt-4 text-3xl font-semibold">{block.slice(3)}</h2>;
        if (block.startsWith("# ")) return <h2 key={index} className="pt-4 text-3xl font-semibold">{block.slice(2)}</h2>;
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
    <main className="publication-shell py-8 sm:py-12">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: serializeJsonLd(articleJsonLd(article)) }} />
      <div className="mx-auto max-w-4xl">
        <Link href="/" className="text-xs font-semibold uppercase tracking-[0.08em] text-stone-500 underline underline-offset-4">← Portada</Link>
        <article className="mt-8">
          <div className="eyebrow">Análisis editorial · aprobado</div>
          <p className="meta-line mt-4">{outlet.site.name} · {article.topic}</p>
          <h1 className="mt-4 text-5xl font-semibold leading-[1.02] sm:text-6xl">{article.title}</h1>
          <p className="mt-6 max-w-3xl text-xl leading-8 text-stone-700 sm:text-2xl sm:leading-9">{article.summary}</p>

          <div className="mt-7 flex flex-wrap items-center justify-between gap-5 border-y border-stone-300 py-4">
            <p className="text-sm text-stone-700">
              Por <Link href={EDITORIAL_IDENTITY.routes.author} className="font-bold underline underline-offset-4">{editor.name}</Link> · {editor.role}
            </p>
            <div className="text-right text-xs leading-5 text-stone-500">
              <div>Publicado {formatPublicDate(article.published_at, outlet.site.locale)}</div>
              {article.updated_at !== article.published_at ? <div>Actualizado {formatPublicDate(article.updated_at, outlet.site.locale)}</div> : null}
            </div>
          </div>

          <ArticleBody body={article.body_md} />

          <section className="mt-14 border-t border-stone-300 pt-8">
            <div className="section-kicker">Transparencia</div>
            <h2 className="mt-3 text-3xl font-semibold">Evidencia y citas</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">
              Claims estructurados y enlaces a las fuentes utilizadas para que la lectura pueda continuar fuera de Media Monitor.
            </p>
            {article.citations.length ? (
              <ol className="mt-6 grid gap-4 sm:grid-cols-2">
                {article.citations.map((citation: any, index: number) => (
                  <li key={citation.citation_id} className="publication-surface p-5">
                    <p className="eyebrow">Cita {String(index + 1).padStart(2, "0")}</p>
                    <p className="mt-3 text-sm leading-6 text-stone-700">{citation.claim_text}</p>
                    <a href={citation.url} target="_blank" rel="noreferrer" className="mt-4 inline-block text-xs font-bold uppercase tracking-[0.06em] text-[#8d2b2b] underline underline-offset-4">Abrir fuente citada ↗</a>
                  </li>
                ))}
              </ol>
            ) : <p className="mt-5 text-sm text-stone-600">Sin citas estructuradas adicionales.</p>}
          </section>

          <section className="mt-10 border-t border-stone-300 pt-8">
            <div className="section-kicker">Fuentes</div>
            <ul className="mt-5 divide-y divide-stone-200 border-y border-stone-300">
              {article.source_links.map((url: string) => {
                let label = url;
                try { label = new URL(url).hostname.replace(/^www\./, ""); } catch {}
                return (
                  <li key={url} className="py-3">
                    <a href={url} target="_blank" rel="noreferrer" className="flex items-center justify-between gap-4 text-sm font-semibold hover:text-[#8d2b2b]">
                      <span>{label}</span><span aria-hidden>↗</span>
                    </a>
                  </li>
                );
              })}
            </ul>
          </section>
        </article>
      </div>
    </main>
  );
}
