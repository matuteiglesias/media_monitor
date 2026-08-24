export type FreshnessStatus = "FRESH" | "DEGRADED" | "STALE";

export interface FreshnessPolicy {
  target_minutes: number;
  degraded_after_minutes: number;
  stale_after_minutes: number;
}

export interface PublicationHealth {
  schema_name: "publication_health.v1";
  site_id: string;
  snapshot_id: string;
  digest_at: string;
  evaluated_at: string;
  newest_item_at: string;
  age_minutes: number;
  freshness_status: FreshnessStatus;
  within_target: boolean;
  is_current: boolean;
  policy: FreshnessPolicy;
}

export const DEFAULT_FRESHNESS_POLICY: Readonly<FreshnessPolicy>;

export function buildPublicationHealth(
  snapshot: any,
  now?: Date | string,
  policy?: FreshnessPolicy,
): PublicationHealth;

export function freshnessLead(health: PublicationHealth): string;
