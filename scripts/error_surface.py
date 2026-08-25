#!/usr/bin/env python3
"""Small, secret-conscious helpers for promoting useful subprocess failures.

The pipeline intentionally keeps full stdout/stderr in immutable telemetry logs. This
module chooses one concise root-cause line for human-facing CLIs without dumping full
provider output or credentials.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

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
SEMANTIC_MARKERS = (
    "] ERROR:",
    "ValueError:",
    "RuntimeError:",
    "AssertionError:",
    "ERROR:",
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
