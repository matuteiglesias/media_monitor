export const CURATION_REASON_LABELS: Record<string, string> = {
  fresh_under_30m: "muy reciente",
  fresh_under_60m: "reciente",
  fresh_under_120m: "últimas 2 h",
  fresh_under_180m: "últimas 3 h",
  high_topic_priority: "tema prioritario",
  standard_topic_priority: "tema relevante",
  unweighted_topic: "sin prioridad temática extra",
  new_source_bonus: "diversidad de fuente",
  new_topic_bonus: "diversidad temática",
  repeat_source_penalty: "fuente ya representada",
  repeat_topic_penalty: "tema ya representado",
};

export function curationReasonLabel(code: string) {
  return CURATION_REASON_LABELS[code] ?? code.replaceAll("_", " ");
}
