#!/usr/bin/env python3
"""Small deployment-provider readiness checks shared by human operator paths."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

MIN_VERCEL_CLI = (47, 2, 2)
MIN_VERCEL_CLI_TEXT = ".".join(str(value) for value in MIN_VERCEL_CLI)
_VERSION_RE = re.compile(r"(?i)(?:vercel\s+cli\s+)?v?(\d+)\.(\d+)\.(\d+)")


def parse_vercel_version(*chunks: str) -> tuple[int, int, int] | None:
    for chunk in chunks:
        match = _VERSION_RE.search(chunk or "")
        if match:
            return tuple(int(match.group(index)) for index in range(1, 4))
    return None


def format_version(version: tuple[int, int, int]) -> str:
    return ".".join(str(value) for value in version)


def vercel_cli_preflight(
    runner: Callable,
    *,
    cwd: Path,
) -> dict:
    remediation = "upgrade with `pnpm add -g vercel@latest` (or `npm i -g vercel@latest`)"
    try:
        result = runner(["vercel", "--version"], cwd=cwd, env=None)
    except OSError as exc:
        return {
            "status": "failed",
            "version": None,
            "minimum_version": MIN_VERCEL_CLI_TEXT,
            "error": f"Vercel CLI unavailable: {exc}; {remediation}",
            "remediation": remediation,
        }

    if result.exit_code:
        detail = (result.stderr or result.stdout or "vercel --version failed").strip().splitlines()[-1]
        return {
            "status": "failed",
            "version": None,
            "minimum_version": MIN_VERCEL_CLI_TEXT,
            "error": f"Vercel CLI version check failed: {detail}; {remediation}",
            "remediation": remediation,
        }

    version = parse_vercel_version(result.stdout, result.stderr)
    if version is None:
        return {
            "status": "failed",
            "version": None,
            "minimum_version": MIN_VERCEL_CLI_TEXT,
            "error": f"Could not parse Vercel CLI version; require >= {MIN_VERCEL_CLI_TEXT}; {remediation}",
            "remediation": remediation,
        }

    current = format_version(version)
    if version < MIN_VERCEL_CLI:
        return {
            "status": "failed",
            "version": current,
            "minimum_version": MIN_VERCEL_CLI_TEXT,
            "error": f"Vercel CLI {current} is below required {MIN_VERCEL_CLI_TEXT}; {remediation}",
            "remediation": remediation,
        }

    return {
        "status": "ok",
        "version": current,
        "minimum_version": MIN_VERCEL_CLI_TEXT,
        "error": None,
        "remediation": remediation,
    }
