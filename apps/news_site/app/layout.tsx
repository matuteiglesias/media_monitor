import "./globals.css";
import type { Metadata } from "next";
import FreshnessNotice from "@/components/FreshnessNotice";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Media Monitor",
  description: "Análisis editorial aprobado y monitoreo de señales de fuentes externas.",
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
