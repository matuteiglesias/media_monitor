import Link from "next/link";
import { loadOutlet } from "@/lib/adapter/mappers";
import { curationReasonLabel } from "@/lib/curation_labels";
import { EDITORIAL_IDENTITY } from "@/lib/editorial_identity";
import { formatPublicDate } from "@/lib/format";
import { OutletPulse } from "@/components/OutletPulse";

export default function HomePage() {
  const outlet = loadOutlet();
  const { site, publication, signals } = outlet;
  const featured = publication.featured;
  const moreAnalysis = publication.latest.filter(
    (item: any) => item.slug !== featured?.slug,
  );
  const curated = Array.isArray(signals.curated) ? signals.curated : [];

  return (
    <main className="publication-shell pb-8 pt-8 sm:pt-10">
      <section className="grid gap-7 border-b border-stone-300 pb-8 lg:grid-cols-[minmax(0,1.5fr),minmax(18rem,0.7fr)] lg:items-end">
        <div>
          <div className="eyebrow">Economía argentina · información para decidir qué mirar</div>
          <h1 className="mt-3 max-w-4xl text-5xl font-bold leading-[0.98] sm:text-6xl lg:text-7xl">
            Lo que se mueve.<br />Lo que importa.
          </h1>
          <p className="mt-5 max-w-3xl text-lg leading-7 text-stone-700">
            {site.tagline}
          </p>
        </div>
        <div className="border-l border-stone-300 pl-5 text-sm leading-6 text-stone-600">
          <p className="font-semibold text-stone-900">{EDITORIAL_IDENTITY.endorsement_line}</p>
          <p className="mt-2">
            Monitoreo de fuentes externas, selección determinística y análisis propio
            publicados como capas distintas.
          </p>
          <div className="mt-4 flex flex-wrap gap-4 text-xs font-semibold uppercase tracking-[0.06em]">
            <Link href="/latest" className="underline underline-offset-4">Últimas señales</Link>
            <Link href={EDITORIAL_IDENTITY.routes.journalists} className="underline underline-offset-4">Para periodistas</Link>
          </div>
        </div>
      </section>

      <OutletPulse
        curatedCount={curated.length}
        latestCount={signals.latest.length}
        topicCount={signals.sections.length}
      />

      <section className="py-10 sm:py-12">
        <div className="section-kicker">Análisis actual</div>
        {featured ? (
          <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.65fr),minmax(17rem,0.65fr)]">
            <article className="editorial-callout p-6 sm:p-8">
              <div className="meta-line">Análisis editorial · aprobado · {featured.topic}</div>
              <h2 className="mt-4 max-w-4xl text-4xl font-semibold leading-[1.05] sm:text-5xl">
                <Link href={`/articles/${featured.slug}`} className="article-link">{featured.title}</Link>
              </h2>
              <p className="mt-5 max-w-3xl text-lg leading-7 text-stone-700">{featured.summary}</p>
              <div className="mt-6 flex flex-wrap items-center gap-5 text-xs font-semibold uppercase tracking-[0.06em] text-stone-500">
                <span>{formatPublicDate(featured.published_at, site.locale)}</span>
                <Link href={`/articles/${featured.slug}`} className="text-[#8d2b2b] underline underline-offset-4">Leer análisis →</Link>
              </div>
            </article>
            <aside className="publication-surface p-5 sm:p-6">
              <div className="eyebrow">Más análisis</div>
              {moreAnalysis.length ? (
                <div className="mt-2 divide-y divide-stone-200">
                  {moreAnalysis.slice(0, 4).map((item: any) => (
                    <article key={item.article_id} className="py-4">
                      <p className="meta-line">{item.topic}</p>
                      <Link href={`/articles/${item.slug}`} className="article-link mt-2 block text-lg font-semibold leading-snug">
                        {item.title}
                      </Link>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm leading-6 text-stone-600">
                  Esta es la única pieza aprobada en el snapshot actual.
                </p>
              )}
            </aside>
          </div>
        ) : (
          <div className="editorial-callout mt-6 max-w-4xl p-6 text-sm leading-6 text-stone-600">
            <p className="font-semibold text-stone-900">El monitoreo está vivo aunque la mesa editorial esté vacía.</p>
            <p className="mt-2">
              No hay análisis editorial aprobado publicado en este corte. Las señales
              de fuentes externas se muestran por separado debajo y no se presentan
              como contenido propio.
            </p>
          </div>
        )}
      </section>

      <section className="border-t border-stone-300 py-10 sm:py-12">
        <div className="section-kicker">Qué importa ahora</div>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-5">
          <div>
            <h2 className="text-3xl font-semibold sm:text-4xl">Selección del monitoreo</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-600">
              Shortlist determinística de señales externas según actualidad, prioridad
              temática y diversidad. Estar seleccionado no convierte una señal en autoría,
              aprobación ni análisis editorial de Media Monitor.
            </p>
          </div>
          <Link href="/methodology" className="text-xs font-semibold uppercase tracking-[0.08em] text-[#8d2b2b] underline underline-offset-4">
            Ver metodología
          </Link>
        </div>

        {curated.length ? (
          <div className="mt-7 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {curated.slice(0, 6).map((item: any) => (
              <article key={item.index_id} className="signal-card flex min-h-[18rem] flex-col p-5">
                <div className="flex items-start justify-between gap-4">
                  <span className="rank-mark">{String(item.rank).padStart(2, "0")}</span>
                  <span className="max-w-[11rem] text-right text-[0.66rem] font-bold uppercase tracking-[0.08em] text-stone-500">{item.source}</span>
                </div>
                <p className="meta-line mt-3">{item.topic} · {formatPublicDate(item.published_at, site.locale)}</p>
                <Link href={`/story/${item.index_id}`} className="story-link mt-3 block text-xl font-semibold leading-snug">
                  {item.title}
                </Link>
                <div className="mt-auto flex flex-wrap gap-1.5 pt-5">
                  {item.reason_codes.slice(0, 3).map((code: string) => (
                    <span key={code} className="chip">{curationReasonLabel(code)}</span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="mt-6 max-w-3xl border border-stone-300 bg-[#fffdf8] p-5 text-sm text-stone-600">
            Este despliegue todavía no contiene una selección editorial determinística.
            El cable cronológico sigue disponible debajo sin ser presentado como una
            shortlist curada.
          </div>
        )}
      </section>

      <section className="grid gap-10 border-t border-stone-300 py-10 sm:py-12 lg:grid-cols-[minmax(0,2fr),minmax(15rem,0.7fr)]">
        <div>
          <div className="flex items-end justify-between gap-4">
            <div>
              <div className="section-kicker">Últimas señales</div>
              <h2 className="mt-3 text-3xl font-semibold">Cable cronológico</h2>
            </div>
            <Link href="/latest" className="text-xs font-semibold uppercase tracking-[0.08em] underline underline-offset-4">
              Ver todas
            </Link>
          </div>
          <div className="mt-5 border-t border-stone-300">
            {signals.latest.map((item: any) => (
              <article key={item.index_id} className="wire-row">
                <div className="meta-line leading-5">
                  <div>{formatPublicDate(item.published_at, site.locale)}</div>
                  <div className="mt-1 normal-case tracking-normal text-stone-500">{item.source}</div>
                </div>
                <div>
                  <p className="meta-line">Fuente externa · {item.topic}</p>
                  <Link href={`/story/${item.index_id}`} className="story-link mt-1 block text-lg font-semibold leading-snug sm:text-xl">
                    {item.title}
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </div>

        <aside className="lg:border-l lg:border-stone-300 lg:pl-7">
          <div className="section-kicker">Mapa rápido</div>
          <h2 className="mt-3 text-2xl font-semibold">Temas monitoreados</h2>
          <div className="mt-4 border-t border-stone-300">
            {signals.sections.map((section: any) => (
              <Link
                key={section.topic}
                href={`/topic/${encodeURIComponent(section.topic)}`}
                className="topic-link"
              >
                <span>{section.topic}</span>
                <span className="font-semibold text-stone-500">{section.article_count}</span>
              </Link>
            ))}
          </div>
          <div className="mt-8 bg-[#20201c] p-5 text-stone-100">
            <p className="eyebrow !text-[#d7aaa0]">Para medios</p>
            <p className="editorial-serif mt-2 text-2xl font-semibold leading-tight">¿Necesitás contexto o datos para una nota?</p>
            <p className="mt-3 text-sm leading-6 text-stone-300">Acceso directo al editor, áreas de expertise y análisis aprobado disponible.</p>
            <Link href={EDITORIAL_IDENTITY.routes.journalists} className="mt-4 inline-block text-xs font-bold uppercase tracking-[0.08em] underline underline-offset-4">
              Para periodistas →
            </Link>
          </div>
        </aside>
      </section>
    </main>
  );
}
