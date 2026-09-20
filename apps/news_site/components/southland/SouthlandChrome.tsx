import Link from "next/link";
import { EDITORIAL_IDENTITY } from "@/lib/editorial_identity";
import { SITE_PRESENTATION } from "@/lib/site_presentation";
import { loadOutlet } from "@/lib/adapter/mappers";
import { formatPublicDate } from "@/lib/format";

export function SouthlandHeader() {
  const routes = EDITORIAL_IDENTITY.routes;
  const outlet = loadOutlet();
  const editionDate = outlet.publication.featured?.published_at
    ? formatPublicDate(outlet.publication.featured.published_at, outlet.site.locale)
    : null;
  return (
    <header className="st-header">
      {SITE_PRESENTATION.preview_mode === "prepared_issue" ? (
        <div className="st-preview-banner" role="status">
          <strong>{SITE_PRESENTATION.preview_label ?? "BORRADORES IA · NO PUBLICADO"}</strong>
          <span>
            Digest {SITE_PRESENTATION.preview_digest_at} · {SITE_PRESENTATION.preview_draft_count ?? 0} piezas · vista previa local
          </span>
        </div>
      ) : null}
      <div className="st-shell">
        <div className="st-utility-bar">
          <span>Ficción satírica basada en hechos públicos</span>
          <nav aria-label="Navegación institucional">
            <Link href={routes.about}>Qué es</Link>
            <Link href={routes.methodology}>Método</Link>
            <Link href="/latest">Fuentes</Link>
          </nav>
        </div>

        <div className="st-masthead">
          <Link href="/" className="st-nameplate" aria-label="Southland Times, portada">
            {EDITORIAL_IDENTITY.outlet_name}
          </Link>
          <p className="st-tagline">Noticias de un país sospechosamente parecido al nuestro.</p>
          <div className="st-edition-line">
            <span>{SITE_PRESENTATION.location_label}</span>
            <span aria-hidden>·</span>
            <span>{editionDate ? `Edición actual · ${editionDate}` : "Primera edición en preparación"}</span>
            <span aria-hidden>·</span>
            <span className="st-trust-inline">Fuentes reales / ficción marcada</span>
          </div>
        </div>

        <nav className="st-section-nav" aria-label="Secciones de Southland Times">
          {(SITE_PRESENTATION.section_navigation ?? []).map((section: any) => (
            <Link
              key={section.slug}
              href={section.slug === "archivo" ? "/archivo" : `/seccion/${section.slug}`}
            >
              {section.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}

export function SouthlandFooter() {
  const editor = EDITORIAL_IDENTITY.editor;
  const routes = EDITORIAL_IDENTITY.routes;
  return (
    <footer className="st-footer">
      <div className="st-shell st-footer-inner">
        <div>
          <Link href="/" className="st-footer-name">{EDITORIAL_IDENTITY.outlet_name}</Link>
          <p className="st-footer-line">
            Noticias de un país sospechosamente parecido al nuestro.
          </p>
          <p className="st-footer-meta">
            Editor: <Link href={routes.author}>{editor.name}</Link> · {editor.location}
          </p>
        </div>
        <nav aria-label="Información de Southland Times" className="st-footer-nav">
          <Link href={routes.about}>Qué es</Link>
          <Link href={routes.methodology}>Método</Link>
          <Link href="/latest">Fuentes reales</Link>
          <a href={`mailto:${editor.contact.email}`}>Contacto</a>
        </nav>
      </div>
      <div className="st-shell st-footer-disclosure">
        Ficción satírica basada en hechos públicos. Las fuentes del evento real se enlazan de forma explícita.
      </div>
    </footer>
  );
}
