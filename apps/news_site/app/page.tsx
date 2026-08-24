import Link from "next/link";
import { loadOutlet } from "@/lib/adapter/mappers";
import { curationReasonLabel } from "@/lib/curation_labels";
import { EDITORIAL_IDENTITY } from "@/lib/editorial_identity";

export default function HomePage() {
  const outlet = loadOutlet();
  const { site, publication, signals } = outlet;
  const featured = publication.featured;
  const moreAnalysis = publication.latest.filter(
    (item: any) => item.slug !== featured?.slug,
  );
  const curated = Array.isArray(signals.curated) ? signals.curated : [];

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <header className="border-b pb-6">
        <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
          {site.locale}
        </div>
        <h1 className="mt-2 text-4xl font-semibold">{site.name}</h1>
        <p className="mt-2 text-sm font-medium text-neutral-700">
          {EDITORIAL_IDENTITY.endorsement_line}
        </p>
        <p className="mt-2 max-w-3xl text-neutral-600">{site.tagline}</p>
        <p className="mt-3 max-w-3xl text-sm text-neutral-500">
          Análisis editorial aprobado y monitoreo de señales de fuentes externas,
          presentados como capas distintas.
        </p>
      </header>

      <section className="mt-10 border-b pb-10">
        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-neutral-500">
          Análisis actual
        </div>
        <h2 className="mt-2 text-2xl font-semibold">Análisis y notas editoriales</h2>
        {featured ? (
          <div className="mt-6 grid gap-8 lg:grid-cols-[2fr,1fr]">
            <article>
              <div className="text-xs font-medium uppercase tracking-[0.14em] text-neutral-500">
                Análisis editorial · aprobado
              </div>
              <h3 className="mt-3 text-3xl font-semibold">{featured.title}</h3>
              <p className="mt-3 max-w-3xl text-lg text-neutral-700">
                {featured.summary}
              </p>
              <p className="mt-3 text-sm text-neutral-500">
                {featured.topic} · {featured.published_at}
              </p>
              <Link
                href={`/articles/${featured.slug}`}
                className="mt-5 inline-block text-sm font-medium underline"
              >
                Leer análisis
              </Link>
            </article>
            <aside>
              {moreAnalysis.length ? (
                <>
                  <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-neutral-500">
                    Más análisis
                  </h3>
                  <div className="mt-3 space-y-4">
                    {moreAnalysis.slice(0, 4).map((item: any) => (
                      <article key={item.article_id} className="border-t pt-3">
                        <Link href={`/articles/${item.slug}`} className="font-medium">
                          {item.title}
                        </Link>
                        <p className="mt-1 text-xs text-neutral-500">{item.topic}</p>
                      </article>
                    ))}
                  </div>
                </>
              ) : null}
            </aside>
          </div>
        ) : (
          <div className="mt-5 max-w-3xl border p-5 text-sm text-neutral-600">
            No hay análisis editorial aprobado publicado en este corte. Las señales
            de fuentes externas se muestran por separado debajo y no se presentan
            como contenido propio.
          </div>
        )}
      </section>

      <section className="mt-10 border-b pb-10">
        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-neutral-500">
          Qué importa ahora
        </div>
        <h2 className="mt-2 text-2xl font-semibold">Selección del monitoreo</h2>
        <p className="mt-2 max-w-3xl text-sm text-neutral-500">
          Shortlist determinística de señales externas según actualidad, prioridad
          temática y diversidad de fuentes/temas. Estar seleccionado no convierte
          una señal en análisis editorial de Media Monitor.
        </p>
        {curated.length ? (
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {curated.slice(0, 6).map((item: any) => (
              <article key={item.index_id} className="border p-5">
                <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.12em] text-neutral-500">
                  <span>#{item.rank} · señal monitoreada</span>
                  <span>{item.source}</span>
                </div>
                <Link
                  href={`/story/${item.index_id}`}
                  className="mt-3 block text-xl font-semibold"
                >
                  {item.title}
                </Link>
                <p className="mt-2 text-sm text-neutral-500">
                  {item.topic} · {item.published_at}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {item.reason_codes.map((code: string) => (
                    <span key={code} className="border px-2 py-1 text-xs text-neutral-600">
                      {curationReasonLabel(code)}
                    </span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="mt-5 max-w-3xl border p-5 text-sm text-neutral-600">
            Este despliegue todavía no contiene una selección editorial determinística.
            El cable cronológico sigue disponible debajo sin ser presentado como una
            shortlist curada.
          </div>
        )}
      </section>

      <section className="mt-10 grid gap-8 lg:grid-cols-[2fr,1fr]">
        <div>
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-neutral-500">
                Últimas señales
              </div>
              <h2 className="mt-1 text-xl font-semibold">Cable cronológico de fuentes</h2>
            </div>
            <Link href="/latest" className="text-sm underline">
              Ver todas
            </Link>
          </div>
          {signals.latest.map((item: any) => (
            <article key={item.index_id} className="border-b py-4">
              <div className="text-xs uppercase tracking-[0.12em] text-neutral-500">
                Fuente externa · {item.source}
              </div>
              <Link
                href={`/story/${item.index_id}`}
                className="mt-1 block text-lg font-medium"
              >
                {item.title}
              </Link>
              <p className="mt-1 text-xs text-neutral-500">{item.topic}</p>
            </article>
          ))}
        </div>
        <aside>
          <h2 className="mb-4 text-xl font-semibold">Temas monitoreados</h2>
          {signals.sections.map((section: any) => (
            <Link
              key={section.topic}
              href={`/topic/${encodeURIComponent(section.topic)}`}
              className="mb-3 block border p-4"
            >
              {section.topic} · {section.article_count}
            </Link>
          ))}
        </aside>
      </section>
    </main>
  );
}
