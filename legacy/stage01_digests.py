"""Legacy compatibility wrapper for acquire stage01.

Primary implementation moved to apps.news_acquire.src.news_acquire.stage01_digests.
"""

from apps.news_acquire.src.news_acquire.stage01_digests import run


if __name__ == "__main__":
    raise SystemExit(run())
