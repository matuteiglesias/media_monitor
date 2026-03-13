"""Legacy compatibility wrapper for editorial stage05.

Primary implementation moved to apps.news_editorial.src.news_editorial.stage05_explode_pf_outputs.
"""

from apps.news_editorial.src.news_editorial.stage05_explode_pf_outputs import run


if __name__ == "__main__":
    raise SystemExit(run())
