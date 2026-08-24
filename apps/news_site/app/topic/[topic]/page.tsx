import Link from "next/link";
import { loadOutlet } from "@/lib/adapter/mappers";

export default function TopicPage({ params }: { params: { topic: string } }) {
  const outlet = loadOutlet();
  const topic = decodeURIComponent(params.topic);
  const items = outlet.signals.latest.filter((item: any) => item.topic === topic);
  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">
        Señales monitoreadas · fuentes externas
      </p>
      <h1 className="mt-2 text-3xl font-semibold">{topic}</h1>
      <p className="mt-2 text-neutral-600">
        Cobertura detectada por {outlet.site.name}; no constituye análisis editorial propio.
      </p>
      <div className="mt-8 space-y-4">
        {items.map((item: any) => (
          <article key={item.index_id} className="border-b pb-4">
            <div className="text-xs text-neutral-500">Fuente externa · {item.source}</div>
            <Link className="mt-1 block text-lg font-medium" href={`/story/${item.index_id}`}>
              {item.title}
            </Link>
          </article>
        ))}
      </div>
    </main>
  );
}
