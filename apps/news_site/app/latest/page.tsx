import Link from "next/link";
import { loadOutlet } from "@/lib/adapter/mappers";
import { SITE_PRESENTATION } from "@/lib/site_presentation";
import { formatPublicDate } from "@/lib/format";

export default function LatestPage() {
  const outlet = loadOutlet();

  if (SITE_PRESENTATION.theme === "southland") {
    return (
      <main className="publication-shell st-wire-page">
        <header className="st-page-heading">
          <p className="st-kicker">Cable de realidad</p>
          <h1>Señales de fuentes reales</h1>
          <p>
            Esta superficie reproduce titulares detectados en fuentes externas. No son artículos de Southland Times ni ficción propia.
          </p>
        </header>
        <div className="st-latest-list">
          {outlet.signals.latest.map((item: any, index: number) => (
            <article key={item.index_id} className="st-latest-row">
              <span className="st-latest-number">{String(index + 1).padStart(2, "0")}</span>
              <div>
                <p className="st-wire-meta">
                  Fuente externa · {item.source} · {item.topic} · {formatPublicDate(item.published_at, outlet.site.locale)}
                </p>
                <h2>
                  <Link href={`/story/${item.index_id}`} className="story-link">{item.title}</Link>
                </h2>
              </div>
            </article>
          ))}
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">
        Señales monitoreadas · fuentes externas
      </p>
      <h1 className="mt-2 text-3xl font-semibold">Señales recientes</h1>
      <p className="mt-2 max-w-3xl text-neutral-600">
        Titulares detectados por Media Monitor. Esta capa es monitoreo de fuentes,
        no análisis editorial propio.
      </p>
      <div className="mt-8 space-y-6">
        {outlet.signals.latest.map((item: any) => (
          <article key={item.index_id} className="border-b pb-4">
            <div className="text-xs uppercase tracking-[0.12em] text-neutral-500">
              Fuente externa · {item.source}
            </div>
            <Link href={`/story/${item.index_id}`} className="mt-1 block text-xl font-medium">
              {item.title}
            </Link>
            <div className="mt-1 text-sm text-neutral-600">
              {item.topic} · {item.published_at}
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}
