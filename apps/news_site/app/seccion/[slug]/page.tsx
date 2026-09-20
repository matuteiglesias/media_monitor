import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { loadOutlet } from "@/lib/adapter/mappers";
import { SITE_PRESENTATION } from "@/lib/site_presentation";
import { SouthlandStory } from "@/components/southland/SouthlandStory";

function sectionConfig(slug: string) {
  return (SITE_PRESENTATION.section_navigation ?? []).find(
    (section) => section.slug === slug && section.slug !== "archivo",
  );
}

export function generateMetadata({ params }: { params: { slug: string } }): Metadata {
  const section = sectionConfig(params.slug);
  if (!section) return { title: "Sección no encontrada | Southland Times", robots: { index: false } };
  return { title: `${section.label} | Southland Times` };
}

export default function SectionPage({ params }: { params: { slug: string } }) {
  const section = sectionConfig(params.slug);
  if (!section) notFound();

  const outlet = loadOutlet();
  const stories = outlet.publication.latest.filter((item: any) =>
    section.topics.includes(item.topic),
  );

  return (
    <main className="publication-shell st-section-page">
      <header className="st-page-heading st-section-heading">
        <p className="st-kicker">Sección</p>
        <h1>{section.label}</h1>
        <p>Historias publicadas por Southland Times dentro de esta sección editorial.</p>
      </header>

      {stories.length ? (
        <section className="st-section-grid">
          {stories.map((story: any) => (
            <SouthlandStory
              key={story.article_id}
              story={story}
              locale={outlet.site.locale}
              variant="grid"
            />
          ))}
        </section>
      ) : (
        <section className="st-section-empty">
          <h2>Todavía no hay historias publicadas acá.</h2>
          <p>La sección aparecerá cuando una pieza aprobada de Southland Times entre en esta categoría.</p>
          <Link href="/">Volver a portada →</Link>
        </section>
      )}
    </main>
  );
}
