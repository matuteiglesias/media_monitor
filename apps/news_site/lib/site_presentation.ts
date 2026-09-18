import presentation from "../config/site_presentation.json";

export const SITE_PRESENTATION = Object.freeze(presentation);

export function isPublicationMode() {
  return SITE_PRESENTATION.mode === "publication";
}
