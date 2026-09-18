#!/usr/bin/env python3
"""Resolve configured outlet runtime paths without sharing mutable state."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OutletRuntime:
    site_id: str
    repo_root: Path
    site_config: Path
    data_dir: Path
    storage_dir: Path
    selection_policy: Path

    @property
    def indexes_dir(self) -> Path:
        return self.storage_dir / "indexes"

    @property
    def published_bus_dir(self) -> Path:
        return self.storage_dir / "buses" / "published_article" / "v1"

    @property
    def snapshot_path(self) -> Path:
        return self.storage_dir / "public" / "site_snapshot.json"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def _repo_path(root: Path, value: Any, label: str, *, must_exist: bool = False) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty repository-relative path")
    raw = Path(value)
    if raw.is_absolute():
        raise ValueError(f"{label} must be repository-relative")
    resolved_root = root.resolve()
    resolved = (resolved_root / raw).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label} escapes repository root: {value}") from exc
    if resolved == resolved_root:
        raise ValueError(f"{label} must not resolve to repository root")
    if must_exist and not resolved.is_file():
        raise ValueError(f"{label} does not exist: {value}")
    return resolved


def resolve_outlet_runtime(repo_root: Path, site_id: str) -> OutletRuntime:
    root = repo_root.resolve()
    config_path = root / "sites" / f"{site_id}.json"
    if not config_path.is_file():
        raise ValueError(f"missing site config: {config_path}")

    config = _read_json(config_path)
    if config.get("site_id") != site_id:
        raise ValueError(f"{config_path}: site_id does not match {site_id}")

    runtime = config.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError(f"{config_path}: runtime must be an object")

    required = ("data_dir", "storage_dir", "selection_policy")
    missing = [key for key in required if not runtime.get(key)]
    if missing:
        raise ValueError(f"{config_path}: runtime missing {', '.join(missing)}")

    data_dir = _repo_path(root, runtime["data_dir"], "runtime.data_dir")
    storage_dir = _repo_path(root, runtime["storage_dir"], "runtime.storage_dir")
    selection_policy = _repo_path(
        root,
        runtime["selection_policy"],
        "runtime.selection_policy",
        must_exist=True,
    )
    if data_dir == storage_dir:
        raise ValueError(f"{config_path}: runtime data_dir and storage_dir must differ")

    return OutletRuntime(
        site_id=site_id,
        repo_root=root,
        site_config=config_path,
        data_dir=data_dir,
        storage_dir=storage_dir,
        selection_policy=selection_policy,
    )
