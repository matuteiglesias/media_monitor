import presentation from "../config/site_presentation.json";

export type PublicationSection = {
  slug: string;
  label: string;
  topics: string[];
};

export const SITE_PRESENTATION = Object.freeze(presentation) as Readonly<
  typeof presentation & {
    section_navigation?: PublicationSection[];
    preview_mode?: "prepared_issue";
    preview_label?: string;
    preview_digest_at?: string;
    preview_draft_count?: number;
  }
>;

export function isPublicationMode() {
  return SITE_PRESENTATION.mode === "publication";
}
