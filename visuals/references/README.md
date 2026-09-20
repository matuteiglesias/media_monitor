# LPO visual reference corpus

This directory is the local authoring surface for Southland visual references.

## Boundary

- `originals/` contains downloaded source images for **local/reference-only** editorial work and is gitignored.
- `manifests/lpo_articles.jsonl` and `manifests/lpo_images.jsonl` contain provenance and may be committed when deliberately curated.
- Southland publishable illustrations belong elsewhere; source originals are never automatically promoted to the public site.

The ingestion tool only follows public article and image URLs already exposed by LPO HTML/RSS. It does not bypass authentication, access controls, paywalls, or anti-bot systems.

## Acquire a current corpus

Install the bounded dependencies:

```bash
python -m pip install -r requirements-visuals.txt
```

Then collect up to 40 unique current/recent LPO articles from the same section feeds used by Southland and capture their article images:

```bash
python scripts/ingest_lpo_visual_refs.py \
  --from-rss-config config/sensing_feeds.southland.yaml \
  --limit 40 \
  --output-root visuals/references \
  --verbose
```

Explicit URLs are also supported:

```bash
python scripts/ingest_lpo_visual_refs.py \
  --url https://www.lapoliticaonline.com/economia/.../ \
  --input-file my_lpo_urls.txt \
  --output-root visuals/references
```

Re-running the command is idempotent by default. Use `--reingest-existing` only when refreshing metadata/assets intentionally.

## Image manifest semantics

Each image row records:
- stable image ID;
- all associated article IDs/URLs;
- role (hero / inline / og_only);
- original and redirected image URL;
- dimensions, MIME type, byte size, SHA-256;
- local reference path;
- caption, alt/title text and credit when exposed by the article;
- `rights_status=reference_only`;
- `publish_original=false`.

This is deliberately provenance data, not a claim about reuse rights.
