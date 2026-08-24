import type { MetadataRoute } from "next";
import { canonicalUrl } from "@/lib/seo";
import { PUBLIC_IDENTITY } from "@/lib/public_identity";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/"],
    },
    sitemap: canonicalUrl("/sitemap.xml"),
    host: PUBLIC_IDENTITY.public_outlet_url,
  };
}
