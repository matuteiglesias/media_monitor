import { loadOutlet } from "@/lib/adapter/mappers";
import { monitoredSignalsRss } from "@/lib/feeds";

export const dynamic = "force-dynamic";

export async function GET() {
  return new Response(monitoredSignalsRss(loadOutlet()), {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
