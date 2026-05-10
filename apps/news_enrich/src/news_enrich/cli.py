"""Command-line entrypoints for news_enrich."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from .bus_writer import default_scraped_article_bus_path, write_scraped_article
from .io import append_jsonl
from .requests import EnrichRequest
from .service import enrich_one


def default_scrape_output(now: datetime | None = None) -> Path:
    now = now or datetime.now(timezone.utc)
    return Path("data/scrape") / f"{now:%Y-%m-%d}.enriched.jsonl"


def enrich_one_command(args: argparse.Namespace) -> int:
    request = EnrichRequest(
        index_id=args.index_id,
        url=args.url,
        title=args.title or "",
        source=args.source or "",
        topic=args.topic or "",
        digest_at=args.digest_at,
        priority=args.priority,
    )
    record = enrich_one(request, timeout=args.timeout)
    bus_path = write_scraped_article(record, path=Path(args.bus_output) if args.bus_output else None)

    if not args.no_scrape_mirror:
        mirror_path = Path(args.scrape_output) if args.scrape_output else default_scrape_output()
        append_jsonl(mirror_path, record)

    print(record.model_dump_json())
    print(f"scraped_article_bus={bus_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="news_enrich on-demand article text service")
    subparsers = parser.add_subparsers(dest="command", required=True)

    enrich_one_parser = subparsers.add_parser("enrich-one", help="Fetch one article URL and append one schema-valid scraped_article.v1 record")
    enrich_one_parser.add_argument("--index-id", required=True, help="Reference/article id to carry through the enriched record")
    enrich_one_parser.add_argument("--url", required=True, help="Article URL to fetch")
    enrich_one_parser.add_argument("--title", default="", help="Optional known article title")
    enrich_one_parser.add_argument("--source", default="", help="Optional known source/publication")
    enrich_one_parser.add_argument("--topic", default="", help="Optional known topic")
    enrich_one_parser.add_argument("--digest-at", default=None, help="Optional digest hour, e.g. YYYYMMDDTHH")
    enrich_one_parser.add_argument("--priority", choices=["high", "normal", "low"], default="normal")
    enrich_one_parser.add_argument("--timeout", type=int, default=20)
    enrich_one_parser.add_argument("--bus-output", default=None, help="Override scraped_article.v1 bus JSONL path; defaults to storage/buses/scraped_article/v1/scraped_article_<UTC-day>.jsonl")
    enrich_one_parser.add_argument("--scrape-output", default=None, help="Override optional Level-0 scrape mirror path; defaults to data/scrape/<UTC-day>.enriched.jsonl")
    enrich_one_parser.add_argument("--no-scrape-mirror", action="store_true", help="Do not also append the record to data/scrape")
    enrich_one_parser.set_defaults(func=enrich_one_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
