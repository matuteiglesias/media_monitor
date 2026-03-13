#!/usr/bin/env python3
"""Compatibility wrapper for enrich replay helper.

Primary implementation moved to apps.news_enrich.src.news_enrich.replay_job.
"""

from apps.news_enrich.src.news_enrich.replay_job import main


if __name__ == "__main__":
    main()
