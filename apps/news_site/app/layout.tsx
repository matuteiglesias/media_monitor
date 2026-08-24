import "./globals.css";
import type { Metadata } from "next";
import FreshnessNotice from "@/components/FreshnessNotice";
import { PUBLIC_IDENTITY } from "@/lib/public_identity";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  metadataBase: new URL(PUBLIC_IDENTITY.public_outlet_url),
  title: PUBLIC_IDENTITY.outlet_name,
  description: PUBLIC_IDENTITY.outlet_tagline,
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: PUBLIC_IDENTITY.outlet_name,
    description: PUBLIC_IDENTITY.outlet_tagline,
    url: "/",
    siteName: PUBLIC_IDENTITY.outlet_name,
    locale: "es_AR",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>
        <FreshnessNotice />
        {children}
      </body>
    </html>
  );
}
