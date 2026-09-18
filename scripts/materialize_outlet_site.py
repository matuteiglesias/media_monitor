#!/usr/bin/env python3
"""Materialize one configured outlet into the shared Next application."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
from typing import Any
from urllib.parse import urlparse

from outlet_runtime import resolve_outlet_runtime


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def repo_path(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty repository-relative path")
    candidate = (root / value).resolve()
    candidate.relative_to(root.resolve())
    if not candidate.is_file():
        raise ValueError(f"{label} does not exist: {value}")
    return candidate


def validate_https_origin(value: str, label: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/"):
        raise ValueError(f"{label} must be an HTTPS origin")
    return value.rstrip("/")


def materialize(*, repo_root: Path, site_id: str) -> dict[str, Any]:
    root = repo_root.resolve()
    runtime = resolve_outlet_runtime(root, site_id)
    site = read_json(runtime.site_config)
    build = site.get("build")
    if not isinstance(build, dict):
        raise ValueError(f"{runtime.site_config}: build must be an object")

    public_source = repo_path(root, build.get("public_identity"), "build.public_identity")
    editorial_source = repo_path(root, build.get("editorial_identity"), "build.editorial_identity")
    if not runtime.snapshot_path.is_file():
        raise ValueError(f"compiled outlet snapshot does not exist: {runtime.snapshot_path}")

    public_identity = read_json(public_source)
    editorial_identity = read_json(editorial_source)
    if public_identity.get("schema_name") != "public_identity.v1":
        raise ValueError("public identity must be public_identity.v1")
    if editorial_identity.get("schema_name") != "editorial_identity.v1":
        raise ValueError("editorial identity must be editorial_identity.v1")

    deployment = site.get("deployment") if isinstance(site.get("deployment"), dict) else {}
    public_url_env = str(deployment.get("public_url_env") or "").strip()
    if public_url_env:
        override = os.getenv(public_url_env, "").strip()
        if override:
            public_identity["public_outlet_url"] = validate_https_origin(override, public_url_env)
            if public_identity.get("owned_domain_status") == "active":
                public_identity["owned_outlet_url"] = public_identity["public_outlet_url"]

    validate_https_origin(str(public_identity.get("public_outlet_url") or ""), "public_outlet_url")

    presentation = site.get("presentation")
    if not isinstance(presentation, dict):
        raise ValueError(f"{runtime.site_config}: presentation must be an object")
    materialized_presentation = {
        "schema_name": "site_presentation.v1",
        **presentation,
    }
    mode = materialized_presentation.get("mode")
    if mode not in {"monitor", "publication"}:
        raise ValueError("presentation.mode must be monitor or publication")

    app = root / "apps" / "news_site"
    snapshot_target = app / "public" / "data" / "site_snapshot.json"
    snapshot_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(runtime.snapshot_path, snapshot_target)
    atomic_json(app / "config" / "public_identity.json", public_identity)
    atomic_json(app / "config" / "editorial_identity.json", editorial_identity)
    atomic_json(app / "config" / "site_presentation.json", materialized_presentation)

    return {
        "schema_name": "outlet_site_materialization.v1",
        "status": "ok",
        "site_id": site_id,
        "snapshot_source": str(runtime.snapshot_path),
        "snapshot_target": str(snapshot_target),
        "presentation_mode": mode,
        "public_outlet_url": public_identity["public_outlet_url"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--site-id", required=True)
    args = parser.parse_args()
    try:
        result = materialize(repo_root=args.repo_root, site_id=args.site_id)
    except Exception as exc:
        print(json.dumps({"schema_name":"outlet_site_materialization.v1","status":"failed","error":str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
