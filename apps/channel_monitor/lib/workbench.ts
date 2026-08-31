export type TabId = "latest" | "outlets" | "item";
export const TAB_CATALOG: Record<TabId, { label: string; description: string }> = {
  latest: { label: "Latest", description: "Recent publisher activity across configured channels." },
  outlets: { label: "Outlets", description: "Reconciliation health and latest known publication by channel." },
  item: { label: "Item", description: "One canonical monitored video and its metadata observation history." },
};
export function configuredTabs(): TabId[] {
  const raw = process.env.NEXT_PUBLIC_CHANNEL_MONITOR_TABS || "latest,outlets,item";
  const selected = raw.split(",").map((value) => value.trim()).filter((value): value is TabId => value in TAB_CATALOG);
  return selected.length ? Array.from(new Set(selected)) : ["latest", "outlets", "item"];
}
