import Link from "next/link";
import { loadOutlet } from "@/lib/adapter/mappers";
import { EDITORIAL_IDENTITY, pressMailto } from "@/lib/editorial_identity";

export default function JournalistsPage() {
  const editor = EDITORIAL_IDENTITY.editor;
  const outlet = loadOutlet();
  const latestAnalysis = outlet.publication.latest.slice(0, 3);

  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">Para periodistas y productores</p>
      <h1 className="mt-3 text-4xl font-semibold">Contacto y contexto económico</h1>
      <p className="mt-5 text-xl leading-8 text-neutral-700">
        {editor.name} · economista (PhD), editor de Media Monitor y profesional de datos e IA en Buenos Aires.
      </p>
      <p className="mt-4 max-w-3xl leading-7 text-neutral-700">
        Para entrevistas, chequeos de contexto, preparación de segmentos o consultas sobre datos económicos argentinos, el canal directo es el correo indicado abajo. El contacto no implica disponibilidad inmediata, pero evita intermediarios y deja clara la temática de la consulta.
      </p>

      <section className="mt-10 border p-6">
        <h2 className="text-2xl font-semibold">Contacto directo</h2>
        <p className="mt-3 text-neutral-700">{editor.contact.email}</p>
        <a
          href={pressMailto("Consulta periodística / producción — Media Monitor")}
          className="mt-5 inline-block border border-neutral-900 px-4 py-2 text-sm font-medium"
        >
          Escribir por una consulta periodística
        </a>
      </section>

      <section className="mt-10 border-t pt-8">
        <h2 className="text-2xl font-semibold">Áreas en las que puede aportar contexto</h2>
        <ul className="mt-5 grid gap-3 md:grid-cols-2">
          {editor.expertise.map((item) => (
            <li key={item} className="border p-4 text-sm text-neutral-700">{item}</li>
          ))}
        </ul>
        <p className="mt-5 text-sm leading-6 text-neutral-600">
          El foco es interpretación de evidencia, lectura de indicadores, calidad de fuentes y métodos reproducibles. Media Monitor no presenta una señal monitoreada como posición editorial propia.
        </p>
      </section>

      <section className="mt-10 border-t pt-8">
        <h2 className="text-2xl font-semibold">Análisis editorial reciente</h2>
        {latestAnalysis.length ? (
          <div className="mt-5 space-y-4">
            {latestAnalysis.map((article: any) => (
              <article key={article.article_id} className="border-b pb-4">
                <p className="text-xs uppercase tracking-[0.12em] text-neutral-500">{article.topic}</p>
                <Link href={`/articles/${article.slug}`} className="mt-1 block text-lg font-medium underline-offset-4 hover:underline">
                  {article.title}
                </Link>
                <p className="mt-2 text-sm text-neutral-600">{article.summary}</p>
              </article>
            ))}
          </div>
        ) : (
          <p className="mt-4 border-l-4 border-neutral-300 pl-4 text-sm leading-6 text-neutral-600">
            No hay análisis editorial human-approved disponible en este snapshot. Las señales monitoreadas de terceros no se usan como sustituto de una pieza propia.
          </p>
        )}
      </section>

      <section className="mt-10 border-t pt-8">
        <h2 className="text-2xl font-semibold">Identidad profesional</h2>
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          <a href={editor.contact.website} className="underline">Sitio profesional</a>
          <a href={editor.contact.linkedin} className="underline">LinkedIn</a>
          <a href={editor.contact.github} className="underline">GitHub</a>
          <Link href={EDITORIAL_IDENTITY.routes.about} className="underline">Quién lo hace</Link>
          <Link href={EDITORIAL_IDENTITY.routes.methodology} className="underline">Metodología editorial</Link>
        </div>
      </section>
    </main>
  );
}
