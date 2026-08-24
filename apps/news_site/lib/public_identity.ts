import identity from "../config/public_identity.json";

export const PUBLIC_IDENTITY = identity;

export function canonicalUrl(path = "/") {
  return new URL(path, PUBLIC_IDENTITY.public_outlet_url).toString();
}
