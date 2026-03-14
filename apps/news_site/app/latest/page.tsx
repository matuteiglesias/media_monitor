import { loadFrontpage } from "@/lib/adapter/mappers";

export default function LatestPage() {
  const data = loadFrontpage();

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-3xl font-semibold">Últimas noticias</h1>
      <div className="mt-8 space-y-6">
        {data.latest.map((item: any, idx: number) => (
          <article key={`${item.link}-${idx}`} className="border-b pb-4">
            <div className="text-xs text-neutral-500">{item.source}</div>
            <h2 className="mt-1 text-xl font-medium">{item.title}</h2>
            <div className="mt-1 text-sm text-neutral-600">{item.published_at}</div>
            <a href={item.link} target="_blank" rel="noreferrer" className="mt-2 inline-block text-sm underline">
              Abrir fuente
            </a>
          </article>
        ))}
      </div>
    </main>
  );
}
