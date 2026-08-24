import { loadOutlet } from "@/lib/adapter/mappers";
import { approvedAnalysisRss } from "@/lib/feeds";

export const dynamic = "force-dynamic";

export async function GET() {
  return new Response(approvedAnalysisRss(loadOutlet()), {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
