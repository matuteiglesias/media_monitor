#!/usr/bin/env python3
"""Prepare and evidence a governed adopter recipient brief without sending it.

AP5 deliberately separates three authorities:

1. prepare: build deterministic recipient artifacts from already-published,
   human-approved content;
2. authorize: record explicit human authorization for delivery, bound to the
   exact prepared manifest bytes;
3. record: after an external/human sender acts, record delivery evidence.

This module never sends email, calls a provider, or invents a recipient address.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from scripts.adopter_intake import load_intake, load_schema, require_valid
from scripts.build_site_snapshot import validate_schema as validate_site_snapshot_schema


DELIVERY_SCHEMA = "media_monitor_adopter_delivery.v1"
AUTH_SCHEMA = "media_monitor_delivery_authorization.v1"
RECEIPT_SCHEMA = "media_monitor_delivery_receipt.v1"
PREPARED_STATUS = "prepared_not_authorized"
AUTHORIZED_STATUS = "authorized_not_sent"
RECEIPT_STATUSES = {"sent", "delivered", "failed"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def parse_target_item_count(value: Any) -> tuple[int, int]:
    if isinstance(value, int) and not isinstance(value, bool):
        if value < 1:
            raise ValueError("target_item_count integer must be positive")
        return value, value
    text = str(value or "").strip()
    if re.fullmatch(r"\d+", text):
        number = int(text)
        if number < 1:
            raise ValueError("target_item_count must be positive")
        return number, number
    match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", text)
    if not match:
        raise ValueError(f"unsupported target_item_count: {value!r}; expected integer or N-M")
    lower, upper = (int(match.group(1)), int(match.group(2)))
    if lower < 1 or upper < lower:
        raise ValueError("target_item_count range must satisfy 1 <= lower <= upper")
    return lower, upper


def html_email_deliverable(intake: dict[str, Any]) -> dict[str, Any]:
    matches = [item for item in intake["deliverables"] if item.get("type") == "html_email_brief"]
    if len(matches) != 1:
        raise ValueError("AP5 html-email preparation requires exactly one html_email_brief deliverable")
    return matches[0]


def load_snapshot(path: Path) -> dict[str, Any]:
    snapshot = load_json(path)
    validate_site_snapshot_schema(snapshot)
    if snapshot.get("schema_name") != "site_snapshot.v4" or snapshot.get("status") != "ok":
        raise ValueError("recipient brief requires an ok site_snapshot.v4")
    return snapshot


def approved_articles(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    latest = (snapshot.get("publication") or {}).get("latest")
    articles = snapshot.get("articles")
    if not isinstance(latest, list) or not isinstance(articles, dict):
        raise ValueError("snapshot publication/latest articles surfaces are invalid")

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ref in latest:
        if not isinstance(ref, dict):
            raise ValueError("snapshot publication.latest row is not an object")
        slug = str(ref.get("slug") or "").strip()
        article = articles.get(slug)
        if not isinstance(article, dict):
            raise ValueError(f"published ref {slug!r} has no corresponding article body")
        if article.get("article_id") != ref.get("article_id"):
            raise ValueError(f"published ref {slug!r} article_id does not match article body")
        if article.get("status") != "published" or article.get("review_status") != "human_approved":
            raise ValueError(f"article {article.get('article_id')} is not human-approved published content")
        article_id = str(article.get("article_id") or "")
        if article_id in seen:
            continue
        seen.add(article_id)
        result.append(article)
    return result


def _article_source_links(article: dict[str, Any]) -> list[str]:
    links = [str(value).strip() for value in article.get("source_links") or [] if str(value).strip()]
    if not links:
        raise ValueError(f"article {article.get('article_id')} has no source links")
    return links


def render_html_brief(intake: dict[str, Any], articles: list[dict[str, Any]], snapshot: dict[str, Any]) -> str:
    brand = html.escape(str(intake["identity"]["name"]))
    locale = html.escape(str(intake["identity"]["locale"]))
    digest_at = html.escape(str(snapshot["digest_at"]))
    rows: list[str] = []
    for article in articles:
        title = html.escape(str(article["title"]))
        summary = html.escape(str(article["summary"]))
        topic = html.escape(str(article["topic"]))
        published_at = html.escape(str(article["published_at"]))
        links = _article_source_links(article)
        source_html = "".join(
            f'<li><a href="{html.escape(url, quote=True)}">{html.escape(url)}</a></li>' for url in links
        )
        rows.append(
            "\n".join(
                [
                    '<article style="margin:0 0 24px 0;padding:0 0 18px 0;border-bottom:1px solid #ddd">',
                    f"<h2 style=\"margin:0 0 6px 0\">{title}</h2>",
                    f"<p style=\"margin:0 0 8px 0;color:#555\"><strong>{topic}</strong> · {published_at}</p>",
                    f"<p style=\"margin:0 0 10px 0\">{summary}</p>",
                    "<p style=\"margin:0 0 4px 0\"><strong>Sources</strong></p>",
                    f"<ul style=\"margin-top:0\">{source_html}</ul>",
                    "</article>",
                ]
            )
        )
    return "\n".join(
        [
            "<!doctype html>",
            f'<html lang="{locale}">',
            '<meta charset="utf-8">',
            f"<title>{brand} — briefing</title>",
            '<body style="font-family:Arial,Helvetica,sans-serif;max-width:760px;margin:24px auto;padding:0 16px;line-height:1.45;color:#111">',
            f"<h1 style=\"margin-bottom:4px\">{brand}</h1>",
            "<p style=\"margin-top:0;color:#555\">Recipient briefing · human-approved published content only</p>",
            f"<p style=\"font-size:13px;color:#666\">Source digest: {digest_at}</p>",
            *rows,
            '<p style="font-size:12px;color:#666">Prepared artifact only. Delivery is a separate explicitly authorized action.</p>',
            "</body>",
            "</html>",
            "",
        ]
    )


def render_text_brief(intake: dict[str, Any], articles: list[dict[str, Any]], snapshot: dict[str, Any]) -> str:
    lines = [
        str(intake["identity"]["name"]),
        "Recipient briefing — human-approved published content only",
        f"Source digest: {snapshot['digest_at']}",
        "",
    ]
    for index, article in enumerate(articles, 1):
        lines.extend(
            [
                f"{index}. {article['title']}",
                f"Topic: {article['topic']}",
                f"Published: {article['published_at']}",
                str(article["summary"]),
                "Sources:",
            ]
        )
        lines.extend(f"- {url}" for url in _article_source_links(article))
        lines.append("")
    lines.append("Prepared artifact only. Delivery is a separate explicitly authorized action.")
    lines.append("")
    return "\n".join(lines)


def prepare_delivery(
    intake_path: Path,
    snapshot_path: Path,
    out_dir: Path,
    *,
    replace: bool = False,
    prepared_at: str | None = None,
) -> dict[str, Any]:
    intake = load_intake(intake_path)
    require_valid(intake, load_schema())
    snapshot = load_snapshot(snapshot_path)
    deliverable = html_email_deliverable(intake)
    lower, upper = parse_target_item_count(deliverable.get("target_item_count"))

    articles = approved_articles(snapshot)
    if len(articles) < lower:
        raise ValueError(
            f"snapshot has {len(articles)} human-approved published articles; target requires at least {lower}"
        )
    selected = articles[:upper]

    if intake["editorial_authority"].get("evidence_links_required"):
        for article in selected:
            _article_source_links(article)

    if out_dir.exists():
        if not replace:
            raise ValueError(f"output already exists: {out_dir}; pass --replace to rebuild")
        import shutil

        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=False)

    html_path = out_dir / "brief.html"
    text_path = out_dir / "brief.txt"
    html_payload = render_html_brief(intake, selected, snapshot).encode("utf-8")
    text_payload = render_text_brief(intake, selected, snapshot).encode("utf-8")
    atomic_write(html_path, html_payload)
    atomic_write(text_path, text_payload)

    manifest = {
        "schema": DELIVERY_SCHEMA,
        "status": PREPARED_STATUS,
        "send_eligible": False,
        "delivery_authorization_required": bool(
            intake["editorial_authority"].get("human_approval_required_for_delivery")
        ),
        "delivery_authorization_status": "not_recorded",
        "delivery_channel": "html_email_brief",
        "organization": intake["organization"]["name"],
        "recipient_role": intake["organization"]["primary_recipient_role"],
        "recipient_address": None,
        "identity_name": intake["identity"]["name"],
        "locale": intake["identity"]["locale"],
        "cadence": deliverable["cadence"],
        "delivery_window_local": deliverable.get("delivery_window_local"),
        "target_item_count": deliverable.get("target_item_count"),
        "item_count": len(selected),
        "content_authority": "published_article.v1_human_approved_only",
        "source_intake_sha256": canonical_sha256(intake),
        "source_snapshot_id": snapshot["snapshot_id"],
        "source_snapshot_sha256": sha256_file(snapshot_path),
        "source_digest_at": snapshot["digest_at"],
        "article_ids": [article["article_id"] for article in selected],
        "brief_html": "brief.html",
        "brief_html_sha256": hashlib.sha256(html_payload).hexdigest(),
        "brief_text": "brief.txt",
        "brief_text_sha256": hashlib.sha256(text_payload).hexdigest(),
        "prepared_at": prepared_at or utc_now(),
        "delivery_status": "not_sent",
        "provider_message_ref": None,
        "evidence_note": "This manifest proves recipient-artifact preparation only, not authorization, sending or receipt.",
    }
    write_json(out_dir / "delivery_manifest.json", manifest)
    return manifest


def authorize_delivery(
    manifest_path: Path,
    authorization_path: Path,
    *,
    reviewer: str,
    note: str,
    approve_delivery_human: bool,
    authorized_at: str | None = None,
) -> dict[str, Any]:
    if not approve_delivery_human:
        raise ValueError("refusing delivery authorization without --approve-delivery-human")
    if not reviewer.strip():
        raise ValueError("reviewer is required")
    if not note.strip():
        raise ValueError("authorization note is required")
    manifest = load_json(manifest_path)
    if manifest.get("schema") != DELIVERY_SCHEMA or manifest.get("status") != PREPARED_STATUS:
        raise ValueError("authorization requires a prepared Media Monitor delivery manifest")
    if manifest.get("delivery_status") != "not_sent":
        raise ValueError("cannot authorize a manifest that already records a delivery status")

    authorization = {
        "schema": AUTH_SCHEMA,
        "status": AUTHORIZED_STATUS,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "brief_html_sha256": manifest["brief_html_sha256"],
        "brief_text_sha256": manifest["brief_text_sha256"],
        "source_snapshot_id": manifest["source_snapshot_id"],
        "reviewer": reviewer,
        "note": note,
        "authorized_at": authorized_at or utc_now(),
        "authority": "explicit_human_delivery_authorization",
        "external_send_performed": False,
    }
    write_json(authorization_path, authorization)
    return authorization


def read_receipts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: receipt row is not an object")
        result.append(value)
    return result


def append_receipt(path: Path, record: dict[str, Any]) -> None:
    rows = read_receipts(path)
    rows.append(record)
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")
    atomic_write(path, payload)


def record_delivery(
    manifest_path: Path,
    authorization_path: Path,
    receipts_path: Path,
    *,
    status: str,
    actor: str,
    provider_message_ref: str | None,
    note: str,
    occurred_at: str | None = None,
) -> dict[str, Any]:
    if status not in RECEIPT_STATUSES:
        raise ValueError(f"unsupported delivery status: {status}")
    if not actor.strip():
        raise ValueError("actor is required")
    if not note.strip():
        raise ValueError("receipt note is required")
    if status in {"sent", "delivered"} and not str(provider_message_ref or "").strip():
        raise ValueError(f"{status} receipt requires provider_message_ref")

    manifest = load_json(manifest_path)
    authorization = load_json(authorization_path)
    manifest_sha = sha256_file(manifest_path)
    if manifest.get("schema") != DELIVERY_SCHEMA:
        raise ValueError("receipt requires a Media Monitor delivery manifest")
    if authorization.get("schema") != AUTH_SCHEMA or authorization.get("status") != AUTHORIZED_STATUS:
        raise ValueError("receipt requires a valid delivery authorization")
    if authorization.get("manifest_sha256") != manifest_sha:
        raise ValueError("delivery authorization does not match current manifest bytes")
    if authorization.get("brief_html_sha256") != manifest.get("brief_html_sha256"):
        raise ValueError("delivery authorization HTML hash does not match manifest")
    if authorization.get("brief_text_sha256") != manifest.get("brief_text_sha256"):
        raise ValueError("delivery authorization text hash does not match manifest")

    occurred = occurred_at or utc_now()
    seed = f"{manifest_sha}|{status}|{actor}|{provider_message_ref or ''}|{occurred}"
    record = {
        "schema": RECEIPT_SCHEMA,
        "receipt_id": hashlib.sha256(seed.encode("utf-8")).hexdigest(),
        "status": status,
        "manifest_sha256": manifest_sha,
        "authorization_sha256": sha256_file(authorization_path),
        "source_snapshot_id": manifest["source_snapshot_id"],
        "brief_html_sha256": manifest["brief_html_sha256"],
        "brief_text_sha256": manifest["brief_text_sha256"],
        "delivery_channel": manifest["delivery_channel"],
        "recipient_role": manifest["recipient_role"],
        "provider_message_ref": provider_message_ref,
        "actor": actor,
        "note": note,
        "occurred_at": occurred,
        "external_send_claim_source": "human_or_provider_supplied_evidence",
    }
    append_receipt(receipts_path, record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="prepare a recipient brief; never sends it")
    prepare.add_argument("--intake", type=Path, required=True)
    prepare.add_argument("--snapshot", type=Path, required=True)
    prepare.add_argument("--out", type=Path, required=True)
    prepare.add_argument("--replace", action="store_true")
    prepare.add_argument("--prepared-at")

    authorize = sub.add_parser("authorize", help="record explicit human authorization for delivery")
    authorize.add_argument("--manifest", type=Path, required=True)
    authorize.add_argument("--authorization", type=Path, required=True)
    authorize.add_argument("--reviewer", required=True)
    authorize.add_argument("--note", required=True)
    authorize.add_argument("--approve-delivery-human", action="store_true")
    authorize.add_argument("--authorized-at")

    record = sub.add_parser("record", help="record external delivery evidence after a sender/provider acts")
    record.add_argument("--manifest", type=Path, required=True)
    record.add_argument("--authorization", type=Path, required=True)
    record.add_argument("--receipts", type=Path, required=True)
    record.add_argument("--status", choices=sorted(RECEIPT_STATUSES), required=True)
    record.add_argument("--actor", required=True)
    record.add_argument("--provider-message-ref")
    record.add_argument("--note", required=True)
    record.add_argument("--occurred-at")

    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare_delivery(
                args.intake,
                args.snapshot,
                args.out,
                replace=args.replace,
                prepared_at=args.prepared_at,
            )
        elif args.command == "authorize":
            result = authorize_delivery(
                args.manifest,
                args.authorization,
                reviewer=args.reviewer,
                note=args.note,
                approve_delivery_human=args.approve_delivery_human,
                authorized_at=args.authorized_at,
            )
        else:
            result = record_delivery(
                args.manifest,
                args.authorization,
                args.receipts,
                status=args.status,
                actor=args.actor,
                provider_message_ref=args.provider_message_ref,
                note=args.note,
                occurred_at=args.occurred_at,
            )
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
