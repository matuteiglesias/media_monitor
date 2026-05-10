"""Legacy compatibility wrapper for editorial stage04.

Primary implementation moved to apps.news_editorial.src.news_editorial.stage04_promptflow_run.
"""

from apps.news_editorial.src.news_editorial.stage04_promptflow_run import run


if __name__ == "__main__":
    raise SystemExit(run())
