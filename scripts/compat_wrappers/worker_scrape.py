#!/usr/bin/env python3
"""Compatibility wrapper for enrich scrape worker.

Primary implementation moved to apps.news_enrich.src.news_enrich.worker_scrape.
"""

from apps.news_enrich.src.news_enrich.worker_scrape import main


if __name__ == "__main__":
    main()
