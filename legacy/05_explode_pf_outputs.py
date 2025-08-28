import pandas as pd
from pathlib import Path
import json
import argparse

# At the top of your script
parser = argparse.ArgumentParser()
parser.add_argument('--digest-id', type=str, help="Filter by digest_id prefix (e.g. 20250621T16)")
args = parser.parse_args()


# === PATHS ===
PFOUT_DIR = Path("./data/pf_out")
ARTICLE_OUT_PATH = Path("./data/article_quotes/articles_exploded.jsonl")
IDEA_OUT_PATH = Path("./data/idea_cluster/seed_ideas_exploded.jsonl")
MASTER_REF_PATH = Path("./data/master_ref.csv")
SCRAPED_PATH = Path("./data/scraped_links.jsonl")
ENRICHED_OUT_PATH = Path("./data/article_quotes/articles_to_scrape.jsonl")


# Crear directorios de salida si no existen
ARTICLE_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
IDEA_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# === Utilidades ===
def concat_existing(output_path: Path, new_df: pd.DataFrame, subset_cols=None):
    if output_path.exists():
        old_df = pd.read_json(output_path, lines=True)
        if subset_cols:
            combined = pd.concat([old_df, new_df], ignore_index=True).drop_duplicates(subset=subset_cols)
        else:
            combined = pd.concat([old_df, new_df], ignore_index=True)
    else:
        combined = new_df
    return combined

# === Leer archivos PF ===
pf_files = list(PFOUT_DIR.glob(f"pfout_{args.digest_id}_*.jsonl" if args.digest_id else "pfout_*.jsonl"))
print(f"🔍 Encontrados {len(pf_files)} archivos para procesar...")

 
master_ref = pd.read_csv(MASTER_REF_PATH)
master_ref = master_ref.loc[master_ref.index_id.str.len() == 10]

# master_ref["article_key"] = master_ref["digest_file"] + "::" + master_ref["article_id"].astype(str)
# rss_index = master_ref.set_index("article_key").to_dict(orient="index")
rss_index = master_ref.set_index("key").to_dict(orient="index")

# === Inicializar listas acumuladoras ===
article_rows = []
seed_idea_rows = []

# === Cargar todos los archivos pfout ===
if args.digest_id:
    pf_files = list(PFOUT_DIR.glob(f"pfout_{args.digest_id}_*.jsonl"))
else:
    pf_files = list(PFOUT_DIR.glob("pfout_*.jsonl"))
print(f"🔍 Encontrados {len(pf_files)} archivos para procesar...")

for pf_file in pf_files:
    df = pd.read_json(pf_file, lines=True)
    for _, row in df.iterrows():
        digest_group_id = row.get("digest_group_id", "")
        parts = digest_group_id.split("::")
        if len(parts) < 4:
            raise ValueError(f"Malformed digest_group_id in {pf_file}: {digest_group_id}")
        digest_ts, window_type, topic, group_number = parts
        id_digest = f"{window_type}_{digest_ts}0000"

        line_metadata = {
            "line_number": row.get("line_number"),
            "id_digest": id_digest,
            "digest_group_id": digest_group_id,
            "window_type": window_type,
            "topic": topic,
            "group_number": group_number,
        }

        # Artículos
        for cluster in row.get("clustered_agenda_table", {}).get("clustered_agenda_table", []):
            for aid, title in zip(cluster["article_ids"], cluster["deduplicated_titles"]):
                article_rows.append({
                    **line_metadata,
                    "cluster_topic": cluster["topic"],
                    "article_id": aid,
                    "title": title,
                    "source_file": pf_file.name,
                })

        # Ideas
        for idea in row.get("seed_ideas", {}).get("seed_ideas", []):
            seed_idea_rows.append({
                **line_metadata,
                **idea,
                "source_file": pf_file.name,
            })

# === Guardar resultados incrementales ===
new_articles_df = pd.DataFrame(article_rows)
new_ideas_df = pd.DataFrame(seed_idea_rows)


