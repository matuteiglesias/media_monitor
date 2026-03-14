"""Legacy compatibility wrapper for editorial stage06.

Primary implementation moved to apps.news_editorial.src.news_editorial.stage06_build_piece_briefs.
"""

from apps.news_editorial.src.news_editorial.stage06_build_piece_briefs import run


if __name__ == "__main__":
    raise SystemExit(run())
