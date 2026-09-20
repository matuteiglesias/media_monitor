import presentation from "../config/site_presentation.json";

export type PublicationSection = {
  slug: string;
  label: string;
  topics: string[];
};

export const SITE_PRESENTATION = Object.freeze(presentation) as Readonly<
  typeof presentation & {
    section_navigation?: PublicationSection[];
  }
>;

export function isPublicationMode() {
  return SITE_PRESENTATION.mode === "publication";
}
