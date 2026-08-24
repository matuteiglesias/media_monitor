import { NextRequest, NextResponse } from "next/server";
import identity from "./config/public_identity.json";

export function middleware(request: NextRequest) {
  if (process.env.CANONICAL_OWNED_DOMAIN_ACTIVE !== "1") return NextResponse.next();

  const host = request.nextUrl.hostname.toLowerCase();
  const owned = new URL(identity.owned_outlet_url);
  const legacyHosts = new Set(identity.legacy_outlet_urls.map((value) => new URL(value).hostname.toLowerCase()));

  if (!legacyHosts.has(host) || host === owned.hostname.toLowerCase()) return NextResponse.next();

  const target = new URL(request.nextUrl.pathname + request.nextUrl.search, owned);
  return NextResponse.redirect(target, 308);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
