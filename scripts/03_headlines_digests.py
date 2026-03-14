#!/usr/bin/env python3
"""Compatibility wrapper for headlines digests stage.

Canonical implementation lives in:
- apps.news_acquire.src.news_acquire.stage03_headlines_digests

Historical script snapshot archived at:
- scripts/archive/historical/03_headlines_digests.py
"""

from apps.news_acquire.src.news_acquire.stage03_headlines_digests import run


if __name__ == "__main__":
    raise SystemExit(run())
