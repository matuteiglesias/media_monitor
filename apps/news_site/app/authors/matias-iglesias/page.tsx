import Link from "next/link";
import { EDITORIAL_IDENTITY, pressMailto } from "@/lib/editorial_identity";
import { authorMetadata, personJsonLd, serializeJsonLd } from "@/lib/seo";

export const metadata = authorMetadata();

export default function AuthorPage() {
  const editor = EDITORIAL_IDENTITY.editor;
  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(personJsonLd()) }}
      />
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-500">Autor y editor</p>
      <h1 className="mt-3 text-4xl font-semibold">{editor.name}</h1>
      <p className="mt-3 text-xl text-neutral-700">Economista · {EDITORIAL_IDENTITY.outlet_name}</p>
      <p className="mt-6 max-w-3xl leading-7 text-neutral-700">{editor.bio_short}</p>

      <section className="mt-10 grid gap-8 md:grid-cols-2">
        <div>
          <h2 className="text-xl font-semibold">Áreas de trabajo</h2>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-neutral-700">
            {editor.expertise.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
        <div>
          <h2 className="text-xl font-semibold">Credenciales</h2>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-neutral-700">
            {editor.credentials.map((item) => <li key={item}>{item}</li>)}
          </ul>
          <p className="mt-4 text-sm text-neutral-600">{editor.location}</p>
        </div>
      </section>

      <section className="mt-10 border-t pt-8">
        <h2 className="text-xl font-semibold">Contacto e identidad profesional</h2>
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          <a className="underline" href={pressMailto("Consulta periodística — Media Monitor")}>Email</a>
          <a className="underline" href={editor.contact.website}>Sitio personal</a>
          <a className="underline" href={editor.contact.linkedin}>LinkedIn</a>
          <a className="underline" href={editor.contact.github}>GitHub</a>
        </div>
      </section>

      <p className="mt-10 text-sm text-neutral-600">
        <Link href={EDITORIAL_IDENTITY.routes.journalists} className="underline">Información para periodistas y productores</Link>
        {" · "}
        <Link href={EDITORIAL_IDENTITY.routes.methodology} className="underline">Metodología editorial</Link>
      </p>
    </main>
  );
}
