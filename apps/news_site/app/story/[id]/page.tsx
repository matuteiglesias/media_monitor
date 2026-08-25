import Link from "next/link";
import { notFound } from "next/navigation";
import {
  findStory,
  findStoryContext,
  loadOutlet,
} from "@/lib/adapter/mappers";
import { curationReasonLabel } from "@/lib/curation_labels";
import { formatPublicDate } from "@/lib/format";
import {
  articleRelationLabel,
  relatedApprovedArticles,
} from "@/lib/story_relations";

export default function StoryPage({ params }: { params: { id: string } }) {
  const item = findStory(params.id);
  if (!item) notFound();

  const outlet = loadOutlet();
  const context = findStoryContext(params.id);
  const publicSignalIds = new Set(
    outlet.signals.latest.map((signal: any) => signal.index_id),
  );
  const relatedAnalysis = relatedApprovedArticles(
    item,
    context,
    outlet.articles,
    3,
  );

  return (
    <main className="publication-shell py-8 sm:py-12">
      <div className="mx-auto max-w-5xl">
        <Link href="/" className="text-xs font-semibold uppercase tracking-[0.08em] text-stone-500 underline underline-offset-4">← Portada</Link>

        <header className="mt-8 border-b border-stone-300 pb-8">
          <div className="eyebrow">Señal monitoreada · fuente externa</div>
          <p className="meta-line mt-4">{item.topic} · {item.source} · {formatPublicDate(item.published_at, outlet.site.locale)}</p>
          <h1 className="mt-4 max-w-4xl text-4xl font-semibold leading-[1.04] sm:text-5xl">{item.title}</h1>
          <div className="mt-6 grid gap-5 md:grid-cols-[minmax(0,1fr),auto] md:items-end">
            <div className="editorial-callout p-5 text-sm leading-6 text-stone-600">
              Este registro es un titular detectado por el sistema de monitoreo y no es
              un artículo ni análisis editorial de Media Monitor. El contexto que aparece
              debajo se deriva de señales y agrupaciones observadas; no reemplaza el
              contenido de las fuentes originales.
            </div>
            <a
              className="press-cta justify-center"
              href={item.link}
              target="_blank"
              rel="noreferrer"
            >
              Abrir fuente original ↗
            </a>
          </div>
        </header>

        <section className="py-9">
          <div className="section-kicker">Contexto de cobertura</div>
          {context ? (
            <>
              <div className="mt-6 grid gap-4 sm:grid-cols-3">
                <div className="publication-surface p-5">
                  <div className="editorial-serif text-4xl font-semibold">{context.coverage_count}</div>
                  <div className="mt-2 text-xs uppercase tracking-[0.06em] text-stone-500">señales detectadas</div>
                </div>
                <div className="publication-surface p-5">
                  <div className="editorial-serif text-4xl font-semibold">{context.source_count}</div>
                  <div className="mt-2 text-xs uppercase tracking-[0.06em] text-stone-500">fuentes distintas</div>
                </div>
                <div className="publication-surface p-5">
                  <div className="text-sm font-semibold">{formatPublicDate(context.coverage_first_published_at, outlet.site.locale)}</div>
                  <div className="mt-2 text-xs leading-5 text-stone-500">
                    primera señal · última {formatPublicDate(context.coverage_latest_published_at, outlet.site.locale)}
                  </div>
                </div>
              </div>

              <div className="mt-6">
                <h2 className="text-sm font-bold uppercase tracking-[0.06em]">Fuentes observadas</h2>
                <div className="mt-3 flex flex-wrap gap-2">
                  {context.sources.map((source: string) => (
                    <span key={source} className="chip">{source}</span>
                  ))}
                </div>
              </div>

              {context.window_types.length ? (
                <p className="mt-5 text-xs text-stone-500">
                  Ventanas de agrupación observadas: {context.window_types.join(", ")}.
                </p>
              ) : (
                <p className="mt-5 text-xs text-stone-500">
                  No hay una agrupación multi-señal materializada para este registro;
                  el contexto disponible es un singleton observado.
                </p>
              )}
            </>
          ) : (
            <div className="mt-5 border border-stone-300 bg-[#fffdf8] p-5 text-sm leading-6 text-stone-600">
              Este despliegue todavía no contiene un contexto de cobertura
              materializado para esta señal. La fuente original y el cable
              cronológico siguen siendo la evidencia disponible.
            </div>
          )}
        </section>

        <section className="border-t border-stone-300 py-9">
          <div className="section-kicker">Qué importa ahora</div>
          {context?.curation?.selected ? (
            <div className="mt-5 grid gap-5 bg-[#fffdf8] p-6 sm:grid-cols-[auto,minmax(0,1fr)]">
              <div className="rank-mark">{String(context.curation.rank).padStart(2, "0")}</div>
              <div>
                <p className="text-lg font-semibold">
                  Esta señal ocupa el puesto #{context.curation.rank} de la shortlist determinística actual.
                </p>
                <p className="mt-2 text-sm leading-6 text-stone-500">
                  La selección ordena monitoreo externo; no constituye aprobación,
                  autoría ni análisis editorial.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {context.curation.reason_codes.map((code: string) => (
                    <span key={code} className="chip">{curationReasonLabel(code)}</span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="mt-5 text-sm leading-6 text-stone-600">
              Esta señal forma parte del cable monitoreado, pero no de la shortlist
              determinística “Qué importa ahora” de este corte.
            </p>
          )}
        </section>

        <section className="border-t border-stone-300 py-9">
          <div className="section-kicker">Cobertura relacionada</div>
          {context?.related_signals?.length ? (
            <div className="mt-5 divide-y divide-stone-200 border-y border-stone-300">
              {context.related_signals.slice(0, 8).map((related: any) => (
                <article key={related.link} className="grid gap-2 py-4 sm:grid-cols-[9rem,minmax(0,1fr)]">
                  <p className="meta-line leading-5">
                    {related.source}<br />{formatPublicDate(related.published_at, outlet.site.locale)}
                  </p>
                  {related.index_id && publicSignalIds.has(related.index_id) ? (
                    <Link href={`/story/${related.index_id}`} className="story-link font-semibold leading-snug">
                      {related.title}
                    </Link>
                  ) : (
                    <a href={related.link} target="_blank" rel="noreferrer" className="font-semibold leading-snug underline underline-offset-4 hover:text-[#8d2b2b]">
                      {related.title}
                    </a>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <p className="mt-5 text-sm text-stone-600">
              No hay otras señales materializadas en el mismo contexto de cobertura.
            </p>
          )}
        </section>

        <section className="border-t border-stone-300 py-9">
          <div className="section-kicker">Análisis aprobado relacionado</div>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-500">
            Solo aparecen artículos que ya atravesaron la aprobación humana de Media
            Monitor. La relación se determina por fuente citada, grupo de cobertura o
            tema; nunca por generación automática de una explicación.
          </p>
          {relatedAnalysis.length ? (
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {relatedAnalysis.map(({ article, relation }) => (
                <article key={article.article_id} className="publication-surface p-6">
                  <p className="eyebrow">Análisis editorial · aprobado · {articleRelationLabel(relation)}</p>
                  <Link href={`/articles/${article.slug}`} className="article-link mt-3 block text-2xl font-semibold leading-tight">
                    {article.title}
                  </Link>
                  <p className="mt-3 text-sm leading-6 text-stone-600">{article.summary}</p>
                  <p className="meta-line mt-4">{article.topic} · {formatPublicDate(article.published_at, outlet.site.locale)}</p>
                </article>
              ))}
            </div>
          ) : (
            <div className="mt-5 border border-stone-300 bg-[#fffdf8] p-5 text-sm leading-6 text-stone-600">
              No hay análisis editorial humanamente aprobado relacionado con esta
              señal en el snapshot actual. No se sustituyen artículos aprobados por
              titulares monitoreados ni borradores.
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
