export const DEFAULT_FRESHNESS_POLICY = Object.freeze({
  target_minutes: 120,
  degraded_after_minutes: 180,
  stale_after_minutes: 360,
});

function requireDate(value, label) {
  const parsed = value instanceof Date ? new Date(value.getTime()) : new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`${label} must be a valid timestamp`);
  }
  return parsed;
}

function requireText(value, label) {
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`${label} must be a non-empty string`);
  }
  return value.trim();
}

function newestMonitoredAt(snapshot) {
  const latest = Array.isArray(snapshot?.latest) ? snapshot.latest : [];
  const candidates = [...latest];
  if (snapshot?.hero) candidates.push(snapshot.hero);
  if (!candidates.length) {
    throw new Error("site snapshot has no monitored items");
  }

  let newest = null;
  for (const [index, item] of candidates.entries()) {
    const parsed = requireDate(item?.published_at, `monitored item ${index}.published_at`);
    if (!newest || parsed > newest) newest = parsed;
  }
  return newest;
}

export function buildPublicationHealth(
  snapshot,
  now = new Date(),
  policy = DEFAULT_FRESHNESS_POLICY,
) {
  const evaluatedAt = requireDate(now, "evaluation time");
  const newestItemAt = newestMonitoredAt(snapshot);
  const ageMinutes = Math.max(
    0,
    Math.floor((evaluatedAt.getTime() - newestItemAt.getTime()) / 60_000),
  );

  let freshnessStatus = "FRESH";
  if (ageMinutes > policy.stale_after_minutes) {
    freshnessStatus = "STALE";
  } else if (ageMinutes > policy.degraded_after_minutes) {
    freshnessStatus = "DEGRADED";
  }

  return {
    schema_name: "publication_health.v1",
    site_id: requireText(snapshot?.site?.site_id, "site.site_id"),
    snapshot_id: requireText(snapshot?.snapshot_id, "snapshot_id"),
    digest_at: requireText(snapshot?.digest_at, "digest_at"),
    evaluated_at: evaluatedAt.toISOString(),
    newest_item_at: newestItemAt.toISOString(),
    age_minutes: ageMinutes,
    freshness_status: freshnessStatus,
    within_target: ageMinutes <= policy.target_minutes,
    is_current: freshnessStatus === "FRESH",
    policy: {
      target_minutes: policy.target_minutes,
      degraded_after_minutes: policy.degraded_after_minutes,
      stale_after_minutes: policy.stale_after_minutes,
    },
  };
}

export function freshnessLead(health) {
  if (health.freshness_status === "STALE") {
    return "Actualización temporalmente demorada";
  }
  if (health.freshness_status === "DEGRADED") {
    return "Actualización demorada";
  }
  if (!health.within_target) {
    return "Última actualización";
  }
  return "Actualizado";
}
