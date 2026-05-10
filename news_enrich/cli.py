"""Repo-root compatibility entrypoint for `python -m news_enrich.cli`."""

from apps.news_enrich.src.news_enrich.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
