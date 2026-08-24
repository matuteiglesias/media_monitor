import identity from "../config/editorial_identity.json";

export const EDITORIAL_IDENTITY = identity;
export const EDITOR = identity.editor;

export function pressMailto(subject = "Consulta para Media Monitor") {
  const params = new URLSearchParams({ subject });
  return `mailto:${EDITOR.contact.email}?${params.toString()}`;
}
