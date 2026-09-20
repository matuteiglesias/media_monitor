#!/usr/bin/env python3
"""Capture public La Política Online article images as local reference assets.

The downloaded originals are reference-only inputs for Southland illustration work.
They are intentionally kept out of Git; structured provenance manifests are the
persistent surface.

This tool only follows public article/image URLs exposed by article HTML/RSS. It
does not bypass authentication, access controls, or anti-bot challenges.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import mimetypes
from pathlib import Path
import re
import sys
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse, urlunparse

import feedparser
from bs4 import BeautifulSoup
from PIL import Image
import requests
import yaml


DEFAULT_UA = "media-monitor-southland-visual-reference/1.0 (+https://github.com/matuteiglesias/media_monitor)"
LPO_HOSTS = {"lapoliticaonline.com", "www.lapoliticaonline.com"}
NOISE_TOKENS = (
    "logo", "icon", "avatar", "favicon", "sprite", "banner", "social",
    "facebook", "twitter", "instagram", "youtube", "whatsapp", "pixel",
    "horizontal-pieza-noticia",
)
IMAGE_MIME_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@dataclass(frozen=True)
class Candidate:
    url: str
    role: str
    ordinal: int
    caption: str = ""
    credit: str = ""
    alt_text: str = ""
    title_text: str = ""


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_id(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    return prefix + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def normalize_url(value: str, *, base: str | None = None) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if base:
        value = urljoin(base, value)
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    host = parsed.netloc.lower()
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    return urlunparse((parsed.scheme.lower(), host, path, "", parsed.query, ""))


def is_lpo_article_url(url: str) -> bool:
    return urlparse(url).netloc.lower() in LPO_HOSTS


def parse_srcset(value: str, base_url: str) -> str:
    candidates: list[tuple[float, str]] = []
    for chunk in (value or "").split(","):
        parts = chunk.strip().split()
        if not parts:
            continue
        url = normalize_url(parts[0], base=base_url)
        if not url:
            continue
        score = 1.0
        if len(parts) > 1:
            descriptor = parts[1].lower()
            try:
                if descriptor.endswith("w"):
                    score = float(descriptor[:-1])
                elif descriptor.endswith("x"):
                    score = float(descriptor[:-1]) * 1000.0
            except ValueError:
                pass
        candidates.append((score, url))
    return max(candidates, default=(0.0, ""), key=lambda item: item[0])[1]


def best_img_url(img, base_url: str) -> str:
    for attr in ("srcset", "data-srcset"):
        value = img.get(attr)
        if value:
            picked = parse_srcset(value, base_url)
            if picked:
                return picked
    for attr in ("vsmsrc", "data-vsmsrc", "src", "data-src", "data-lazy-src", "data-original"):
        value = img.get(attr)
        if value:
            picked = normalize_url(value, base=base_url)
            if picked:
                return picked
    return ""


def looks_like_noise(url: str, alt: str = "") -> bool:
    combined = (url + " " + alt).casefold()
    return any(token in combined for token in NOISE_TOKENS)


def asset_family_key(url: str) -> str:
    """Collapse LPO generated crops back to their underlying image family."""
    parsed = urlparse(url)
    path = parsed.path
    if parsed.netloc.lower() in LPO_HOSTS and "/files/image/" in path:
        path = re.sub(r"_\d+_\d+!?(?=\.[A-Za-z0-9]+$)", "", path)
        return f"{parsed.netloc.lower()}{path}"
    return normalize_url(url)


def _prefer_asset_url(existing: str, incoming: str) -> str:
    """Prefer the uncropped LPO source asset over generated social/card crops."""
    crop = re.compile(r"_\d+_\d+!?(?=\.[A-Za-z0-9]+$)")
    existing_crop = bool(crop.search(urlparse(existing).path))
    incoming_crop = bool(crop.search(urlparse(incoming).path))
    if existing_crop != incoming_crop:
        return incoming if not incoming_crop else existing
    return incoming if len(urlparse(incoming).query) < len(urlparse(existing).query) else existing


def _jsonld_objects(soup: BeautifulSoup) -> Iterable[dict[str, Any]]:
    for node in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = node.string or node.get_text("", strip=True)
        if not raw:
            continue
        try:
            value = json.loads(raw)
        except Exception:
            continue
        stack = value if isinstance(value, list) else [value]
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                yield current
                graph = current.get("@graph")
                if isinstance(graph, list):
                    stack.extend(graph)
            elif isinstance(current, list):
                stack.extend(current)


def _jsonld_article(soup: BeautifulSoup) -> dict[str, Any]:
    for obj in _jsonld_objects(soup):
        kind = obj.get("@type")
        kinds = kind if isinstance(kind, list) else [kind]
        if any(value in {"NewsArticle", "Article", "ReportageNewsArticle"} for value in kinds):
            return obj
    return {}


def _extract_credit(text: str) -> str:
    text = " ".join((text or "").split())
    if not text:
        return ""
    match = re.search(
        r"(?:foto(?:graf[ií]a)?|cr[eé]dito|gentileza|fuente)\s*[:\-]\s*(.+)$",
        text,
        flags=re.IGNORECASE,
    )
    return match.group(0).strip() if match else ""


def _gallery_entries(gallery) -> list[dict[str, Any]]:
    """Read LPO's server-rendered gallery metadata from its vplfgal config."""
    media = gallery.find_parent("div", class_=lambda value: value and "media" in value)
    if media is None:
        media = gallery.parent
    script = media.find("script") if media is not None else None
    raw = script.get_text("", strip=False) if script else ""
    if not raw:
        return []
    match = re.search(
        r"arguments:\s*\['[^']+',\s*(\[\{.*?\}\])\s*,\s*\d+",
        raw,
        flags=re.DOTALL,
    )
    if not match:
        return []
    try:
        value = json.loads(match.group(1))
    except Exception:
        return []
    return [row for row in value if isinstance(row, dict)]