combined_articles = concat_existing(ARTICLE_OUT_PATH, new_articles_df, subset_cols=["article_id", "title", "source_file"])
combined_ideas = concat_existing(IDEA_OUT_PATH, new_ideas_df, subset_cols=["idea_id", "idea_title", "source_file"])

# === Agregar digest_file y key antes de merge ===
combined_articles["id_digest"] = combined_articles["id_digest"].astype(str).str.strip()
combined_articles["article_id"] = combined_articles["article_id"].astype(str).str.strip()

# Formato normalizado
combined_articles["digest_file"] = combined_articles["id_digest"].str.replace(r"T(\d{2})(\d{2})(\d{2})$", r"T\1\2", regex=True)

# Key final
combined_articles["key"] = combined_articles["digest_file"] + "::" + combined_articles["article_id"]

master_ref["article_id"] = master_ref["article_id"].astype(str)
master_ref["digest_file"] = master_ref["digest_file"].astype(str)
master_ref["key"] = master_ref["digest_file"] + "::" + master_ref["article_id"]


# combined_articles.to_json(ARTICLE_OUT_PATH, orient="records", lines=True, force_ascii=False)
# combined_ideas.to_json(IDEA_OUT_PATH, orient="records", lines=True, force_ascii=False)

# print(f"✅ Guardados:")
# print(f"  - Artículos → {ARTICLE_OUT_PATH}")
# print(f"  - Ideas     → {IDEA_OUT_PATH}")


# # # === Enriquecer con master_ref ===

# from pathlib import Path
# import pandas as pd
# ARTICLE_OUT_PATH = Path("./data/article_quotes/articles_exploded.jsonl")
# # === Enriquecer con master_ref y scraped_data ===
# full_df = pd.read_json(ARTICLE_OUT_PATH, lines=True, dtype={"id_digest": str, "article_id": str})
# full_df["digest_file"] = full_df["id_digest"]
# full_df["key"] = full_df["digest_file"] + "::" + full_df["article_id"].astype(str)
# print(full_df.head(1))
# print(full_df.columns)


# === Merge con master_ref.csv para obtener index_id ===
if MASTER_REF_PATH.exists():
    print("🔗 Enriqueciendo con master_ref.csv...")
    master_ref = pd.read_csv(MASTER_REF_PATH)
    master_ref = master_ref.loc[master_ref.index_id.str.len() == 10]

    master_ref["article_id"] = master_ref["article_id"].astype(str)
    master_ref["article_key"] = master_ref["digest_file"] + "::" + master_ref["article_id"]
    master_ref["key"] = master_ref["article_key"]

    master_subset = master_ref[["key", "index_id", "Source", "Title", "Published", "Link"]].drop_duplicates()
    combined_articles = combined_articles.merge(master_subset, how="left", on="key")
else:
    print("⚠️ master_ref.csv no encontrado, no se puede enriquecer con index_id.")

# === Merge con scraped_links.jsonl si está disponible ===
if SCRAPED_PATH.exists():
    print("🔗 Agregando contenido scrapeado...")
    content_df = pd.read_json(SCRAPED_PATH, lines=True)[["index_id", "scraped_data"]]
    combined_articles["index_id"] = combined_articles["index_id"].astype(str)
    content_df["index_id"] = content_df["index_id"].astype(str)
    combined_articles = combined_articles.merge(content_df, how="left", on="index_id")
else:
    print("⚠️ scraped_links.jsonl no encontrado, salteando merge con contenido.")
    combined_articles["scraped_data"] = None

# === Guardar artículos e ideas ===
combined_articles.to_json(ARTICLE_OUT_PATH, orient="records", lines=True, force_ascii=False)
combined_ideas.to_json(IDEA_OUT_PATH, orient="records", lines=True, force_ascii=False)
combined_articles.to_json(ENRICHED_OUT_PATH, orient="records", lines=True, force_ascii=False)

print(f"✅ Guardados:")
print(f"  - Artículos     → {ARTICLE_OUT_PATH}")
print(f"  - Ideas         → {IDEA_OUT_PATH}")
print(f"  - Enriquecidos  → {ENRICHED_OUT_PATH}")
