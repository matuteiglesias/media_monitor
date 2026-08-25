import Link from "next/link";

export function OutletPulse({
  curatedCount,
  latestCount,
  topicCount,
}: {
  curatedCount: number;
  latestCount: number;
  topicCount: number;
}) {
  return (
    <div className="outlet-pulse" aria-label="Estado del monitoreo">
      <div>
        <strong>{curatedCount}</strong>
        <span>señales priorizadas</span>
      </div>
      <div>
        <strong>{latestCount}</strong>
        <span>últimas señales</span>
      </div>
      <div>
        <strong>{topicCount}</strong>
        <span>temas activos</span>
      </div>
      <Link href="/methodology">Cómo se elige</Link>
    </div>
  );
}
