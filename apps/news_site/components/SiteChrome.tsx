import Link from "next/link";
import { EDITORIAL_IDENTITY, pressMailto } from "@/lib/editorial_identity";
import { SITE_PRESENTATION } from "@/lib/site_presentation";

export function SiteHeader() {
  const routes = EDITORIAL_IDENTITY.routes;
  const publication = SITE_PRESENTATION.mode === "publication";
  return (
    <header className={publication ? "border-b-2 border-black bg-[#f6edcf]" : "border-b border-stone-300 bg-[#fffdf8]"}>
      <div className="publication-shell">
        <div className={publication
          ? "flex items-center justify-between gap-4 border-b border-black/20 py-2 text-[0.68rem] font-black uppercase tracking-[0.14em] text-stone-700"
          : "flex items-center justify-between gap-4 border-b border-stone-200 py-2 text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-stone-500"
        }>
          <span>{SITE_PRESENTATION.header_kicker}</span>
          <span className="hidden sm:inline">{SITE_PRESENTATION.location_label}</span>
        </div>
        <div className="flex flex-wrap items-end justify-between gap-5 py-5">
          <div>
            <Link href="/" className={publication
              ? "text-4xl font-black uppercase tracking-[-0.04em] sm:text-5xl"
              : "editorial-serif text-3xl font-bold tracking-tight sm:text-4xl"
            }>
              {EDITORIAL_IDENTITY.outlet_name}
            </Link>
            <p className="mt-1 text-xs font-medium text-stone-600">
              {EDITORIAL_IDENTITY.endorsement_line}
            </p>
          </div>
          <nav aria-label="Navegación editorial" className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs font-semibold uppercase tracking-[0.06em] text-stone-700">
            <Link href={routes.about} className="underline-offset-4 hover:underline">Quién lo hace</Link>
            <Link href={routes.methodology} className="underline-offset-4 hover:underline">Metodología</Link>
            {publication ? (
              <Link href="/latest" className="underline-offset-4 hover:underline">Fuentes reales</Link>
            ) : (
              <Link href={routes.journalists} className="underline-offset-4 hover:underline">Para periodistas</Link>
            )}
            <a href={pressMailto(publication ? "Consulta sobre Southland" : undefined)} className="press-cta">Contacto</a>
          </nav>
        </div>
      </div>
    </header>
  );
}

export function SiteFooter() {
  const editor = EDITORIAL_IDENTITY.editor;
  const routes = EDITORIAL_IDENTITY.routes;
  const publication = SITE_PRESENTATION.mode === "publication";
  return (
    <footer className={publication ? "mt-20 border-t-4 border-black bg-[#171714] text-stone-100" : "mt-20 border-t border-stone-300 bg-[#20201c] text-stone-100"}>
      <div className="publication-shell grid gap-8 py-12 md:grid-cols-[2fr,1fr]">
        <div>
          <p className={publication ? "text-3xl font-black uppercase tracking-tight" : "editorial-serif text-2xl font-semibold"}>{EDITORIAL_IDENTITY.outlet_name}</p>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-300">{EDITORIAL_IDENTITY.endorsement_line}</p>
          <p className="mt-3 text-sm text-stone-400">
            Editor: <Link href={routes.author} className="underline underline-offset-4">{editor.name}</Link> · {editor.location}
          </p>
          <p className="mt-5 max-w-2xl text-xs leading-5 text-stone-500">
            {SITE_PRESENTATION.disclosure_short}
          </p>
        </div>
        <div className="space-y-2 text-sm text-stone-300">
          <p><Link href={routes.author} className="hover:text-white hover:underline">Editor: {editor.name}</Link></p>
          <p><Link href={routes.about} className="hover:text-white hover:underline">Quién lo hace</Link></p>
          <p><Link href={routes.methodology} className="hover:text-white hover:underline">Cómo se produce</Link></p>
          <p><Link href="/latest" className="hover:text-white hover:underline">{publication ? "Fuentes reales" : "Señales monitoreadas"}</Link></p>
          <p><a href={pressMailto()} className="hover:text-white hover:underline">{editor.contact.email}</a></p>
        </div>
      </div>
    </footer>
  );
}
