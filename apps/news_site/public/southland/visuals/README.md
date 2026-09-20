# Southland visual assets

This directory contains **publishable Southland illustrations**, not the downloaded LPO source-reference corpus.

The canonical metadata registry is:

`config/southland_visual_assets.v1.json`

The build only considers an asset when:
- `status == "approved"`;
- `identity_status` is `confirmed` or `generic`;
- the referenced file exists under this public directory;
- at least one controlled tag overlaps the article's derived visual tags;
- if both article and image have character tags, at least one character must match.

No match intentionally means no article image.

Validate a local collection with:

```bash
python scripts/validate_southland_visual_assets.py --require-files --require-ready
```

The initial seven seed records deliberately begin as `pending_lineage`: copy the corresponding user-created images here and attach character tags from explicit source/user lineage before changing them to `confirmed`.
