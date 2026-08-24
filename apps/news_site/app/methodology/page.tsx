import Link from "next/link";
import { EDITORIAL_IDENTITY, pressMailto } from "@/lib/editorial_identity";

export default function MethodologyPage() {
  const editor = EDITORIAL_IDENTITY.editor;
  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">Metodología editorial</p>
      <h1 className="mt-3 text-4xl font-semibold">Cómo se produce Media Monitor</h1>
      <p className="mt-5 text-lg leading-8 text-neutral-700">
        La regla central es simple: monitorear no es publicar, generar un borrador no es aprobarlo y una pieza editorial sólo es pública cuando atravesó la frontera humana de publicación.
      </p>

      <section className="mt-10 border-t pt-8">
        <h2 className="text-2xl font-semibold">El recorrido</h2>
        <ol className="mt-5 space-y-5 text-neutral-700">
          <li><strong>1. Fuentes y monitoreo.</strong> El sistema adquiere referencias de fuentes externas y conserva identidad, tiempo, enlace y procedencia.</li>
          <li><strong>2. Artefactos e índices.</strong> Las corridas y proyecciones se materializan en contratos versionados e índices deterministas antes de llegar a la web.</li>
          <li><strong>3. Asistencia editorial.</strong> Herramientas automáticas y modelos pueden ayudar a preparar briefs y borradores. Ese material sigue siendo pre-publicación.</li>
          <li><strong>4. Revisión humana.</strong> La promoción a <code>published_article.v1</code> requiere una aprobación humana explícita.</li>
          <li><strong>5. Publicación.</strong> La web consume un snapshot versionado que mantiene separados los artículos aprobados y las señales externas monitoreadas.</li>
        </ol>
      </section>

      <section className="mt-10 border-t pt-8">
        <h2 className="text-2xl font-semibold">Qué significa cada etiqueta</h2>
        <div className="mt-5 space-y-5">
          <div className="border-l-4 border-neutral-300 pl-4">
            <h3 className="font-semibold">Señal monitoreada · fuente externa</h3>
            <p className="mt-2 text-sm leading-6 text-neutral-700">Es una referencia detectada por el sistema. No es una nota ni una interpretación de Media Monitor.</p>
          </div>
          <div className="border-l-4 border-neutral-300 pl-4">
            <h3 className="font-semibold">Brief o borrador generado</h3>
            <p className="mt-2 text-sm leading-6 text-neutral-700">Es material interno de trabajo. Puede contener síntesis o redacción asistida y no tiene autoridad pública por sí mismo.</p>
          </div>
          <div className="border-l-4 border-neutral-900 pl-4">
            <h3 className="font-semibold">Análisis editorial · aprobado</h3>
            <p className="mt-2 text-sm leading-6 text-neutral-700">Es contenido propio que atravesó la revisión y promoción humana de la publicación y conserva sus fuentes y citas disponibles.</p>
          </div>
        </div>
      </section>

      <section className="mt-10 border-t pt-8">
        <h2 className="text-2xl font-semibold">Fuentes, citas y correcciones</h2>
        <p className="mt-4 leading-7 text-neutral-700">
          Los artículos aprobados pueden conservar enlaces de fuente y citas estructuradas vinculadas con afirmaciones concretas. Las señales externas mantienen el enlace a la publicación original y no se reproducen como contenido propio.
        </p>
        <p className="mt-4 leading-7 text-neutral-700">
          Para señalar un error factual, aportar una fuente mejor o pedir una aclaración metodológica, escribir a {editor.name}. Una pieza corregida puede reflejar la revisión mediante su fecha de actualización y su superficie de evidencia.
        </p>
        <a href={pressMailto("Corrección o consulta metodológica — Media Monitor")} className="mt-5 inline-block text-sm font-medium underline">
          Enviar corrección o consulta
        </a>
      </section>

      <section className="mt-10 border-t pt-8">
        <h2 className="text-2xl font-semibold">Uso de automatización e IA</h2>
        <p className="mt-4 leading-7 text-neutral-700">
          Media Monitor usa automatización para adquisición, estructuración, enriquecimiento, preparación editorial y despliegue. La asistencia de IA puede intervenir antes de la publicación, pero no sustituye la aprobación humana ni convierte por sí sola una salida generada en una afirmación editorial del medio.
        </p>
      </section>

      <div className="mt-10 flex flex-wrap gap-4 border-t pt-8 text-sm">
        <Link href={EDITORIAL_IDENTITY.routes.about} className="underline">Quién lo hace</Link>
        <Link href={EDITORIAL_IDENTITY.routes.journalists} className="underline">Para periodistas y productores</Link>
        <Link href="/" className="underline">Volver a la portada</Link>
      </div>
    </main>
  );
}
