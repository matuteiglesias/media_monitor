#!/usr/bin/env python3
"""Compatibility wrapper for editorial stage05 explode.

Canonical implementation lives in:
- apps.news_editorial.src.news_editorial.stage05_explode_pf_outputs

Historical script snapshot archived at:
- scripts/archive/historical/05_explode_pf_outputs.py
"""

from apps.news_editorial.src.news_editorial.stage05_explode_pf_outputs import run


if __name__ == "__main__":
    raise SystemExit(run())
