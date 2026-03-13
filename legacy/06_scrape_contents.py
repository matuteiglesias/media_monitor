#!/usr/bin/env python3
"""Legacy compatibility wrapper for enrich scrape-contents path.

Primary implementation moved to apps.news_enrich.src.news_enrich.scrape_contents_legacy.
"""

from apps.news_enrich.src.news_enrich.scrape_contents_legacy import main


if __name__ == "__main__":
    main()
