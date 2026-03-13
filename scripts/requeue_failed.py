#!/usr/bin/env python3
"""Compatibility wrapper for enrich requeue helper.

Primary implementation moved to apps.news_enrich.src.news_enrich.requeue_failed.
"""

from apps.news_enrich.src.news_enrich.requeue_failed import main


if __name__ == "__main__":
    main()
