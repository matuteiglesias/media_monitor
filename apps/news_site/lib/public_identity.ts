import identity from "../config/public_identity.json";

const ownedDomainActive = process.env.CANONICAL_OWNED_DOMAIN_ACTIVE === "1";

export const PUBLIC_IDENTITY = Object.freeze({
  ...identity,
  public_outlet_url: ownedDomainActive ? identity.owned_outlet_url : identity.public_outlet_url,
  canonical_mode: ownedDomainActive ? "owned_domain" : "provider_host",
});

export function canonicalUrl(path = "/") {
  return new URL(path, PUBLIC_IDENTITY.public_outlet_url).toString();
}

export function isOwnedDomainActive() {
  return ownedDomainActive;
}
