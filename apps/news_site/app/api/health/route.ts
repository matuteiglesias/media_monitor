import { NextResponse } from "next/server"; import { loadSiteSnapshot } from "@/lib/adapter/loaders";
export async function GET(){const s=loadSiteSnapshot(); return NextResponse.json({status:s.status,site_id:s.site.site_id,snapshot_id:s.snapshot_id,digest_at:s.digest_at,generated_at:s.generated_at,item_count:s.metrics.item_count,section_count:s.metrics.section_count});}
