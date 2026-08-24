import Link from "next/link";
import { EDITORIAL_IDENTITY, pressMailto } from "@/lib/editorial_identity";

export function SiteHeader() {
  const routes = EDITORIAL_IDENTITY.routes;
  return (
    <header className="border-b bg-white">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4">
        <div>
          <Link href="/" className="font-semibold">{EDITORIAL_IDENTITY.outlet_name}</Link>
          <p className="mt-1 text-xs text-neutral-500">{EDITORIAL_IDENTITY.endorsement_line}</p>
        </div>
        <nav aria-label="Navegación editorial" className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
          <Link href={routes.about} className="underline-offset-4 hover:underline">Quién lo hace</Link>
          <Link href={routes.methodology} className="underline-offset-4 hover:underline">Metodología</Link>
          <Link href={routes.journalists} className="underline-offset-4 hover:underline">Para periodistas</Link>
          <a href={pressMailto()} className="underline-offset-4 hover:underline">Contacto</a>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  const editor = EDITORIAL_IDENTITY.editor;
  const routes = EDITORIAL_IDENTITY.routes;
  return (
    <footer className="mt-16 border-t bg-neutral-50">
      <div className="mx-auto grid max-w-6xl gap-6 px-6 py-10 md:grid-cols-[2fr,1fr]">
        <div>
          <p className="font-semibold">{EDITORIAL_IDENTITY.outlet_name}</p>
          <p className="mt-2 max-w-2xl text-sm text-neutral-600">{EDITORIAL_IDENTITY.endorsement_line}</p>
          <p className="mt-2 text-sm text-neutral-600">Editor: {editor.name} · {editor.location}</p>
        </div>
        <div className="space-y-2 text-sm">
          <p><Link href={routes.about} className="underline">Quién lo hace</Link></p>
          <p><Link href={routes.methodology} className="underline">Cómo se produce</Link></p>
          <p><Link href={routes.journalists} className="underline">Para periodistas y productores</Link></p>
          <p><a href={pressMailto()} className="underline">{editor.contact.email}</a></p>
        </div>
      </div>
    </footer>
  );
}
