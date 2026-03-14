#!/usr/bin/env python3
"""Compatibility wrapper for PromptFlow stage04.

Canonical implementation lives in:
- apps.news_editorial.src.news_editorial.stage04_promptflow_run

Historical script snapshot archived at:
- scripts/archive/historical/04_promptflow_run.py
"""

from apps.news_editorial.src.news_editorial.stage04_promptflow_run import run


if __name__ == "__main__":
    raise SystemExit(run())
