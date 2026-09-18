import { ImageResponse } from "next/og";
import socialCards from "../../../public/data/article_social_cards.json";
import { EDITORIAL_IDENTITY } from "@/lib/editorial_identity";
import { PUBLIC_IDENTITY } from "@/lib/public_identity";
import { SITE_PRESENTATION } from "@/lib/site_presentation";

export const runtime = "edge";
export const alt = PUBLIC_IDENTITY.outlet_tagline;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

type SocialCard = { title: string; topic: string };
type SocialCardIndex = { schema_name: "article_social_cards.v1"; articles: Record<string, SocialCard> };
const SOCIAL_CARDS = socialCards as SocialCardIndex;

export default function OpenGraphImage({ params }: { params: { slug: string } }) {
  const article = SOCIAL_CARDS.articles[params.slug];
  const title = article?.title ?? PUBLIC_IDENTITY.outlet_name;
  const topic = article?.topic ?? PUBLIC_IDENTITY.outlet_tagline;
  const publication = SITE_PRESENTATION.mode === "publication";

  return new ImageResponse(
    (
      <div style={{
        width: "100%", height: "100%", display: "flex", flexDirection: "column",
        justifyContent: "space-between", padding: "72px",
        background: publication ? "#f6edcf" : "white", color: "#111", fontFamily: "sans-serif",
        border: publication ? "18px solid #111" : "none",
      }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "22px" }}>
          <div style={{ fontSize: 28, letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 800 }}>
            {PUBLIC_IDENTITY.outlet_name} · {publication ? "ficción satírica" : "análisis aprobado"}
          </div>
          <div style={{ fontSize: publication ? 64 : 58, fontWeight: 800, lineHeight: 1.04, maxWidth: "1050px" }}>
            {title}
          </div>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", fontSize: 26 }}>
          <div>{topic}</div>
          <div>{publication ? "Fuentes reales · ficción marcada" : `Por ${EDITORIAL_IDENTITY.editor.name}`}</div>
        </div>
      </div>
    ),
    size,
  );
}
