import Link from "next/link";
import type { Metadata } from "next";
import { loadOutlet } from "@/lib/adapter/mappers";
import { formatPublicDate } from "@/lib/format";

export const metadata: Metadata = {
  title: "Archivo | Southland Times",
};

function monthKey(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Sin fecha";
  return new Intl.DateTimeFormat("es-AR", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export default function ArchivePage() {
  const outlet = loadOutlet();
  const groups = new Map<string, any[]>();

  for (const story of outlet.publication.latest) {
    const key = monthKey(story.published_at);
    groups.set(key, [...(groups.get(key) ?? []), story]);
  }

  return (
    <main className="publication-shell st-archive-page">
      <header className="st-page-heading">
        <p className="st-kicker">Archivo</p>
        <h1>Ediciones publicadas</h1>
        <p>Historias que ya pasaron por la mesa editorial de Southland Times.</p>
      </header>

      {groups.size ? (
        <div className="st-archive-groups">
          {[...groups.entries()].map(([label, stories]) => (
            <section key={label} className="st-archive-group">
              <h2>{label}</h2>
              <div>
                {stories.map((story: any) => (
                  <article key={story.article_id} className="st-archive-row">
                    <span>{formatPublicDate(story.published_at, outlet.site.locale)}</span>
                    <div>
                      <p>{story.topic}</p>
                      <h3>
                        <Link href={`/articles/${story.slug}`} className="article-link">
                          {story.title}
                        </Link>
                      </h3>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <section className="st-section-empty">
          <h2>El archivo empieza con la primera edición.</h2>
          <p>Por ahora no hay artículos de Southland Times publicados en este snapshot.</p>
          <Link href="/">Volver a portada →</Link>
        </section>
      )}
    </main>
  );
}
