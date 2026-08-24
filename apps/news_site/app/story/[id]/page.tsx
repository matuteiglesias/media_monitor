import Link from "next/link";
import { notFound } from "next/navigation";
import {
  findStory,
  findStoryContext,
  loadOutlet,
} from "@/lib/adapter/mappers";
import { curationReasonLabel } from "@/lib/curation_labels";
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
    <main className="mx-auto max-w-4xl px-6 py-10">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">
        Señal monitoreada · fuente externa
      </p>
      <p className="mt-3 text-sm text-neutral-500">
        {outlet.site.name} · {item.topic} · {item.source}
      </p>
      <h1 className="mt-2 text-3xl font-semibold">{item.title}</h1>
      <p className="mt-2 text-sm text-neutral-600">{item.published_at}</p>

      <div className="mt-6 border-l-4 border-neutral-300 pl-4 text-sm text-neutral-600">
        Este registro es un titular detectado por el sistema de monitoreo y no es
        un artículo ni análisis editorial de Media Monitor. El contexto que aparece
        debajo se deriva de señales y agrupaciones observadas; no reemplaza el
        contenido de las fuentes originales.
      </div>

      <a
        className="mt-6 inline-block font-medium underline"
        href={item.link}
        target="_blank"
        rel="noreferrer"
      >
        Abrir fuente original
      </a>

      <section className="mt-10 border-t pt-8">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">
          Contexto de cobertura
        </p>
        {context ? (
          <>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <div className="border p-4">
                <div className="text-2xl font-semibold">{context.coverage_count}</div>
                <div className="mt-1 text-xs text-neutral-500">
                  señales en la cobertura detectada
                </div>
              </div>
              <div className="border p-4">
                <div className="text-2xl font-semibold">{context.source_count}</div>
                <div className="mt-1 text-xs text-neutral-500">fuentes distintas</div>
              </div>
              <div className="border p-4">
                <div className="text-sm font-medium">
                  {context.coverage_first_published_at}
                </div>
                <div className="mt-1 text-xs text-neutral-500">
                  primera señal · última {context.coverage_latest_published_at}
                </div>
              </div>
            </div>

            <div className="mt-5">
              <h2 className="text-sm font-semibold">Fuentes observadas</h2>
              <div className="mt-2 flex flex-wrap gap-2">
                {context.sources.map((source: string) => (
                  <span key={source} className="border px-2 py-1 text-xs text-neutral-600">
                    {source}
                  </span>
                ))}
              </div>
            </div>

            {context.window_types.length ? (
              <p className="mt-4 text-xs text-neutral-500">
                Ventanas de agrupación observadas: {context.window_types.join(", ")}.
              </p>
            ) : (
              <p className="mt-4 text-xs text-neutral-500">
                No hay una agrupación multi-señal materializada para este registro;
                el contexto disponible es un singleton observado.
              </p>
            )}
          </>
        ) : (
          <div className="mt-4 border p-4 text-sm text-neutral-600">
            Este despliegue todavía no contiene un contexto de cobertura
            materializado para esta señal. La fuente original y el cable
            cronológico siguen siendo la evidencia disponible.
          </div>
        )}
      </section>

      <section className="mt-10 border-t pt-8">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">
          Qué importa ahora
        </p>
        {context?.curation?.selected ? (
          <div className="mt-4 border p-5">
            <p className="font-medium">
              Esta señal ocupa el puesto #{context.curation.rank} de la shortlist
              determinística actual.
            </p>
            <p className="mt-2 text-sm text-neutral-500">
              La selección ordena monitoreo externo; no constituye aprobación,
              autoría ni análisis editorial.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {context.curation.reason_codes.map((code: string) => (
                <span key={code} className="border px-2 py-1 text-xs text-neutral-600">
                  {curationReasonLabel(code)}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <p className="mt-4 text-sm text-neutral-600">
            Esta señal forma parte del cable monitoreado, pero no de la shortlist
            determinística “Qué importa ahora” de este corte.
          </p>
        )}
      </section>

      <section className="mt-10 border-t pt-8">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">
          Cobertura relacionada
        </p>
        {context?.related_signals?.length ? (
          <div className="mt-4 divide-y border-y">
            {context.related_signals.slice(0, 8).map((related: any) => (
              <article key={related.link} className="py-4">
                <p className="text-xs uppercase tracking-[0.12em] text-neutral-500">
                  {related.source} · {related.published_at}
                </p>
                {related.index_id && publicSignalIds.has(related.index_id) ? (
                  <Link
                    href={`/story/${related.index_id}`}
                    className="mt-1 block font-medium"
                  >
                    {related.title}
                  </Link>
                ) : (
                  <a
                    href={related.link}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 block font-medium underline"
                  >
                    {related.title}
                  </a>
                )}
              </article>
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm text-neutral-600">
            No hay otras señales materializadas en el mismo contexto de cobertura.
          </p>
        )}
      </section>

      <section className="mt-10 border-t pt-8">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">
          Análisis aprobado relacionado
        </p>
        <p className="mt-2 max-w-3xl text-sm text-neutral-500">
          Solo aparecen artículos que ya atravesaron la aprobación humana de Media
          Monitor. La relación se determina por fuente citada, grupo de cobertura o
          tema; nunca por generación automática de una explicación.
        </p>
        {relatedAnalysis.length ? (
          <div className="mt-4 space-y-4">
            {relatedAnalysis.map(({ article, relation }) => (
              <article key={article.article_id} className="border p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-neutral-500">
                  Análisis editorial · aprobado · {articleRelationLabel(relation)}
                </p>
                <Link
                  href={`/articles/${article.slug}`}
                  className="mt-2 block text-xl font-semibold"
                >
                  {article.title}
                </Link>
                <p className="mt-2 text-sm text-neutral-600">{article.summary}</p>
                <p className="mt-2 text-xs text-neutral-500">
                  {article.topic} · {article.published_at}
                </p>
              </article>
            ))}
          </div>
        ) : (
          <div className="mt-4 border p-4 text-sm text-neutral-600">
            No hay análisis editorial humanamente aprobado relacionado con esta
            señal en el snapshot actual. No se sustituyen artículos aprobados por
            titulares monitoreados ni borradores.
          </div>
        )}
      </section>
    </main>
  );
}
