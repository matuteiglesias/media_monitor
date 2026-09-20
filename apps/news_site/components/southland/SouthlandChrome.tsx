import Link from "next/link";
import { EDITORIAL_IDENTITY } from "@/lib/editorial_identity";
import { SITE_PRESENTATION } from "@/lib/site_presentation";

const sections = ["Política", "Economía", "Provincias", "Sociedad", "Archivo"];

export function SouthlandHeader() {
  const routes = EDITORIAL_IDENTITY.routes;
  return (
    <header className="st-header">
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
            <span>Edición actual</span>
            <span aria-hidden>·</span>
            <span className="st-trust-inline">Fuentes reales / ficción marcada</span>
          </div>
        </div>

        <nav className="st-section-nav" aria-label="Secciones de Southland Times">
          {sections.map((section) => (
            <span key={section}>{section}</span>
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
