"""Legacy compatibility wrapper for acquire stage02.

Primary implementation moved to apps.news_acquire.src.news_acquire.stage02_master_index_update.
"""

from apps.news_acquire.src.news_acquire.stage02_master_index_update import run


if __name__ == "__main__":
    raise SystemExit(run())
