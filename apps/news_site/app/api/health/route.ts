import { NextResponse } from "next/server";
import { loadSiteSnapshot } from "@/lib/adapter/loaders";
import { buildPublicationHealth } from "@/lib/publication_health.mjs";

export const dynamic = "force-dynamic";

export async function GET() {
  const snapshot = loadSiteSnapshot();
  const publicationHealth = buildPublicationHealth(snapshot);

  return NextResponse.json(
    {
      status: snapshot.status,
      site_id: snapshot.site.site_id,
      snapshot_id: snapshot.snapshot_id,
      digest_at: snapshot.digest_at,
      generated_at: snapshot.generated_at,
      item_count: snapshot.metrics.item_count,
      section_count: snapshot.metrics.section_count,
      published_article_count: snapshot.metrics.published_article_count ?? 0,
      freshness_status: publicationHealth.freshness_status,
      is_current: publicationHealth.is_current,
      publication_health: publicationHealth,
    },
    { headers: { "Cache-Control": "no-store" } },
  );
}
