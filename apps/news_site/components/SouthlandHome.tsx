import Link from "next/link";
import { ArticleVisual, hasArticleVisual } from "@/components/ArticleVisual";
import { SITE_PRESENTATION } from "@/lib/site_presentation";
import { formatPublicDate } from "@/lib/format";

export function SouthlandHome({ outlet }: { outlet: any }) {
  const { site, publication, signals } = outlet;
  const featured = publication.featured;
  const remaining = publication.latest.filter((item: any) => item.slug !== featured?.slug);
  const featuredHasVisual = featured ? hasArticleVisual(featured.slug) : false;

  return (
    <main className="publication-shell southland-home pb-12 pt-5 sm:pt-7">
      {featured ? (
        <section className={`${featuredHasVisual ? "grid gap-6 lg:grid-cols-[1.15fr,0.85fr] lg:items-stretch" : ""} border-b-2 border-black py-8`}>
          {featuredHasVisual ? <ArticleVisual slug={featured.slug} title={featured.title} className="min-h-[20rem] border-2 border-black sm:min-h-[25rem]" /> : null}
          <article className="flex flex-col justify-center">
            <p className="meta-line font-bold">{SITE_PRESENTATION.publication_label} · {featured.topic}</p>
            <h2 className="southland-headline mt-4 text-4xl font-black leading-[0.98] sm:text-6xl">
              <Link href={`/articles/${featured.slug}`} className="article-link">{featured.title}</Link>
            </h2>
            <p className="mt-5 text-lg font-medium leading-7 text-stone-700">{featured.summary}</p>
            <div className="mt-6 flex flex-wrap items-center gap-5 text-xs font-bold uppercase tracking-[0.08em]">
              <span>{formatPublicDate(featured.published_at, site.locale)}</span>
              <Link href={`/articles/${featured.slug}`} className="underline decoration-2 underline-offset-4">
                {SITE_PRESENTATION.publication_read_label}
              </Link>
            </div>
          </article>
        </section>
      ) : (
        <section className="border-b-2 border-black py-12 text-center">
          <h2 className="text-3xl font-black">La edición todavía no salió.</h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-stone-600">
            Southland no publica automáticamente: una historia llega a portada sólo después de evidencia, transformación editorial y aprobación humana.
          </p>
        </section>
      )}

      {remaining.length ? (
        <section className="py-9">
          <div className="section-kicker">{SITE_PRESENTATION.publication_section_label}</div>
          <div className="mt-6 grid gap-x-5 gap-y-8 md:grid-cols-2 lg:grid-cols-3">
            {remaining.slice(0, 8).map((item: any) => (
              <article key={item.article_id} className="border-b-2 border-black pb-6">
                {hasArticleVisual(item.slug) ? <ArticleVisual slug={item.slug} title={item.title} className="min-h-[14rem] border-2 border-black" /> : null}
                <p className="meta-line mt-4 font-bold">{item.topic}</p>
                <h3 className="southland-headline mt-2 text-2xl font-black leading-tight">
                  <Link href={`/articles/${item.slug}`} className="article-link">{item.title}</Link>
                </h3>
                <p className="mt-3 text-sm leading-6 text-stone-700">{item.summary}</p>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="grid gap-6 border-t-4 border-black pt-7 md:grid-cols-[1fr,0.65fr]">
        <div>
          <div className="eyebrow">La realidad debajo del pueblo</div>
          <h2 className="mt-2 text-3xl font-black">Fuentes reales, ficción marcada.</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-700">
            Cada artículo enlaza la fuente pública que sostiene el evento de partida. Southland puede literalizar una metáfora o exagerar un mecanismo, pero esa ficción se mantiene separada de la evidencia.
          </p>
        </div>
        <div className="border-2 border-black bg-white p-5">
          <p className="text-xs font-black uppercase tracking-[0.12em]">Cable de realidad</p>
          <p className="mt-2 text-sm leading-6 text-stone-700">
            El monitoreo subyacente sigue disponible como superficie separada y nunca se presenta como contenido propio.
          </p>
          <Link href="/latest" className="mt-4 inline-block text-xs font-black uppercase tracking-[0.08em] underline underline-offset-4">
            Ver señales monitoreadas →
          </Link>
        </div>
      </section>
    </main>
  );
}
