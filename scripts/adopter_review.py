#!/usr/bin/env python3
"""Minimal human review surface for Media Monitor adopter/editorial pilots.

The tool materializes explicit draft files into a readable queue and records
operator decisions. Publishing remains behind the existing human approval gate;
an approve decision requires --approve-human and an explicit published bus
location so adopter tests cannot accidentally target the canonical outlet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import scripts.promote_draft_to_published as promote_module


DECISIONS = {"hold", "reject", "revise", "approve"}
QUEUE_SCHEMA = "media_monitor_review_queue.v1"
DECISION_SCHEMA = "media_monitor_editorial_review_decision.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def load_one_draft(path: Path) -> dict[str, Any]:
    rows = promote_module.read_jsonl_rows(path)
    if len(rows) != 1:
        raise ValueError(f"{path}: review queue requires exactly one draft row per file")
    draft = rows[0]
    promote_module.validate_draft(draft)
    return draft


def queue_item(path: Path, draft: dict[str, Any]) -> dict[str, Any]:
    return {
        "draft_id": draft["draft_id"],
        "digest_at": draft["digest_at"],
        "story_group_id": draft["story_group_id"],
        "title": draft["title"],
        "summary": draft["summary"],
        "body_md": draft["body_md"],
        "topic": draft["topic"],
        "source_links": draft["source_links"],
        "citations": draft.get("citations") or [],
        "fact_check_flags": draft.get("fact_check_flags") or [],
        "revision_notes": draft.get("revision_notes") or [],
        "draft_path": str(path),
        "draft_sha256": sha256_file(path),
        "allowed_decisions": ["hold", "reject", "revise", "approve"],
        "authority_note": "approve still requires explicit --approve-human at decision time",
    }


def render_queue_markdown(queue: dict[str, Any], *, decisions_path: Path, published_bus_dir: Path) -> str:
    lines = [
        "# Media Monitor Review Queue",
        "",
        f"Status: `{queue['status']}`",
        f"Draft count: **{queue['draft_count']}**",
        "",
        "This is an operator surface. Reading a draft or recording hold/reject/revise does not publish anything.",
        "Approval still requires the explicit human publication gate.",
        "",
    ]
    for index, item in enumerate(queue["items"], 1):
        lines.extend(
            [
                f"## {index}. {item['title']}",
                "",
                f"- draft id: `{item['draft_id']}`",
                f"- topic: `{item['topic']}`",
                f"- digest: `{item['digest_at']}`",
                f"- draft SHA-256: `{item['draft_sha256']}`",
                "",
                "### Summary",
                "",
                str(item["summary"]),
                "",
                "### Draft",
                "",
                str(item["body_md"]),
                "",
                "### Sources",
                "",
            ]
        )
        lines.extend(f"- {url}" for url in item["source_links"])
        lines.extend(["", "### Citations", ""])
        if item["citations"]:
            for citation in item["citations"]:
                claim = str(citation.get("claim_text") or "")
                url = str(citation.get("url") or "")
                lines.append(f"- {claim} — {url}")
        else:
            lines.append("- No structured citations attached.")
        lines.extend(["", "### Fact-check flags", ""])
        if item["fact_check_flags"]:
            for flag in item["fact_check_flags"]:
                lines.append(
                    f"- **{flag.get('severity', 'unknown')}**: {flag.get('flag', '')} — {flag.get('note', '')}"
                )
        else:
            lines.append("- None recorded on the draft.")
        lines.extend(["", "### Existing revision notes", ""])
        if item["revision_notes"]:
            lines.extend(f"- {note}" for note in item["revision_notes"])
        else:
            lines.append("- None.")

        base = (
            "python scripts/adopter_review.py decide "
            f"--draft {item['draft_path']} --decisions {decisions_path} "
            "--reviewer <name-or-role> --note '<reason>'"
        )
        lines.extend(
            [
                "",
                "### Decisions",
                "",
                "Hold:",
                "```bash",
                f"{base} --decision hold",
                "```",
                "Revise:",
                "```bash",
                f"{base} --decision revise",
                "```",
                "Reject:",
                "```bash",
                f"{base} --decision reject",
                "```",
                "Approve + publish to the explicitly isolated bus:",
                "```bash",
                f"{base} --decision approve --approve-human --published-bus-dir {published_bus_dir}",
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def materialize_queue(
    draft_paths: list[Path],
    *,
    out_dir: Path,
    decisions_path: Path,
    published_bus_dir: Path,
) -> dict[str, Any]:
    if not draft_paths:
        raise ValueError("at least one --draft is required")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in draft_paths:
        draft = load_one_draft(path)
        draft_id = str(draft["draft_id"])
        if draft_id in seen:
            raise ValueError(f"duplicate draft_id in review queue: {draft_id}")
        seen.add(draft_id)
        items.append(queue_item(path, draft))
    items.sort(key=lambda item: (str(item["digest_at"]), str(item["draft_id"])))
    queue = {
        "schema": QUEUE_SCHEMA,
        "status": "ready_for_human_review",
        "draft_count": len(items),
        "items": items,
        "decisions_path": str(decisions_path),
        "published_bus_dir": str(published_bus_dir),
        "publication_authority": "explicit_human_approval_required",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(out_dir / "review_queue.json", json_bytes(queue))
    atomic_write(
        out_dir / "review_queue.md",
        render_queue_markdown(queue, decisions_path=decisions_path, published_bus_dir=published_bus_dir).encode("utf-8"),
    )
    return queue


def read_decisions(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: decision row is not an object")
        rows.append(value)
    return rows


def append_decision(path: Path, record: dict[str, Any]) -> None:
    rows = read_decisions(path)
    rows.append(record)
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")
    atomic_write(path, payload)


def record_decision(
    *,
    draft_path: Path,
    decisions_path: Path,
    decision: str,
    reviewer: str,
    note: str,
    approve_human: bool = False,
    published_bus_dir: Path | None = None,
) -> dict[str, Any]:
    if decision not in DECISIONS:
        raise ValueError(f"unsupported decision: {decision}")
    if not reviewer.strip():
        raise ValueError("reviewer is required")
    if not note.strip():
        raise ValueError("review note/reason is required")
    draft = load_one_draft(draft_path)
    previous = [row for row in read_decisions(decisions_path) if row.get("draft_id") == draft["draft_id"]]
    if any(row.get("decision") == "approve" for row in previous):
        raise ValueError(f"draft {draft['draft_id']} already has an approve decision in {decisions_path}")

    article_id = None
    published_path = None
    if decision == "approve":
        if not approve_human:
            raise ValueError("refusing approve decision without --approve-human")
        if published_bus_dir is None:
            raise ValueError("approve requires explicit --published-bus-dir for adopter/operator safety")
        article, output = promote_module.promote(
            draft,
            "human_approved",
            published_bus=published_bus_dir,
        )
        article_id = article["article_id"]
        published_path = str(output)
    elif approve_human:
        raise ValueError("--approve-human is only valid with --decision approve")

    decided_at = utc_now()
    seed = f"{draft['draft_id']}|{decision}|{reviewer}|{decided_at}|{sha256_file(draft_path)}"
    record = {
        "schema": DECISION_SCHEMA,
        "decision_id": hashlib.sha256(seed.encode("utf-8")).hexdigest(),
        "draft_id": draft["draft_id"],
        "draft_sha256": sha256_file(draft_path),
        "decision": decision,
        "reviewer": reviewer,
        "note": note,
        "decided_at": decided_at,
        "publication_effect": "published" if decision == "approve" else "none",
        "article_id": article_id,
        "published_path": published_path,
    }
    append_decision(decisions_path, record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    queue_parser = sub.add_parser("materialize", help="build a human-readable review queue")
    queue_parser.add_argument("--draft", type=Path, action="append", required=True)
    queue_parser.add_argument("--out", type=Path, required=True)
    queue_parser.add_argument("--decisions", type=Path, required=True)
    queue_parser.add_argument("--published-bus-dir", type=Path, required=True)

    decide_parser = sub.add_parser("decide", help="record a governed operator decision")
    decide_parser.add_argument("--draft", type=Path, required=True)
    decide_parser.add_argument("--decisions", type=Path, required=True)
    decide_parser.add_argument("--decision", choices=sorted(DECISIONS), required=True)
    decide_parser.add_argument("--reviewer", required=True)
    decide_parser.add_argument("--note", required=True)
    decide_parser.add_argument("--approve-human", action="store_true")
    decide_parser.add_argument("--published-bus-dir", type=Path)

    args = parser.parse_args()
    try:
        if args.command == "materialize":
            result = materialize_queue(
                args.draft,
                out_dir=args.out,
                decisions_path=args.decisions,
                published_bus_dir=args.published_bus_dir,
            )
        else:
            result = record_decision(
                draft_path=args.draft,
                decisions_path=args.decisions,
                decision=args.decision,
                reviewer=args.reviewer,
                note=args.note,
                approve_human=args.approve_human,
                published_bus_dir=args.published_bus_dir,
            )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