def article_metadata(html: str, requested_url: str, final_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    jsonld = _jsonld_article(soup)

    canonical_tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    canonical = normalize_url(
        canonical_tag.get("href", "") if canonical_tag else "",
        base=final_url,
    ) or normalize_url(final_url) or normalize_url(requested_url)

    headline = ""
    for value in (
        jsonld.get("headline"),
        (soup.find("meta", property="og:title") or {}).get("content") if soup.find("meta", property="og:title") else "",
        soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else "",
    ):
        if isinstance(value, str) and value.strip():
            headline = " ".join(value.split())
            break

    published_at = ""
    updated_at = ""
    for key, target in (("datePublished", "published"), ("dateModified", "updated")):
        value = jsonld.get(key)
        if not value:
            meta = soup.find("meta", property=f"article:{'published_time' if target == 'published' else 'modified_time'}")
            value = meta.get("content", "") if meta else ""
        if target == "published":
            published_at = str(value or "").strip()
        else:
            updated_at = str(value or "").strip()

    section = str(jsonld.get("articleSection") or "").strip()
    if not section:
        meta = soup.find("meta", property="article:section")
        section = str(meta.get("content", "") if meta else "").strip()

    slug = urlparse(canonical).path.rstrip("/").split("/")[-1] if canonical else ""
    return {
        "canonical_url": canonical,
        "slug": slug,
        "headline": headline,
        "section": section,
        "published_at": published_at,
        "updated_at": updated_at,
        "jsonld": jsonld,
        "soup": soup,
    }


def discover_images(html: str, article_url: str, final_url: str) -> tuple[dict[str, Any], list[Candidate]]:
    meta = article_metadata(html, article_url, final_url)
    soup: BeautifulSoup = meta.pop("soup")
    jsonld = meta.pop("jsonld")
    candidate_index: dict[str, int] = {}
    article_surface_families: set[str] = set()
    candidates: list[Candidate] = []

    def add(url: str, role: str, *, caption: str = "", credit: str = "", alt: str = "", title: str = "") -> None:
        normalized = normalize_url(url, base=final_url)
        if not normalized or looks_like_noise(normalized, alt):
            return
        family = asset_family_key(normalized)
        caption = " ".join((caption or "").split())
        credit = " ".join((credit or "").split())
        alt = " ".join((alt or "").split())
        title = " ".join((title or "").split())
        if family in candidate_index:
            idx = candidate_index[family]
            previous = candidates[idx]
            candidates[idx] = Candidate(
                url=_prefer_asset_url(previous.url, normalized),
                role="hero" if "hero" in {previous.role, role} else previous.role,
                ordinal=previous.ordinal,
                caption=previous.caption or caption,
                credit=previous.credit or credit,
                alt_text=previous.alt_text or alt,
                title_text=previous.title_text or title,
            )
            return
        candidate_index[family] = len(candidates)
        candidates.append(
            Candidate(
                url=normalized,
                role=role,
                ordinal=len(candidates),
                caption=caption,
                credit=credit,
                alt_text=alt,
                title_text=title,
            )
        )

    og = soup.find("meta", property="og:image")
    if og:
        add(og.get("content", ""), "hero")
    twitter = soup.find("meta", attrs={"name": "twitter:image"})
    if twitter:
        add(twitter.get("content", ""), "hero")

    image_value = jsonld.get("image")
    if isinstance(image_value, str):
        add(image_value, "hero")
    elif isinstance(image_value, dict):
        add(str(image_value.get("url") or image_value.get("contentUrl") or ""), "hero")
    elif isinstance(image_value, list):
        for item in image_value:
            if isinstance(item, str):
                add(item, "hero")
            elif isinstance(item, dict):
                add(str(item.get("url") or item.get("contentUrl") or ""), "hero")

    # Current LPO pages render the lead gallery with base64 placeholders and
    # expose the real URL in `vsmsrc`; caption/author live in the adjacent
    # vplfgal JavaScript config. Capture that before falling back to generic
    # semantic article markup.
    for gallery_index, gallery in enumerate(soup.select("div.gallery")):
        entries = _gallery_entries(gallery)
        media = gallery.find_parent("div", class_=lambda value: value and "media" in value)
        footer = media.find("div", class_="media-footer") if media else None

        # The JavaScript config is authoritative for all gallery images, even
        # when only the first image is rendered into static HTML.
        for entry_index, entry in enumerate(entries):
            url = normalize_url(str(entry.get("i") or ""), base=final_url)
            if not url:
                continue
            article_surface_families.add(asset_family_key(url))
            add(
                url,
                "hero" if gallery_index == 0 and entry_index == 0 else "inline",
                caption=str(entry.get("t") or ""),
                credit=str(entry.get("a") or ""),
            )

        # Rendered lazy-image elements add alt/title and act as a fallback when
        # LPO changes the gallery config shape.
        gallery_images = gallery.select("img[vsmsrc], img[data-vsmsrc]")
        for image_index, img in enumerate(gallery_images):
            entry = entries[image_index] if image_index < len(entries) else {}
            entry_url = str(entry.get("i") or "")
            url = normalize_url(entry_url, base=final_url) or best_img_url(img, final_url)
            if not url:
                continue
            article_surface_families.add(asset_family_key(url))
            caption = str(entry.get("t") or "")
            author = str(entry.get("a") or "")
            if not caption and footer:
                caption_node = footer.find(class_="caption")
                caption = caption_node.get_text(" ", strip=True) if caption_node else ""
            if not author and footer:
                author_node = footer.find(class_=lambda value: value and ("g_author" in value or "author" in value))
                author = author_node.get_text(" ", strip=True) if author_node else ""
            add(
                url,
                "hero" if gallery_index == 0 and image_index == 0 else "inline",
                caption=caption,
                credit=author,
                alt=img.get("alt", ""),
                title=img.get("title", ""),
            )

    article = (
        soup.find("article")
        or soup.find("main")
        or soup.select_one("div.body.vsmcontent")
        or soup.select_one("div.bloque1.nota")
    )
    if article:
        for figure_index, figure in enumerate(article.find_all("figure")):
            img = figure.find("img")
            if not img:
                continue
            figcaption = figure.find("figcaption")
            caption = figcaption.get_text(" ", strip=True) if figcaption else ""
            credit = _extract_credit(caption)
            url = best_img_url(img, final_url)
            if url:
                article_surface_families.add(asset_family_key(url))
            add(
                url,
                "hero" if figure_index == 0 and not candidates else "inline",
                caption=caption,
                credit=credit,
                alt=img.get("alt", ""),
                title=img.get("title", ""),
            )
        for img in article.find_all("img"):
            related = img.find_parent(
                class_=lambda value: value and (
                    "noticia-ar" in value
                    if isinstance(value, (list, tuple))
                    else "noticia-ar" in str(value)
                )
            )
            if related is not None and img.find_parent("figure", class_="vsmimage") is None:
                continue
            url = best_img_url(img, final_url)
            if url:
                article_surface_families.add(asset_family_key(url))
            add(
                url,
                "inline",
                alt=img.get("alt", ""),
                title=img.get("title", ""),
            )

    # An og/jsonld image that never appears in article markup is still useful as
    # reference evidence, but mark it explicitly.
    if candidates:
        candidates = [
            Candidate(
                url=row.url,
                role=(
                    "og_only"
                    if row.role == "hero"
                    and asset_family_key(row.url) not in article_surface_families
                    and len(candidates) > 1
                    else row.role
                ),
                ordinal=row.ordinal,
                caption=row.caption,
                credit=row.credit,
                alt_text=row.alt_text,
                title_text=row.title_text,
            )
            for row in candidates
        ]

    return meta, candidates


def load_jsonl(path: Path, key: str) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict) and value.get(key):
            rows[str(value[key])] = value
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]], key: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda row: str(row.get(key) or ""))
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in ordered),
        encoding="utf-8",
    )
    tmp.replace(path)


