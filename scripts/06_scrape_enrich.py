#!/usr/bin/env python3
"""Compatibility wrapper for enrich scrape runner.

Primary implementation moved to apps.news_enrich.src.news_enrich.scrape_enrich.
"""

from apps.news_enrich.src.news_enrich.scrape_enrich import main


if __name__ == "__main__":
    main()
