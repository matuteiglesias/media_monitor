import Link from "next/link";
import { EDITORIAL_IDENTITY, pressMailto } from "@/lib/editorial_identity";

export default function AboutPage() {
  const { editor, routes } = EDITORIAL_IDENTITY;
  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">Quién lo hace</p>
      <h1 className="mt-3 text-4xl font-semibold">Media Monitor y su editor</h1>
      <p className="mt-5 text-xl leading-8 text-neutral-700">{EDITORIAL_IDENTITY.endorsement_line}</p>

      <section className="mt-10 border-t pt-8">
        <h2 className="text-2xl font-semibold">Qué es Media Monitor</h2>
        <p className="mt-4 leading-7 text-neutral-700">
          Media Monitor es un sistema de monitoreo y publicación orientado a la economía argentina. Mantiene separadas dos capas públicas: señales detectadas en fuentes externas y análisis editorial propio que atravesó una aprobación humana explícita.
        </p>
        <p className="mt-4 leading-7 text-neutral-700">
          La automatización ayuda a adquirir, ordenar, enriquecer y preparar material. No reemplaza la autoridad editorial: un titular monitoreado o un borrador generado no se presenta como análisis de Media Monitor.
        </p>
      </section>

      <section className="mt-10 border-t pt-8">
        <h2 className="text-2xl font-semibold">{editor.name}</h2>
        <p className="mt-2 text-sm font-medium text-neutral-600">{editor.role} · {editor.location}</p>
        <p className="mt-4 leading-7 text-neutral-700">{editor.bio_short}</p>
        <div className="mt-6 grid gap-8 md:grid-cols-2">
          <div>
            <h3 className="font-semibold">Formación</h3>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-neutral-700">
              {editor.credentials.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
          <div>
            <h3 className="font-semibold">Áreas de trabajo</h3>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-neutral-700">
              {editor.expertise.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        </div>
        <div className="mt-6 flex flex-wrap gap-4 text-sm">
          <a href={editor.contact.website} className="underline">Sitio profesional</a>
          <a href={editor.contact.linkedin} className="underline">LinkedIn</a>
          <a href={editor.contact.github} className="underline">GitHub</a>
          <a href={pressMailto()} className="underline">Contacto</a>
        </div>
      </section>

      <section className="mt-10 border-t pt-8">
        <h2 className="text-2xl font-semibold">Qué no es</h2>
        <ul className="mt-4 list-disc space-y-3 pl-5 leading-7 text-neutral-700">
          <li>No es una redacción autónoma: la publicación editorial conserva una decisión humana explícita.</li>
          <li>No convierte automáticamente titulares de terceros en contenido propio.</li>
          <li>No usa una URL desplegada como prueba de actualidad: la frescura se expone por separado mediante el health público.</li>
        </ul>
      </section>

      <div className="mt-10 flex flex-wrap gap-4 border-t pt-8 text-sm">
        <Link href={routes.methodology} className="underline">Leer metodología editorial</Link>
        <Link href={routes.journalists} className="underline">Información para periodistas y productores</Link>
        <Link href="/" className="underline">Volver a la portada</Link>
      </div>
    </main>
  );
}
