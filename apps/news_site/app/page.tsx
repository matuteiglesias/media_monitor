import Link from "next/link";
import { loadFrontpage } from "@/lib/adapter/mappers";

export default function HomePage() {
  const data = loadFrontpage();

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <header className="border-b pb-6">
        <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
          Media Monitor
        </div>
        <h1 className="mt-2 text-4xl font-semibold">Portada</h1>
      </header>

      {data.hero ? (
        <section className="mt-8 border-b pb-8">
          <div className="text-sm text-neutral-500">{data.hero.source}</div>
          <h2 className="mt-2 text-3xl font-semibold">{data.hero.title}</h2>
          <p className="mt-2 text-sm text-neutral-600">{data.hero.published_at}</p>
          <a
            href={data.hero.link}
            className="mt-4 inline-block text-sm underline"
            target="_blank"
            rel="noreferrer"
          >
            Abrir fuente
          </a>
        </section>
      ) : (
        <section className="mt-8">No hay hero disponible.</section>
      )}

      <section className="mt-10 grid gap-8 lg:grid-cols-[2fr,1fr]">
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-xl font-semibold">Últimas</h3>
            <Link href="/latest" className="text-sm underline">
              Ver todo
            </Link>
          </div>

          <div className="space-y-6">
            {data.latest.map((item: any, idx: number) => (
              <article key={`${item.link}-${idx}`} className="border-b pb-4">
                <div className="text-xs text-neutral-500">{item.source}</div>
                <h4 className="mt-1 text-lg font-medium">{item.title}</h4>
                <div className="mt-1 text-sm text-neutral-600">{item.published_at}</div>
                <a
                  href={item.link}
                  className="mt-2 inline-block text-sm underline"
                  target="_blank"
                  rel="noreferrer"
                >
                  Fuente
                </a>
              </article>
            ))}
          </div>
        </div>

        <aside>
          <h3 className="mb-4 text-xl font-semibold">Grupos</h3>
          <div className="space-y-4">
            {data.groups.map((group: any, idx: number) => (
              <div key={`${group.topic}-${idx}`} className="border p-4">
                <div className="text-sm font-medium">{group.topic}</div>
                <div className="mt-1 text-sm text-neutral-600">
                  {group.article_count} artículos
                </div>
              </div>
            ))}
          </div>
        </aside>
      </section>
    </main>
  );
}
