import visuals from "../public/data/article_visuals.json";

type LegacyVisual = {
  kind: string;
  seed: number;
  palette: string[];
  alt: string;
};

type CuratedMatch = {
  asset_id: string;
  public_path: string;
  alt: string;
  created_at: string;
  matched_tags: string[];
  character_match_count: number;
  match_count: number;
};

type CuratedVisual = {
  kind: "curated_asset_matches";
  article_tags: string[];
  matches: CuratedMatch[];
};

type LegacyIndex = {
  schema_name: "article_visuals.v1";
  articles: Record<string, LegacyVisual>;
};

type CuratedIndex = {
  schema_name: "article_visuals.v2";
  articles: Record<string, CuratedVisual>;
};

const INDEX = visuals as unknown as LegacyIndex | CuratedIndex;

function positions(seed: number) {
  return {
    sunX: 12 + (seed % 58),
    hill: 34 + ((seed >> 4) % 25),
    figure: 18 + ((seed >> 9) % 62),
  };
}

function curatedMatch(slug: string, slot = 0): CuratedMatch | null {
  if (INDEX.schema_name !== "article_visuals.v2") return null;
  return INDEX.articles?.[slug]?.matches?.[slot] ?? null;
}

export function hasArticleVisual(slug: string, slot = 0) {
  if (INDEX.schema_name === "article_visuals.v2") {
    return Boolean(curatedMatch(slug, slot));
  }
  return Boolean(INDEX.articles?.[slug]);
}

export function ArticleVisual({
  slug,
  title,
  slot = 0,
  className = "",
}: {
  slug: string;
  title: string;
  slot?: number;
  className?: string;
}) {
  if (INDEX.schema_name === "article_visuals.v2") {
    const match = curatedMatch(slug, slot);
    if (!match) return null;
    return (
      <div className={`southland-visual relative overflow-hidden ${className}`}>
        <img
          src={match.public_path}
          alt={match.alt || `Ilustración de Southland para: ${title}`}
          className="absolute inset-0 h-full w-full object-cover"
        />
      </div>
    );
  }

  const visual = INDEX.articles[slug];
  if (!visual) return null;
  const palette = visual.palette ?? ["#f6d44a", "#e95d4f", "#2f6f68", "#f4efe2"];
  const seed = visual.seed ?? 17;
  const pos = positions(seed);

  return (
    <div
      className={`southland-visual relative overflow-hidden ${className}`}
      role="img"
      aria-label={visual.alt ?? `Ilustración editorial para: ${title}`}
      style={{ background: palette[3] }}
    >
      <div
        className="absolute rounded-full"
        style={{
          width: "22%",
          aspectRatio: "1",
          left: `${pos.sunX}%`,
          top: "9%",
          background: palette[0],
          transform: "rotate(-4deg)",
        }}
      />
      <div
        className="absolute left-[-8%] right-[-8%] bottom-[-18%] h-[58%]"
        style={{
          background: palette[2],
          clipPath: `polygon(0 42%, 18% ${pos.hill}%, 38% 48%, 59% 22%, 78% 44%, 100% 31%, 100% 100%, 0 100%)`,
        }}
      />
      <div
        className="absolute bottom-[12%] h-[36%] w-[13%]"
        style={{
          left: `${pos.figure}%`,
          background: palette[1],
          clipPath: "polygon(28% 0, 72% 0, 82% 22%, 100% 100%, 0 100%, 18% 22%)",
          transform: "rotate(2deg)",
        }}
      />
      <div
        className="absolute bottom-[38%] h-[14%] w-[14%] rounded-full"
        style={{
          left: `calc(${pos.figure}% - 0.5%)`,
          background: "#ead0ac",
          transform: "rotate(-3deg)",
        }}
      />
      <div className="absolute inset-x-4 bottom-3 flex justify-between gap-3 text-[0.58rem] font-black uppercase tracking-[0.18em] text-black/65">
        <span>Southland</span>
        <span>Ilustración original</span>
      </div>
    </div>
  );
}
