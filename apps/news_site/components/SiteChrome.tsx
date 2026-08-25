import Link from "next/link";
import { EDITORIAL_IDENTITY, pressMailto } from "@/lib/editorial_identity";

export function SiteHeader() {
  const routes = EDITORIAL_IDENTITY.routes;
  return (
    <header className="border-b border-stone-300 bg-[#fffdf8]">
      <div className="publication-shell">
        <div className="flex items-center justify-between gap-4 border-b border-stone-200 py-2 text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-stone-500">
          <span>Economía argentina · monitoreo y análisis</span>
          <span className="hidden sm:inline">Buenos Aires</span>
        </div>
        <div className="flex flex-wrap items-end justify-between gap-5 py-5">
          <div>
            <Link href="/" className="editorial-serif text-3xl font-bold tracking-tight sm:text-4xl">
              {EDITORIAL_IDENTITY.outlet_name}
            </Link>
            <p className="mt-1 text-xs font-medium text-stone-600">
              {EDITORIAL_IDENTITY.endorsement_line}
            </p>
          </div>
          <nav aria-label="Navegación editorial" className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs font-semibold uppercase tracking-[0.06em] text-stone-700">
            <Link href={routes.about} className="underline-offset-4 hover:text-[#8d2b2b] hover:underline">Quién lo hace</Link>
            <Link href={routes.methodology} className="underline-offset-4 hover:text-[#8d2b2b] hover:underline">Metodología</Link>
            <Link href={routes.journalists} className="underline-offset-4 hover:text-[#8d2b2b] hover:underline">Para periodistas</Link>
            <a href={pressMailto()} className="press-cta">Contacto</a>
          </nav>
        </div>
      </div>
    </header>
  );
}

export function SiteFooter() {
  const editor = EDITORIAL_IDENTITY.editor;
  const routes = EDITORIAL_IDENTITY.routes;
  return (
    <footer className="mt-20 border-t border-stone-300 bg-[#20201c] text-stone-100">
      <div className="publication-shell grid gap-8 py-12 md:grid-cols-[2fr,1fr]">
        <div>
          <p className="editorial-serif text-2xl font-semibold">{EDITORIAL_IDENTITY.outlet_name}</p>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-300">{EDITORIAL_IDENTITY.endorsement_line}</p>
          <p className="mt-3 text-sm text-stone-400">
            Editor: <Link href={routes.author} className="underline underline-offset-4">{editor.name}</Link> · {editor.location}
          </p>
          <p className="mt-5 max-w-2xl text-xs leading-5 text-stone-500">
            Las señales monitoreadas provienen de fuentes externas. El análisis propio se publica únicamente después de aprobación humana explícita.
          </p>
        </div>
        <div className="space-y-2 text-sm text-stone-300">
          <p><Link href={routes.author} className="hover:text-white hover:underline">Autor: {editor.name}</Link></p>
          <p><Link href={routes.about} className="hover:text-white hover:underline">Quién lo hace</Link></p>
          <p><Link href={routes.methodology} className="hover:text-white hover:underline">Cómo se produce</Link></p>
          <p><Link href={routes.journalists} className="hover:text-white hover:underline">Para periodistas y productores</Link></p>
          <p><a href={pressMailto()} className="hover:text-white hover:underline">{editor.contact.email}</a></p>
        </div>
      </div>
    </footer>
  );
}
