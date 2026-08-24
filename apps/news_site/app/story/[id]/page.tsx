import { notFound } from "next/navigation";
import { findStory, loadOutlet } from "@/lib/adapter/mappers";

export default function StoryPage({ params }: { params: { id: string } }) {
  const item = findStory(params.id);
  if (!item) notFound();
  const outlet = loadOutlet();
  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">
        Señal monitoreada · fuente externa
      </p>
      <p className="mt-3 text-sm text-neutral-500">
        {outlet.site.name} · {item.topic} · {item.source}
      </p>
      <h1 className="mt-2 text-3xl font-semibold">{item.title}</h1>
      <p className="mt-2 text-sm text-neutral-600">{item.published_at}</p>
      <div className="mt-6 border-l-4 border-neutral-300 pl-4 text-sm text-neutral-600">
        Este registro es un titular detectado por el sistema de monitoreo y no es
        un artículo ni análisis editorial de Media Monitor. Consulte la fuente
        original para el contenido completo y su contexto.
      </div>
      <a
        className="mt-6 inline-block font-medium underline"
        href={item.link}
        target="_blank"
        rel="noreferrer"
      >
        Abrir fuente original
      </a>
    </main>
  );
}
