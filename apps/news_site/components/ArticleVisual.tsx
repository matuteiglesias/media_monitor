import visuals from "../public/data/article_visuals.json";

type Visual = {
  kind: string;
  seed: number;
  palette: string[];
  alt: string;
};

type VisualIndex = {
  schema_name: "article_visuals.v1";
  articles: Record<string, Visual>;
};

const INDEX = visuals as VisualIndex;

function positions(seed: number) {
  return {
    sunX: 12 + (seed % 58),
    hill: 34 + ((seed >> 4) % 25),
    figure: 18 + ((seed >> 9) % 62),
  };
}

export function ArticleVisual({
  slug,
  title,
  className = "",
}: {
  slug: string;
  title: string;
  className?: string;
}) {
  const visual = INDEX.articles[slug];
  const palette = visual?.palette ?? ["#f6d44a", "#e95d4f", "#2f6f68", "#f4efe2"];
  const seed = visual?.seed ?? 17;
  const pos = positions(seed);

  return (
    <div
      className={`southland-visual relative overflow-hidden ${className}`}
      role="img"
      aria-label={visual?.alt ?? `Ilustración editorial para: ${title}`}
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
