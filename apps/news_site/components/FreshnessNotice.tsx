import { loadSiteSnapshot } from "@/lib/adapter/loaders";
import {
  buildPublicationHealth,
  freshnessLead,
} from "@/lib/publication_health.mjs";

function formattedTimestamp(value: string) {
  return new Intl.DateTimeFormat("es-AR", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "America/Argentina/Buenos_Aires",
  }).format(new Date(value));
}

export default function FreshnessNotice() {
  const health = buildPublicationHealth(loadSiteSnapshot());
  const updated = formattedTimestamp(health.newest_item_at);
  const lead = freshnessLead(health);
  const current = health.freshness_status === "FRESH" && health.within_target;
  const message = current
    ? `${lead} ${updated}.`
    : `${lead}. Última señal: ${updated}.`;

  return (
    <div
      data-publication-health={health.freshness_status}
      role="status"
      className={current
        ? "border-b border-stone-800 bg-[#20201c] px-4 py-2 text-center text-[0.68rem] font-semibold uppercase tracking-[0.08em] text-stone-200"
        : "border-b border-[#c39186] bg-[#f0dfda] px-4 py-2 text-center text-[0.68rem] font-semibold uppercase tracking-[0.08em] text-[#6f2424]"}
    >
      {message}
    </div>
  );
}
