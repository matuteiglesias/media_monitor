# %% [markdown]
# 

# %%
import pandas as pd
import re

# === Load paths ===
ideas_path = "/home/matias/Documents/media_monitor/data/idea_cluster/seed_ideas_exploded.jsonl"
articles_path = "/home/matias/Documents/media_monitor/data/article_quotes/articles_exploded.jsonl"
scraped_path = "/home/matias/Documents/media_monitor/data/scraped_links.jsonl"
master_ref_path = "/home/matias/Documents/media_monitor/data/master_ref.csv"


def enrich_idea_cluster():

    # === Load data ===
    df_ideas = pd.read_json(ideas_path, lines=True)
    df_articles = pd.read_json(articles_path, lines=True)
    df_scraped = pd.read_json(scraped_path, lines=True)
    df_master = pd.read_csv(master_ref_path)

    # === Normalize types ===
    df_articles["article_id"] = df_articles["article_id"].astype(str)
    df_scraped["article_id"] = df_scraped["article_id"].astype(str)
    df_master["article_id"] = df_master["article_id"].astype(str)
    df_ideas["source_ids"] = df_ideas["source_ids"].apply(lambda x: [str(i) for i in x])

    # === Ensure consistent digest_file (strip seconds from id_digest) ===
    # Drop seconds from id_digest to create digest_file (safe on nulls)
    for df in [df_articles, df_ideas]:
        df["digest_file"] = df["id_digest"].astype(str).str.extract(r"(.*T\d{4})")

    # === Construct keys ===
    df_articles["key"] = df_articles["digest_file"] + "::" + df_articles["article_id"]
    # df_scraped["key"] = df_scraped["digest_file"] + "::" + df_scraped["article_id"]
    df_master["key"] = df_master["digest_file"] + "::" + df_master["article_id"]

    # === Explode ideas and build their keys ===
    df_ideas_exploded = df_ideas.explode("source_ids").copy()
    df_ideas_exploded["source_ids"] = df_ideas_exploded["source_ids"].astype(str)
    df_ideas_exploded["key"] = df_ideas_exploded["digest_file"] + "::" + df_ideas_exploded["source_ids"]

    # # === Enrich articles with index_id and metadata from master_ref ===
    # merge_fields = ["index_id", "Source", "Title", "Published", "Link"]

    # df_articles = df_articles.merge(
    #     df_master[["index_id", "Source", "Title", "Published", "Link"]],
    #     on="index_id", how="left"
    # )

    # === Enrich articles with scraped_data ===
    df_articles["index_id"] = df_articles["index_id"].astype(str)
    df_scraped["index_id"] = df_scraped["index_id"].astype(str)
    df_articles = df_articles.drop("scraped_data", axis = 1).merge(
        df_scraped[["index_id", "scraped_data"]],
        on="index_id", how="left"
    )

    # === Enrich exploded ideas: attach article metadata via 'key' ===
    df_ideas_exploded = df_ideas_exploded.merge(
        df_articles[["key", "title", "cluster_topic", "index_id"]],
        on="key", how="left"
    )

    # Optionally return the enriched ideas
    return df_ideas_exploded


# Optional: save enriched ideas for downstream usage
output_path = "/home/matias/Documents/media_monitor/data/idea_cluster/enriched_seed_ideas.jsonl"

if __name__ == "__main__":
    enriched_df = enrich_idea_cluster()
    enriched_df.to_json(output_path, orient="records", lines=True, force_ascii=False)

# %%



