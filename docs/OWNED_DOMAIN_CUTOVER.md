# Owned-domain cutover

Target public identity: **https://media.matuteiglesias.link**

Current provider identity remains **https://mediamonitor-psi.vercel.app** until the owned host is actually bound and verified. The repository deliberately does not make the promise stronger than the reachable surface.

## Preconditions

1. Add `media.matuteiglesias.link` as a custom domain on the canonical Media Monitor Vercel project.
2. Configure DNS at the authoritative provider using the target Vercel records.
3. Wait until HTTPS terminates successfully on the owned hostname.
4. Run GitHub Actions workflow **Owned domain readiness** with confirmation `CHECK media.matuteiglesias.link`.

The readiness workflow verifies:

- the owned hostname resolves;
- the owned hostname serves `/api/health` successfully over HTTPS;
- owned and legacy hosts serve the same snapshot;
- the hostname is therefore safe to promote to canonical identity.

## Atomic activation

After readiness is green, set repository Actions variable:

```text
CANONICAL_OWNED_DOMAIN_ACTIVE=1
```

Then run/allow the normal **Scheduled public refresh**. The guarded production build receives this variable and:

- changes the canonical metadata/feeds/sitemap/health identity to the owned URL;
- enables permanent `308` redirects from the known legacy outlet host;
- runs the normal anonymous health check;
- runs the crawler/feed/social-card acceptance check against the new canonical URL.

Do **not** change `public_outlet_url` manually before this point. The runtime identity switch is intentionally one flag so partial migrations cannot leave some surfaces on one host and some on another.

## Rollback

Set:

```text
CANONICAL_OWNED_DOMAIN_ACTIVE=0
```

and run another production roll. Canonical identity returns to the provider host and legacy-host redirect middleware becomes inert.

## What is intentionally not automated

DNS mutation and Vercel custom-domain ownership are external control-plane actions. They are not performed from this repository because this environment has no authenticated Cloudflare/Vercel domain connector. The repository owns verification, activation semantics, canonical projection and rollback; DNS ownership remains an explicit operator action.