def extension_for(content_type: str, final_url: str) -> str:
    mime = content_type.split(";", 1)[0].strip().lower()
    if mime in IMAGE_MIME_EXT:
        return IMAGE_MIME_EXT[mime]
    suffix = Path(urlparse(final_url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    guessed = mimetypes.guess_extension(mime) if mime else None
    return guessed or ".bin"


def dimensions(data: bytes) -> tuple[int | None, int | None]:
    try:
        with Image.open(io.BytesIO(data)) as image:
            return int(image.width), int(image.height)
    except Exception:
        return None, None


def collect_urls_from_rss(config_path: Path, *, limit: int | None = None) -> list[str]:
    """Collect a cross-section, recency-sorted set of LPO article URLs."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    feeds = config.get("feeds") if isinstance(config, dict) else None
    if not isinstance(feeds, list):
        raise ValueError(f"{config_path}: expected feeds list")

    by_url: dict[str, float] = {}
    for feed in feeds:
        if not isinstance(feed, dict) or not feed.get("url"):
            continue
        parsed = feedparser.parse(str(feed["url"]))
        for entry in getattr(parsed, "entries", []):
            url = normalize_url(str(getattr(entry, "link", "") or ""))
            if not url or not is_lpo_article_url(url):
                continue
            stamp = 0.0
            parsed_time = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
            if parsed_time:
                try:
                    import calendar
                    stamp = float(calendar.timegm(parsed_time))
                except Exception:
                    stamp = 0.0
            by_url[url] = max(by_url.get(url, 0.0), stamp)

    ordered = [
        url
        for url, _stamp in sorted(
            by_url.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    return ordered[:limit] if limit is not None else ordered


def request(session: requests.Session, url: str, timeout: float) -> requests.Response:
    response = session.get(url, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    return response


def ingest(
    *,
    urls: list[str],
    output_root: Path,
    timeout: float = 20.0,
    user_agent: str = DEFAULT_UA,
    max_images_per_article: int = 6,
    reingest_existing: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    now: str | None = None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    output_root = output_root.resolve()
    manifest_dir = output_root / "manifests"
    originals_dir = output_root / "originals"
    article_manifest = manifest_dir / "lpo_articles.jsonl"
    image_manifest = manifest_dir / "lpo_images.jsonl"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    originals_dir.mkdir(parents=True, exist_ok=True)

    articles = load_jsonl(article_manifest, "article_id")
    images = load_jsonl(image_manifest, "image_id")
    current_by_url = {
        str(row.get("canonical_url") or row.get("article_url") or ""): row
        for row in articles.values()
    }
    image_by_source_url = {
        str(row.get("source_image_url") or ""): row
        for row in images.values()
        if row.get("source_image_url")
    }
    image_by_sha = {
        str(row.get("sha256") or ""): row
        for row in images.values()
        if row.get("sha256")
    }

    own_session = session is None
    session = session or requests.Session()
    session.headers.update({"User-Agent": user_agent})
    retrieved_at = now or utcnow()

    processed = succeeded = failed = downloaded = reused = 0
    try:
        for requested_url in urls:
            article_url = normalize_url(requested_url)
            if not article_url or not is_lpo_article_url(article_url):
                continue
            if not reingest_existing and article_url in current_by_url:
                reused += 1
                continue
            processed += 1
            if verbose:
                print(f"[visual-ref] article {processed}: {article_url}")
            article_id = stable_id("lpo_article_", article_url)
            article_row: dict[str, Any] = {
                "article_id": article_id,
                "article_url": article_url,
                "canonical_url": article_url,
                "slug": urlparse(article_url).path.rstrip("/").split("/")[-1],
                "headline": "",
                "section": "",
                "published_at": "",
                "updated_at": "",
                "source_publisher": "La Política Online",
                "retrieved_at": retrieved_at,
                "http_status": None,
                "html_sha256": "",
                "image_ids": [],
                "parse_status": "failed",
                "error": "",
            }
            try:
                response = request(session, article_url, timeout)
                article_row["http_status"] = response.status_code
                try:
                    html = response.content.decode("utf-8")
                except UnicodeDecodeError:
                    html = response.content.decode("utf-8", errors="replace")
                article_row["html_sha256"] = hashlib.sha256(response.content).hexdigest()
                meta, candidates = discover_images(html, article_url, response.url)
                article_row.update({key: meta.get(key, "") for key in (
                    "canonical_url", "slug", "headline", "section", "published_at", "updated_at"
                )})
                canonical = str(article_row["canonical_url"] or article_url)
                article_id = stable_id("lpo_article_", canonical)
                article_row["article_id"] = article_id
                selected = candidates[:max_images_per_article]

                for candidate in selected:
                    existing = image_by_source_url.get(candidate.url)
                    if existing and not reingest_existing:
                        ids = list(existing.get("article_ids") or [])
                        article_urls = list(existing.get("article_urls") or [])
                        if article_id not in ids:
                            ids.append(article_id)
                        if canonical not in article_urls:
                            article_urls.append(canonical)
                        existing["article_ids"] = sorted(set(ids))
                        existing["article_urls"] = sorted(set(article_urls))
                        images[existing["image_id"]] = existing
                        article_row["image_ids"].append(existing["image_id"])
                        reused += 1
                        continue

                    image_id = stable_id("lpo_img_", candidate.url)
                    image_row: dict[str, Any] = {
                        "image_id": image_id,
                        "article_ids": [article_id],
                        "article_urls": [canonical],
                        "role": candidate.role,
                        "ordinal": candidate.ordinal,
                        "source_image_url": candidate.url,
                        "final_image_url": candidate.url,
                        "mime_type": "",
                        "extension": "",
                        "width": None,
                        "height": None,
                        "sha256": "",
                        "byte_size": 0,
                        "local_reference_path": "",
                        "caption": candidate.caption,
                        "credit_as_published": candidate.credit,
                        "alt_text": candidate.alt_text,
                        "title_text": candidate.title_text,
                        "source_publisher": "La Política Online",
                        "rights_status": "reference_only",
                        "publish_original": False,
                        "downloaded_at": "",
                        "download_status": "dry_run" if dry_run else "pending",
                        "notes": "",
                    }
                    if not dry_run:
                        try:
                            image_response = request(session, candidate.url, timeout)
                            content_type = image_response.headers.get("content-type", "")
                            if not content_type.lower().startswith("image/"):
                                raise ValueError(f"not an image content-type: {content_type!r}")
                            data = image_response.content
                            digest = hashlib.sha256(data).hexdigest()
                            width, height = dimensions(data)
                            if width is not None and height is not None and (width < 150 or height < 150):
                                raise ValueError(f"image too small for editorial reference: {width}x{height}")

                            duplicate = image_by_sha.get(digest)
                            if duplicate:
                                local_path = str(duplicate.get("local_reference_path") or "")
                                if local_path:
                                    duplicate_path = output_root.parent.parent / local_path if not Path(local_path).is_absolute() else Path(local_path)
                                    # Fall back to this output root when manifests were moved.
                                    if not duplicate_path.is_file():
                                        duplicate_path = originals_dir / Path(local_path).name
                                else:
                                    duplicate_path = None
                            else:
                                duplicate_path = None

                            ext = extension_for(content_type, image_response.url)
                            file_path = duplicate_path if duplicate_path and duplicate_path.is_file() else originals_dir / f"{image_id}{ext}"
                            if not file_path.is_file():
                                file_path.write_bytes(data)
                                downloaded += 1
                            else:
                                reused += 1

                            try:
                                local_reference_path = file_path.relative_to(output_root.parent.parent).as_posix()
                            except ValueError:
                                local_reference_path = file_path.as_posix()

                            image_row.update(
                                final_image_url=normalize_url(image_response.url),
                                mime_type=content_type.split(";", 1)[0].strip().lower(),
                                extension=ext,
                                width=width,
                                height=height,
                                sha256=digest,
                                byte_size=len(data),
                                local_reference_path=local_reference_path,
                                downloaded_at=retrieved_at,
                                download_status="ok",
                            )
                            image_by_sha[digest] = image_row
                        except Exception as exc:
                            image_row["download_status"] = "failed"
                            image_row["notes"] = f"{type(exc).__name__}: {exc}"

                    images[image_id] = image_row
                    image_by_source_url[candidate.url] = image_row
                    article_row["image_ids"].append(image_id)

                article_row["parse_status"] = "ok" if article_row["image_ids"] else "no_images"
                succeeded += 1
            except Exception as exc:
                article_row["error"] = f"{type(exc).__name__}: {exc}"
                failed += 1
            articles[article_row["article_id"]] = article_row
            current_by_url[str(article_row.get("canonical_url") or article_url)] = article_row

        write_jsonl(article_manifest, articles.values(), "article_id")
        write_jsonl(image_manifest, images.values(), "image_id")
    finally:
        if own_session:
            session.close()

    report = {
        "schema_name": "lpo_visual_reference_ingestion.v1",
        "status": "ok" if failed == 0 else ("partial" if succeeded else "failed"),
        "processed_article_count": processed,
        "succeeded_article_count": succeeded,
        "failed_article_count": failed,
        "unique_article_manifest_count": len(articles),
        "unique_image_manifest_count": len(images),
        "downloaded_file_count": downloaded,
        "reused_count": reused,
        "article_manifest": str(article_manifest),
        "image_manifest": str(image_manifest),
        "output_root": str(output_root),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", default=[], help="Public LPO article URL; repeatable")
    parser.add_argument("--input-file", type=Path, help="Text file containing one article URL per line")
    parser.add_argument("--from-rss-config", type=Path, help="Collect article URLs from a sensing_feeds.v1 YAML file")
    parser.add_argument("--output-root", type=Path, default=Path("visuals/references"))
    parser.add_argument("--limit", type=int, default=None, help="Maximum article URLs to process")
    parser.add_argument("--max-images-per-article", type=int, default=6)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--user-agent", default=DEFAULT_UA)
    parser.add_argument("--reingest-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    urls = list(args.url)
    if args.input_file:
        urls.extend(
            line.strip()
            for line in args.input_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    if args.from_rss_config:
        urls.extend(collect_urls_from_rss(args.from_rss_config, limit=args.limit))

    normalized: list[str] = []
    seen: set[str] = set()
    for value in urls:
        url = normalize_url(value)
        if not url or url in seen:
            continue
        seen.add(url)
        normalized.append(url)
        if args.limit is not None and len(normalized) >= args.limit:
            break

    if not normalized:
        print("No LPO article URLs supplied or discovered.", file=sys.stderr)
        return 2

    report = ingest(
        urls=normalized,
        output_root=args.output_root,
        timeout=args.timeout,
        user_agent=args.user_agent,
        max_images_per_article=args.max_images_per_article,
        reingest_existing=args.reingest_existing,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
    return 0 if report["status"] in {"ok", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
