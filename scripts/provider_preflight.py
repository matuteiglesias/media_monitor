#!/usr/bin/env python3
"""Small deployment-provider readiness checks shared by human operator paths."""
from __future__ import annotations

import os
import re
import shutil
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


def _path_candidates(path_value: str | None = None) -> list[Path]:
    """Return distinct executable `vercel` candidates in PATH order."""
    raw_path = os.environ.get("PATH", "") if path_value is None else path_value
    rows: list[Path] = []
    seen: set[str] = set()
    for directory in raw_path.split(os.pathsep):
        if not directory:
            continue
        candidate = Path(directory).expanduser() / "vercel"
        try:
            if not candidate.is_file() or not os.access(candidate, os.X_OK):
                continue
        except OSError:
            continue
        text = str(candidate)
        if text in seen:
            continue
        seen.add(text)
        rows.append(candidate)
    return rows


def _candidate_versions(runner: Callable, *, cwd: Path, candidates: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for candidate in candidates:
        try:
            result = runner([str(candidate), "--version"], cwd=cwd, env=None)
        except Exception:
            continue
        version = parse_vercel_version(result.stdout, result.stderr) if result.exit_code == 0 else None
        rows.append(
            {
                "path": str(candidate),
                "version": format_version(version) if version is not None else None,
                "compatible": bool(version is not None and version >= MIN_VERCEL_CLI),
            }
        )
    return rows


def _shadow_remediation(selected_path: str | None, compatible: dict) -> str:
    compatible_path = str(compatible["path"])
    directory = str(Path(compatible_path).parent)
    if "/pnpm/bin" in compatible_path:
        return (
            f"PATH shadowing: selected {selected_path or 'vercel'} but compatible "
            f"{compatible_path} ({compatible.get('version')}) exists; set "
            f"`export PNPM_HOME=\"{directory}\"; export PATH=\"$PNPM_HOME:$PATH\"; hash -r`"
        )
    return (
        f"PATH shadowing: selected {selected_path or 'vercel'} but compatible "
        f"{compatible_path} ({compatible.get('version')}) exists; prepend `{directory}` to PATH and run `hash -r`"
    )


def vercel_cli_preflight(
    runner: Callable,
    *,
    cwd: Path,
    path_value: str | None = None,
) -> dict:
    remediation = "upgrade with `pnpm add -g vercel@latest` (or `npm i -g vercel@latest`)"
    selected_path = shutil.which("vercel", path=path_value)
    try:
        result = runner(["vercel", "--version"], cwd=cwd, env=None)
    except OSError as exc:
        return {
            "status": "failed",
            "version": None,
            "minimum_version": MIN_VERCEL_CLI_TEXT,
            "selected_path": selected_path,
            "candidates": [],
            "error": f"Vercel CLI unavailable: {exc}; {remediation}",
            "remediation": remediation,
        }

    if result.exit_code:
        detail = (result.stderr or result.stdout or "vercel --version failed").strip().splitlines()[-1]
        return {
            "status": "failed",
            "version": None,
            "minimum_version": MIN_VERCEL_CLI_TEXT,
            "selected_path": selected_path,
            "candidates": [],
            "error": f"Vercel CLI version check failed: {detail}; {remediation}",
            "remediation": remediation,
        }

    version = parse_vercel_version(result.stdout, result.stderr)
    if version is None:
        return {
            "status": "failed",
            "version": None,
            "minimum_version": MIN_VERCEL_CLI_TEXT,
            "selected_path": selected_path,
            "candidates": [],
            "error": f"Could not parse Vercel CLI version; require >= {MIN_VERCEL_CLI_TEXT}; {remediation}",
            "remediation": remediation,
        }

    current = format_version(version)
    if version < MIN_VERCEL_CLI:
        candidates = _candidate_versions(
            runner,
            cwd=cwd,
            candidates=_path_candidates(path_value),
        )
        compatible = next(
            (
                row
                for row in candidates
                if row.get("compatible") and row.get("path") != selected_path
            ),
            None,
        )
        if compatible is not None:
            remediation = _shadow_remediation(selected_path, compatible)
        return {
            "status": "failed",
            "version": current,
            "minimum_version": MIN_VERCEL_CLI_TEXT,
            "selected_path": selected_path,
            "candidates": candidates,
            "error": f"Vercel CLI {current} is below required {MIN_VERCEL_CLI_TEXT}; {remediation}",
            "remediation": remediation,
        }

    return {
        "status": "ok",
        "version": current,
        "minimum_version": MIN_VERCEL_CLI_TEXT,
        "selected_path": selected_path,
        "candidates": [],
        "error": None,
        "remediation": remediation,
    }
