import Link from "next/link";
import { SouthlandStory } from "@/components/southland/SouthlandStory";
import { SouthlandTrustMark } from "@/components/southland/SouthlandTrustMark";

export function SouthlandHome({ outlet }: { outlet: any }) {
  const { site, publication, signals } = outlet;
  const featured = publication.featured;
  const remaining = publication.latest.filter(
    (item: any) => item.slug !== featured?.slug,
  );
  const rail = remaining.slice(0, 2);
  const grid = remaining.slice(2, 8);
  const wire = Array.isArray(signals.latest) ? signals.latest.slice(0, 5) : [];

  return (
    <main className="publication-shell southland-home pb-10 pt-4 sm:pt-5">
      {featured ? (
        <>
          <section className="st-front-grid" aria-label="Portada de la edición actual">
            <SouthlandStory story={featured} locale={site.locale} variant="lead" />
            <aside className="st-front-rail" aria-label="Más historias principales">
              {rail.length ? (
                rail.map((item: any) => (
                  <SouthlandStory
                    key={item.article_id}
                    story={item}
                    locale={site.locale}
                    variant="rail"
                  />
                ))
              ) : (
                <div className="st-rail-note">
                  <p className="st-kicker">Edición en curso</p>
                  <p>La portada crece sólo con historias aprobadas por la mesa editorial.</p>
                </div>
              )}
            </aside>
          </section>

          {grid.length ? (
            <section className="st-story-band" aria-label="Más de la edición">
              {grid.map((item: any) => (
                <SouthlandStory
                  key={item.article_id}
                  story={item}
                  locale={site.locale}
                  variant="grid"
                />
              ))}
            </section>
          ) : null}
        </>
      ) : (
        <section className="st-preissue" aria-label="Primera edición en preparación">
          <p className="st-kicker">Primera edición</p>
          <div className="st-preissue-grid">
            <h1>En preparación.</h1>
            <p>
              Southland Times no rellena la portada automáticamente. La primera edición aparece cuando
              una historia pasa evidencia, transformación editorial y aprobación humana.
            </p>
          </div>
        </section>
      )}

      <SouthlandTrustMark />

      {wire.length ? (
        <section className="st-reality-wire" aria-labelledby="reality-wire-heading">
          <div className="st-wire-header">
            <div>
              <p className="st-kicker">Cable de realidad</p>
              <h2 id="reality-wire-heading">Lo que está pasando afuera de Southland</h2>
            </div>
            <Link href="/latest">Ver todo el cable →</Link>
          </div>
          <div className="st-wire-grid">
            {wire.map((item: any, index: number) => (
              <article key={item.index_id} className="st-wire-item">
                <span className="st-wire-number">{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <p className="st-wire-meta">Fuente externa · {item.source} · {item.topic}</p>
                  <h3>
                    <Link href={`/story/${item.index_id}`} className="story-link">
                      {item.title}
                    </Link>
                  </h3>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </main>
  );
}
