#!/usr/bin/env python3
"""Run a configured outlet's governed AI editorial node.

Southland is the first workflow.  The AI runtime is provider-neutral; Microsoft
Agent Framework is the current execution backend.  Raw execution evidence stays
Level 0 while accepted output is adapted into existing editorial contracts.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.news_editorial.src.news_editorial.ai_runtime import StructuredAIBackend, StructuredAINode
from apps.news_editorial.src.news_editorial.draft_bus_writer import write_article_draft
from apps.news_editorial.src.news_editorial.maf_backend import MAFOpenAIBackend
from apps.news_editorial.src.news_editorial.piece_brief_bus import write_piece_brief
from apps.news_editorial.src.news_editorial.slugs import slugify
from apps.news_editorial.src.news_editorial.southland_workflow import (
    WORKFLOW_ID,
    EvidencePacket,
    SouthlandEditorialNode,
    SouthlandRunEvidence,
    ai_result_record,
)
from scripts.build_editorial_access_indexes import build_editorial_index
from scripts.outlet_runtime import resolve_outlet_runtime


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    yield value


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_policy(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != "editorial_ai.v1":
        raise ValueError(f"{path}: expected schema_version editorial_ai.v1")
    if value.get("workflow_id") != WORKFLOW_ID:
        raise ValueError(
            f"{path}: workflow_id={value.get('workflow_id')!r} does not match {WORKFLOW_ID!r}"
        )
    backend = value.get("backend")
    execution = value.get("execution")
    if not isinstance(backend, dict) or not isinstance(execution, dict):
        raise ValueError(f"{path}: backend and execution must be objects")
    if backend.get("kind") != "maf_openai":
        raise ValueError(f"{path}: unsupported backend.kind={backend.get('kind')!r}")
    for key in (
        "provider_concurrency",
        "story_concurrency",
        "max_attempts",
        "max_revisions",
        "minimum_inputs",
        "publish_candidate_target",
    ):
        if not isinstance(execution.get(key), int):
            raise ValueError(f"{path}: execution.{key} must be an integer")
    return value


def _make_backend(policy: dict[str, Any]) -> StructuredAIBackend:
    backend = policy["backend"]
    model_env = str(backend.get("model_env") or "").strip()
    api_key_env = str(backend.get("api_key_env") or "").strip()
    if not model_env:
        raise ValueError("backend.model_env is required")
    model = os.getenv(model_env, "").strip()
    if not model:
        raise ValueError(f"AI model is not configured: set {model_env}")
    api_key = os.getenv(api_key_env, "").strip() if api_key_env else None
    if api_key_env and not api_key:
        raise ValueError(f"AI provider key is not configured: set {api_key_env}")
    return MAFOpenAIBackend(model=model, api_key=api_key)


def _load_quality_ids(storage_dir: Path, digest_at: str) -> set[str]:
    report_path = storage_dir / "observability" / "selected_enrichment_latest.json"
    if not report_path.is_file():
        raise ValueError(f"missing milestone-2 enrichment report: {report_path}")
    report = _read_json(report_path)
    if report.get("digest_at") != digest_at:
        raise ValueError(
            f"{report_path}: digest_at={report.get('digest_at')} does not match {digest_at}"
        )
    return {
        str(row.get("index_id") or "")
        for row in (report.get("results") or [])
        if isinstance(row, dict) and row.get("quality_ok") is True
    }


def _latest_scraped_by_id(storage_dir: Path) -> dict[str, dict[str, Any]]:
    bus_dir = storage_dir / "buses" / "scraped_article" / "v1"
    latest: dict[str, dict[str, Any]] = {}
    if not bus_dir.exists():
        return latest
    for path in sorted(bus_dir.glob("*.jsonl")):
        for row in _iter_jsonl(path):
            if row.get("schema_name") != "scraped_article.v1":
                continue
            if row.get("fetch_status") != "success":
                continue
            index_id = str(row.get("index_id") or "").strip()
            if not index_id:
                continue
            previous = latest.get(index_id)
            if previous is None or str(row.get("fetched_at") or "") >= str(
                previous.get("fetched_at") or ""
            ):
                latest[index_id] = row
    return latest


def load_evidence_packets(
    *,
    storage_dir: Path,
    digest_at: str,
) -> list[EvidencePacket]:
    selection_path = storage_dir / "indexes" / "editorial_selection_latest.json"
    if not selection_path.is_file():
        raise ValueError(f"missing editorial selection: {selection_path}")
    selection = _read_json(selection_path)
    if selection.get("digest_at") != digest_at:
        raise ValueError(
            f"{selection_path}: digest_at={selection.get('digest_at')} does not match {digest_at}"
        )

    quality_ids = _load_quality_ids(storage_dir, digest_at)
    scraped = _latest_scraped_by_id(storage_dir)
    packets: list[EvidencePacket] = []
    for selected in selection.get("selected") or []:
        if not isinstance(selected, dict):
            continue
        index_id = str(selected.get("index_id") or "").strip()
        if not index_id or index_id not in quality_ids:
            continue
        article = scraped.get(index_id)
        if not article or not str(article.get("text") or "").strip():
            continue
        packets.append(
            EvidencePacket(
                index_id=index_id,
                digest_at=digest_at,
                title=str(article.get("title") or selected.get("title") or "").strip(),
                source=str(article.get("source") or selected.get("source") or "").strip(),
                topic=str(article.get("topic") or selected.get("topic") or "All Topics").strip(),
                source_url=str(article.get("source_url") or selected.get("link") or "").strip(),
                fetched_at=str(article.get("fetched_at") or "").strip(),
                text_hash=str(article.get("text_hash") or "").strip(),
                text=str(article.get("text") or "").strip(),
            )
        )
    return packets


def _stable_id(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    return prefix + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _materialize_accepted(
    *,
    runtime,
    packet: EvidencePacket,
    run: SouthlandRunEvidence,
    created_at: str,
) -> tuple[Path, Path]:
    result = run.result
    if result.status != "accepted" or not result.analysis or not result.decision:
        raise ValueError("cannot materialize non-accepted Southland result")
    if not result.draft or not result.review:
        raise ValueError("accepted Southland result is missing draft/review")

    brief_id = _stable_id(
        "npb_southland_",
        WORKFLOW_ID,
        packet.index_id,
        packet.text_hash,
    )
    source_ref = {
        "index_id": packet.index_id,
        "article_id": packet.index_id,
        "title": packet.title,
        "source": packet.source,
        "url": packet.source_url,
    }
    controversies = _dedupe_strings(
        result.analysis.risk_flags
        + result.analysis.publisher_interpretations
        + result.analysis.uncertainties
        + result.analysis.attributed_claims
    )
    brief = {
        "schema_name": "news_piece_brief.v1",
        "schema_status": "experimental_structured",
        "brief_id": brief_id,
        "digest_id_hour": packet.digest_at,
        "digest_group_id": f"southland::{packet.index_id}",
        "digest_file": f"southland_ai_{packet.digest_at}",
        "topic": packet.topic,
        "working_title": result.draft.title,
        "angle": result.decision.comic_mechanism or result.decision.reason,
        "key_facts": result.analysis.factual_kernel,
        "potential_controversies": controversies,
        "relevant_quotes": [],
        "source_index_ids": [packet.index_id],
        "source_refs": [source_ref],
        "meta": {
            "editorial_mode": "satirical_mirror",
            "workflow_id": WORKFLOW_ID,
            "source_text_hash": packet.text_hash,
            "southland": {
                "analysis": result.analysis.model_dump(mode="json"),
                "decision": result.decision.model_dump(mode="json"),
                "review": result.review.model_dump(mode="json"),
                "revisions_used": result.revisions_used,
            },
            "ai": {
                "stage_work_ids": result.stage_work_ids,
                "backend": run.ai_results[-1].backend if run.ai_results else "",
                "provider": run.ai_results[-1].provider if run.ai_results else "",
                "model": run.ai_results[-1].model if run.ai_results else "",
            },
        },
    }
    brief_path = write_piece_brief(
        brief,
        bus_dir=runtime.storage_dir / "buses" / "news_piece_brief" / "v1",
    )

    draft = result.draft
    draft_id = _stable_id("southland_draft_", brief_id, packet.index_id)
    slug_candidate = slugify(draft.title) or draft_id
    sections = [
        {
            "section_id": f"sec_{ordinal}",
            "heading": section.heading,
            "summary": section.summary,
        }
        for ordinal, section in enumerate(draft.sections, start=1)
    ]
    revision_notes = _dedupe_strings(
        draft.revision_notes
        + result.review.notes
        + [f"Generated through {WORKFLOW_ID}; human approval still required."]
    )
    article = {
        "schema_name": "news_article_draft.v1",
        "schema_status": "experimental_structured",
        "draft_id": draft_id,
        "digest_at": packet.digest_at,
        "story_group_id": f"southland::{packet.index_id}",
        "brief_id": brief_id,
        "title": draft.title,
        "slug_candidate": slug_candidate,
        "summary": draft.summary,
        "dek": draft.dek,
        "lede": draft.lede,
        "sections": sections,
        "body_md": draft.body_md,
        "body_markdown": draft.body_md,
        "source_links": [packet.source_url],
        "source_ids": [packet.index_id],
        "topic": packet.topic,
        "status": "draft",
        "created_at": created_at,
        "citations": [
            {
                "citation_id": "source_1",
                "claim_text": "Source article underlying this satirical transformation.",
                "source_ref_id": packet.index_id,
                "url": packet.source_url,
            }
        ],
        "fact_check_flags": [
            flag.model_dump(mode="json") for flag in draft.fact_check_flags
        ],
        "revision_notes": revision_notes,
    }
    draft_path = write_article_draft(
        article,
        bus_dir=runtime.storage_dir / "buses" / "news_article_draft" / "v1",
    )
    return brief_path, draft_path


def _write_run_evidence(
    *,
    data_dir: Path,
    packet: EvidencePacket,
    run: SouthlandRunEvidence,
) -> Path:
    evidence_id = _stable_id(
        "southland_ai_",
        WORKFLOW_ID,
        packet.index_id,
        packet.text_hash,
    )
    path = data_dir / "ai_runs" / packet.digest_at / f"{evidence_id}.jsonl"
    row = {
        "schema_name": "editorial_ai_run.v1",
        "schema_status": "level0_runtime_evidence",
        "workflow_id": WORKFLOW_ID,
        "index_id": packet.index_id,
        "source_text_hash": packet.text_hash,
        "result": run.result.model_dump(mode="json"),
        "ai_calls": [ai_result_record(value) for value in run.ai_results],
    }
    _atomic_jsonl(path, [row])
    return path


async def run_outlet_ai(
    *,
    repo_root: Path,
    site_id: str,
    digest_at: str,
    created_at: str,
    backend: StructuredAIBackend | None = None,
) -> tuple[dict[str, Any], int]:
    runtime = resolve_outlet_runtime(repo_root, site_id)
    policy = _load_policy(runtime.require_ai_config())
    execution = policy["execution"]
    packets = load_evidence_packets(
        storage_dir=runtime.storage_dir,
        digest_at=digest_at,
    )
    minimum_inputs = int(execution["minimum_inputs"])
    if len(packets) < minimum_inputs:
        raise ValueError(
            f"only {len(packets)} clean evidence packets available; minimum_inputs={minimum_inputs}"
        )

    selected_backend = backend or _make_backend(policy)
    ai_node = StructuredAINode(
        selected_backend,
        concurrency=int(execution["provider_concurrency"]),
        max_attempts=int(execution["max_attempts"]),
    )
    editorial_node = SouthlandEditorialNode(
        ai_node,
        story_concurrency=int(execution["story_concurrency"]),
        max_revisions=int(execution["max_revisions"]),
    )
    runs = await editorial_node.run_many(packets)

    accepted = rejected = failed = 0
    briefs: list[str] = []
    drafts: list[str] = []
    evidence_paths: list[str] = []
    item_results: list[dict[str, Any]] = []

    for packet, run in zip(packets, runs, strict=True):
        evidence_path = _write_run_evidence(
            data_dir=runtime.data_dir,
            packet=packet,
            run=run,
        )
        evidence_paths.append(str(evidence_path))
        status = run.result.status
        if status == "accepted":
            accepted += 1
            brief_path, draft_path = _materialize_accepted(
                runtime=runtime,
                packet=packet,
                run=run,
                created_at=created_at,
            )
            briefs.append(str(brief_path))
            drafts.append(str(draft_path))
        elif status == "rejected":
            rejected += 1
        else:
            failed += 1

        item_results.append(
            {
                "index_id": packet.index_id,
                "status": status,
                "revisions_used": run.result.revisions_used,
                "stage_work_ids": run.result.stage_work_ids,
                "error": run.result.error,
            }
        )

    editorial_index = build_editorial_index(
        runtime.storage_dir,
        runtime.data_dir,
        digest_at,
    )
    target = int(execution["publish_candidate_target"])
    readiness = "ready" if accepted >= target else "below_target"
    status = "failed" if failed == len(runs) else ("partial" if failed else "ok")
    report = {
        "schema_name": "outlet_editorial_ai.v1",
        "status": status,
        "site_id": site_id,
        "digest_at": digest_at,
        "workflow_id": WORKFLOW_ID,
        "backend": selected_backend.backend_name,
        "provider": selected_backend.provider_name,
        "model": selected_backend.model_name,
        "input_count": len(packets),
        "accepted_count": accepted,
        "rejected_count": rejected,
        "failed_count": failed,
        "publish_candidate_target": target,
        "publish_readiness": readiness,
        "brief_paths": briefs,
        "draft_paths": drafts,
        "level0_evidence_paths": evidence_paths,
        "editorial_index": str(editorial_index),
        "items": item_results,
    }
    _atomic_json(
        runtime.storage_dir / "observability" / "editorial_ai_latest.json",
        report,
    )
    return report, 1 if status == "failed" else 0


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--site-id", default="southland")
    parser.add_argument("--digest-at", required=True)
    parser.add_argument("--created-at", default=None)
    args = parser.parse_args()
    try:
        report, code = asyncio.run(
            run_outlet_ai(
                repo_root=args.repo_root,
                site_id=args.site_id,
                digest_at=args.digest_at,
                created_at=args.created_at or _utc_now(),
            )
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "schema_name": "outlet_editorial_ai.v1",
                    "status": "failed",
                    "site_id": args.site_id,
                    "digest_at": args.digest_at,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
