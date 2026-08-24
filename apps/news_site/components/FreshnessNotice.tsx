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
  const message = health.freshness_status === "FRESH" && health.within_target
    ? `${lead} ${updated}.`
    : `${lead}. Última señal: ${updated}.`;

  return (
    <div
      data-publication-health={health.freshness_status}
      role="status"
      className="border-b bg-neutral-50 px-6 py-2 text-center text-xs text-neutral-700"
    >
      {message}
    </div>
  );
}
