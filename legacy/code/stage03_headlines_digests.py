"""Legacy compatibility wrapper for acquire stage03.

Primary implementation moved to apps.news_acquire.src.news_acquire.stage03_headlines_digests.
"""

from apps.news_acquire.src.news_acquire.stage03_headlines_digests import run


if __name__ == "__main__":
    raise SystemExit(run())
