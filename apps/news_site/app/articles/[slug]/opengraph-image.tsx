import { ImageResponse } from "next/og";
import socialCards from "../../../public/data/article_social_cards.json";
import { EDITORIAL_IDENTITY } from "@/lib/editorial_identity";
import { PUBLIC_IDENTITY } from "@/lib/public_identity";

export const runtime = "edge";
export const alt = "Media Monitor — análisis económico de Argentina";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

type SocialCard = { title: string; topic: string };
type SocialCardIndex = { schema_name: "article_social_cards.v1"; articles: Record<string, SocialCard> };

const SOCIAL_CARDS = socialCards as SocialCardIndex;

export default function OpenGraphImage({ params }: { params: { slug: string } }) {
  const article = SOCIAL_CARDS.articles[params.slug];
  const title = article?.title ?? PUBLIC_IDENTITY.outlet_name;
  const topic = article?.topic ?? "Análisis económico de Argentina";

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          background: "white",
          color: "#111",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "22px" }}>
          <div style={{ fontSize: 28, letterSpacing: "0.08em", textTransform: "uppercase" }}>
            {PUBLIC_IDENTITY.outlet_name} · análisis aprobado
          </div>
          <div style={{ fontSize: 58, fontWeight: 700, lineHeight: 1.08, maxWidth: "1050px" }}>
            {title}
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", fontSize: 26 }}>
          <div>{topic}</div>
          <div>Por {EDITORIAL_IDENTITY.editor.name}</div>
        </div>
      </div>
    ),
    size,
  );
}
