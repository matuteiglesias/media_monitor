#!/usr/bin/env python3
"""Secret-conscious helpers for promoting useful subprocess telemetry.

The pipeline keeps detailed stdout/stderr in local telemetry logs. This module chooses
concise human-facing summaries without dumping credentials and resolves wrapped stage
history for one live digest.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
RUN_RECORD_RE = re.compile(
    r"\[run-record\] ERROR lane=(?P<lane>\S+) stage=(?P<stage>\S+) exit=(?P<exit>\d+) "
    r"root_cause=(?P<summary>.*?) log=(?P<log>\S+)\s*$"
)
SECRET_PATTERNS = (
    re.compile(r"(?i)(--token\s+)(\S+)"),
    re.compile(r"(?i)\b(token|password|secret|api[_-]?key)=([^\s]+)"),
    re.compile(r"(?i)\b(bearer\s+)([A-Za-z0-9._~+/=-]+)"),
)
NOISE_PREFIXES = (
    "make: ***",
    "Traceback (most recent call last):",
)
# These messages are more useful than a later generic wrapper such as
# "Error: Upload aborted" or "Command npm run build exited with 1".
ACTIONABLE_PATTERNS = (
    re.compile(r"(?i)vercel cli version is outdated"),
    re.compile(r"(?i)requires version \d+\.\d+\.\d+ or later"),
    re.compile(r"(?i)found invalid node\.js version"),
    re.compile(r"(?i)unhandledschemeerror"),
    re.compile(r"(?i)module build failed"),
    re.compile(r"(?i)selected \d+ signals; minimum_items=\d+"),
)
SEMANTIC_MARKERS = (
    "] ERROR:",
    "ValueError:",
    "RuntimeError:",
    "AssertionError:",
    "Error:",
    "ERROR:",
    "ERR!",
)


@dataclass(frozen=True)
class FailureDetails:
    summary: str
    lane: str | None = None
    stage: str | None = None
    log_path: str | None = None


def redact(text: str) -> str:
    value = ANSI_RE.sub("", text)
    value = SECRET_PATTERNS[0].sub(r"\1[REDACTED]", value)
    value = SECRET_PATTERNS[1].sub(lambda match: f"{match.group(1)}=[REDACTED]", value)
    value = SECRET_PATTERNS[2].sub(r"\1[REDACTED]", value)
    return value


def _clean_lines(*chunks: str) -> list[str]:
    lines: list[str] = []
    for chunk in chunks:
        for raw in redact(chunk or "").splitlines():
            line = " ".join(raw.strip().split())
            if line:
                lines.append(line)
    return lines


def summarize_failure(stdout: str, stderr: str, fallback: str = "command failed") -> str:
    lines = _clean_lines(stdout, stderr)
    for line in reversed(lines):
        marker = RUN_RECORD_RE.search(line)
        if marker:
            return marker.group("summary")[:700]
    for pattern in ACTIONABLE_PATTERNS:
        for line in lines:
            if pattern.search(line):
                return line[:700]
    for marker_text in SEMANTIC_MARKERS:
        for line in reversed(lines):
            if marker_text in line:
                return line[:700]
    for line in reversed(lines):
        if not line.startswith(NOISE_PREFIXES):
            return line[:700]
    return fallback


def failure_details(stdout: str, stderr: str, fallback: str = "command failed") -> FailureDetails:
    lines = _clean_lines(stdout, stderr)
    for line in reversed(lines):
        marker = RUN_RECORD_RE.search(line)
        if marker:
            return FailureDetails(
                summary=marker.group("summary")[:700],
                lane=marker.group("lane"),
                stage=marker.group("stage"),
                log_path=marker.group("log"),
            )
    return FailureDetails(summary=summarize_failure(stdout, stderr, fallback))


def _parse_time(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _display_path(repo_root: Path, value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        path = repo_root / path
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def wrapped_stage_timeline(
    repo_root: Path,
    *,
    lane: str,
    digest_at: str,
    since: datetime | None = None,
) -> list[dict]:
    """Return ordered immutable wrapped-stage telemetry for one lane/digest/attempt."""
    manifests_dir = repo_root / "storage/observability/manifests"
    if not manifests_dir.exists():
        return []

    rows: list[dict] = []
    for manifest_path in manifests_dir.glob("*.json"):
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("lane") != lane:
            continue
        command = payload.get("command")
        command_text = " ".join(str(value) for value in command) if isinstance(command, list) else str(command or "")
        if digest_at not in command_text:
            continue
        started = _parse_time(payload.get("started_at"))
        if since is not None and (started is None or started < since):
            continue
        ended = _parse_time(payload.get("ended_at"))
        duration_ms = None
        if started is not None and ended is not None:
            duration_ms = max(0, round((ended - started).total_seconds() * 1000))
        log_path = _display_path(repo_root, payload.get("log_path"))
        rows.append(
            {
                "lane": lane,
                "stage": str(payload.get("stage") or "unknown"),
                "status": str(payload.get("status") or "unknown"),
                "started_at": payload.get("started_at"),
                "completed_at": payload.get("ended_at"),
                "duration_ms": duration_ms,
                "log_path": log_path,
            }
        )
    rows.sort(key=lambda row: (str(row.get("started_at") or ""), str(row.get("stage") or "")))
    return rows


def latest_failed_stage(
    repo_root: Path,
    *,
    lane: str,
    digest_at: str,
    since: datetime | None = None,
) -> FailureDetails | None:
    """Resolve the newest failed wrapped command for one lane/digest/attempt."""
    timeline = wrapped_stage_timeline(repo_root, lane=lane, digest_at=digest_at, since=since)
    failed = [row for row in timeline if row.get("status") == "failed"]
    if not failed:
        return None
    row = failed[-1]
    log_value = row.get("log_path")
    log_path = repo_root / str(log_value) if log_value else None
    log_text = ""
    if log_path is not None and log_path.exists():
        try:
            log_text = log_path.read_text(encoding="utf-8")
        except Exception:
            log_text = ""
    stage = str(row.get("stage") or "").strip() or None
    return FailureDetails(
        summary=summarize_failure(log_text, "", fallback=f"{stage or lane} failed"),
        lane=lane,
        stage=stage,
        log_path=str(log_value) if log_value else None,
    )
