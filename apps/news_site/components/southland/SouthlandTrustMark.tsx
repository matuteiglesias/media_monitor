import Link from "next/link";

export function SouthlandTrustMark() {
  return (
    <aside className="st-trust-mark" aria-label="Política editorial de Southland Times">
      <strong>Fuentes reales / ficción marcada</strong>
      <span>Los hechos de partida enlazan evidencia pública; la narración de Southland Times es sátira.</span>
      <Link href="/methodology">Cómo funciona →</Link>
    </aside>
  );
}
