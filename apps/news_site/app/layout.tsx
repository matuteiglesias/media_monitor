import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Media Monitor",
  description: "Semi-automated editorial outlet",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
