export type TabId = "latest" | "people" | "outlets" | "search" | "item";
export const TAB_CATALOG: Record<TabId, { label: string; description: string }> = {
  latest: { label: "Latest", description: "Recent publisher activity across configured channels." },
  people: { label: "People", description: "Configured people and evidence-bearing appearances." },
  outlets: { label: "Outlets", description: "Reconciliation health, publication recency and governed text coverage." },
  search: { label: "Search", description: "Literal search over publisher metadata and governed text assets only." },
  item: { label: "Item", description: "One canonical media item with source, monitor and detection evidence." },
};
export function configuredTabs(): TabId[] {
  const raw = process.env.NEXT_PUBLIC_CHANNEL_MONITOR_TABS || "latest,people,outlets,search,item";
  const selected = raw.split(",").map((value) => value.trim()).filter((value): value is TabId => value in TAB_CATALOG);
  return selected.length ? Array.from(new Set(selected)) : ["latest", "people", "outlets", "search", "item"];
}
