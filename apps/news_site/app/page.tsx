import Link from "next/link";
import { loadOutlet } from "@/lib/adapter/mappers";

export default function HomePage() {
  const outlet = loadOutlet();
  const { site, publication, signals } = outlet;
  const featured = publication.featured;
  const moreAnalysis = publication.latest.filter(
    (item: any) => item.slug !== featured?.slug,
  );

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <header className="border-b pb-6">
        <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
          {site.locale}
        </div>
        <h1 className="mt-2 text-4xl font-semibold">{site.name}</h1>
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
                        <Link
                          href={`/articles/${item.slug}`}
                          className="font-medium"
                        >
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
          Lo que estamos monitoreando
        </div>
        <div className="mt-4 border-l-4 border-neutral-300 pl-5">
          <div className="text-xs font-medium uppercase tracking-[0.14em] text-neutral-500">
            Señal monitoreada · fuente externa
          </div>
          <div className="mt-2 text-sm text-neutral-500">{signals.hero.source}</div>
          <h2 className="mt-2 text-3xl font-semibold">{signals.hero.title}</h2>
          <p className="mt-2 text-sm text-neutral-600">{signals.hero.published_at}</p>
          <p className="mt-3 max-w-3xl text-sm text-neutral-500">
            Titular detectado por el sistema de monitoreo. No constituye análisis
            editorial de Media Monitor.
          </p>
          <Link
            href={`/story/${signals.hero.index_id}`}
            className="mt-4 inline-block text-sm underline"
          >
            Ver señal y fuente
          </Link>
        </div>
      </section>

      <section className="mt-10 grid gap-8 lg:grid-cols-[2fr,1fr]">
        <div>
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-neutral-500">
                Señales recientes
              </div>
              <h2 className="mt-1 text-xl font-semibold">Monitoreo de fuentes</h2>
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
