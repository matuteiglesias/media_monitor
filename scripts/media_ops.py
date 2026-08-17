#!/usr/bin/env python3
"""Read-only media ops plus a narrow, verified source-site publish command."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from roll_site import Result, roll

DIGEST_RE = re.compile(r"^\d{8}T\d{2}$")
TARGETS = ("preview", "production")
DEFAULT_SITE_ID = "argentina-general"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def command_runner(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> Result:
    done = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    return Result(command, done.returncode, done.stdout, done.stderr)


def _time(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _digest(value: str) -> str:
    value = value.strip()
    if not DIGEST_RE.fullmatch(value):
        raise ValueError(f"invalid digest_at {value!r}; expected YYYYMMDDTHH")
    return value


def resolve_digest(root: Path, explicit: str | None = None) -> str:
    if explicit:
        return _digest(explicit)
    path = root / "storage/indexes/pr3a_exports_latest.json"
    if not path.exists():
        raise ValueError("no digest specified and storage/indexes/pr3a_exports_latest.json is missing")
    value = str(_json(path).get("digest_at") or "")
    if not value:
        raise ValueError(f"{path}: missing digest_at")
    return _digest(value)


def load_site_config(root: Path, site_id: str) -> dict[str, Any]:
    path = root / "sites" / f"{site_id}.json"
    if not path.exists():
        raise ValueError(f"missing site config: {path}")
    cfg = _json(path)
    if cfg.get("site_id") != site_id:
        raise ValueError(f"{path}: site_id does not match {site_id}")
    for key in ("name", "tagline", "locale", "selection", "presentation"):
        if key not in cfg:
            raise ValueError(f"{path}: missing {key}")
    selection, presentation = cfg["selection"], cfg["presentation"]
    if not isinstance(selection.get("topics"), list) or not selection["topics"]:
        raise ValueError(f"{path}: selection.topics must be non-empty")
    for key in ("max_age_hours", "minimum_items", "max_items"):
        if not isinstance(selection.get(key), int) or selection[key] < 0:
            raise ValueError(f"{path}: selection.{key} must be a non-negative int")
    if not 0 < selection["minimum_items"] <= selection["max_items"]:
        raise ValueError(f"{path}: minimum_items must be positive and <= max_items")
    if not isinstance(presentation.get("latest_count"), int) or presentation["latest_count"] < 1:
        raise ValueError(f"{path}: presentation.latest_count must be positive")
    return cfg


def _latest_roll(root: Path, site_id: str, target: str) -> dict[str, Any] | None:
    paths = list((root / "storage/runs").glob(f"site_roll_{site_id}_*.json"))
    latest = root / "storage/observability" / f"site_roll_latest_{site_id}.json"
    if latest.exists():
        paths.append(latest)
    rows = []
    for path in paths:
        try:
            row = _json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if row.get("site_id") == site_id and row.get("target") == target:
            row = dict(row, _record_path=str(path.relative_to(root)))
            rows.append(row)
    if not rows:
        return None
    floor = datetime.min.replace(tzinfo=timezone.utc)
    return max(rows, key=lambda r: (_time(r.get("completed_at")) or _time(r.get("started_at")) or floor, r["_record_path"]))


def _heartbeat(root: Path) -> dict[str, Any]:
    path = root / "storage/observability/heartbeat.pid"
    try:
        pid = int(path.read_text().strip())
        os.kill(pid, 0)
        return {"state": "running", "pid": pid}
    except (OSError, ValueError):
        return {"state": "not_running", "pid": None}


def _identity(source: dict[str, Any], *, snapshot: bool) -> dict[str, Any]:
    if snapshot:
        return {
            "site_id": (source.get("site") or {}).get("site_id"),
            "snapshot_id": source.get("snapshot_id"),
            "digest_at": source.get("digest_at"),
            "item_count": (source.get("metrics") or {}).get("item_count"),
            "section_count": (source.get("metrics") or {}).get("section_count"),
        }
    return {
        "site_id": source.get("site_id"),
        "snapshot_id": source.get("snapshot_id"),
        "digest_at": source.get("digest_at"),
        "item_count": (source.get("expected") or {}).get("item_count"),
        "section_count": (source.get("expected") or {}).get("section_count"),
    }


def _health_matches(source: dict[str, Any], observed: dict[str, Any], *, snapshot: bool) -> bool:
    expected = _identity(source, snapshot=snapshot)
    return observed.get("status") == "ok" and all(observed.get(k) == v for k, v in expected.items())


def status(
    site_id: str,
    target: str,
    repo_root: Path,
    *,
    runner: Callable[..., Result] = command_runner,
    which: Callable[[str], str | None] = shutil.which,
    local_only: bool = False,
    now: datetime | None = None,
) -> tuple[dict[str, Any], int]:
    if target not in TARGETS:
        raise ValueError(f"target must be one of {TARGETS}")
    root = repo_root.resolve()
    warnings: list[str] = []
    failures: list[str] = []
    report: dict[str, Any] = {
        "schema_name": "media_status.v1", "status": "warn", "site_id": site_id, "target": target,
        "local": None, "roll": None, "remote": None, "heartbeat": _heartbeat(root),
        "warnings": warnings, "failures": failures,
    }

    try:
        cfg = load_site_config(root, site_id)
    except Exception as exc:
        cfg = None
        failures.append(str(exc))

    snapshot_path = root / "apps/news_site/public/data/site_snapshot.json"
    if snapshot_path.exists():
        try:
            snap = _json(snapshot_path)
            generated = _time(snap.get("generated_at"))
            age = ((now or datetime.now(timezone.utc)) - generated).total_seconds() / 3600 if generated else None
            report["local"] = dict(_identity(snap, snapshot=True), generated_at=snap.get("generated_at"), age_hours=round(age, 2) if age is not None else None)
            if report["local"]["site_id"] != site_id:
                failures.append("local snapshot site_id does not match requested site")
            max_age = ((cfg or {}).get("selection") or {}).get("max_age_hours")
            if age is not None and isinstance(max_age, (int, float)) and age > max_age:
                warnings.append(f"local snapshot is stale: age={age:.1f}h threshold={max_age}h")
        except Exception as exc:
            snap = None
            failures.append(f"local snapshot unreadable: {exc}")
    else:
        snap = None
        warnings.append("local site snapshot is missing")

    record = _latest_roll(root, site_id, target)
    if record:
        report["roll"] = {k: v for k, v in record.items() if not k.startswith("_")} | {"record_path": record["_record_path"]}
        if record.get("status") != "ok":
            failures.append(f"latest {target} roll failed at {record.get('failed_stage') or 'unknown'}: {record.get('error') or 'unknown error'}")
    else:
        warnings.append(f"no {target} site roll record found")

    if not local_only and record and record.get("deployment_host"):
        host = str(record["deployment_host"])
        if not which("vercel"):
            warnings.append("vercel CLI unavailable; remote health not checked")
        else:
            result = runner(["vercel", "curl", "/api/health", "--deployment", host], cwd=root, env=None)
            if result.exit_code:
                warnings.append(f"remote health check failed for {host}")
            else:
                try:
                    observed = json.loads(result.stdout)
                    if not isinstance(observed, dict):
                        raise ValueError("health payload is not an object")
                except (json.JSONDecodeError, ValueError) as exc:
                    failures.append(f"remote health returned invalid JSON: {exc}")
                else:
                    match_roll = _health_matches(record, observed, snapshot=False)
                    match_local = _health_matches(snap, observed, snapshot=True) if snap else None
                    report["remote"] = {"deployment_host": host, "health": observed, "matches_roll_record": match_roll, "matches_local_snapshot": match_local}
                    if not match_roll:
                        failures.append("deployed health identity does not match the latest roll record")
                    if match_local is False:
                        warnings.append("local snapshot differs from deployed health identity")
    elif not local_only and record and record.get("status") == "ok":
        failures.append("successful roll record is missing deployment_host")

    report["status"] = "fail" if failures else "warn" if warnings else "ok"
    return report, 1 if failures else 0


def _check(name: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "required": True, "detail": detail}


def doctor(
    site_id: str,
    target: str,
    repo_root: Path,
    *,
    digest_at: str | None = None,
    runner: Callable[..., Result] = command_runner,
    which: Callable[[str], str | None] = shutil.which,
    python_executable: str = sys.executable,
) -> tuple[dict[str, Any], int]:
    if target not in TARGETS:
        raise ValueError(f"target must be one of {TARGETS}")
    root = repo_root.resolve()
    checks: list[dict[str, Any]] = []
    try:
        digest = resolve_digest(root, digest_at)
        checks.append(_check("digest", True, f"resolved {digest}"))
    except Exception as exc:
        digest = digest_at
        checks.append(_check("digest", False, str(exc)))

    for name in ("git", "make", "node", "npm", "vercel"):
        found = which(name)
        checks.append(_check(f"tool:{name}", bool(found), found or "not found on PATH"))

    imported = runner([python_executable, "-c", "import jsonschema"], cwd=root, env=None)
    checks.append(_check("python:jsonschema", imported.exit_code == 0, "import ok" if imported.exit_code == 0 else "jsonschema import failed"))

    for rel in (
        "scripts/build_news_access_indexes.py", "scripts/build_site_snapshot.py", "scripts/validate_site_snapshot.py",
        "scripts/roll_site.py", "apps/news_site/package.json", "apps/news_site/package-lock.json",
    ):
        present = (root / rel).is_file()
        checks.append(_check(f"file:{rel}", present, "present" if present else "missing"))

    try:
        cfg = load_site_config(root, site_id)
        checks.append(_check("site-config", True, f"sites/{site_id}.json locale={cfg.get('locale')}"))
    except Exception as exc:
        checks.append(_check("site-config", False, str(exc)))

    project_path = root / ".vercel/project.json"
    try:
        project = _json(project_path)
        linked = bool(project.get("projectId") and project.get("orgId"))
        detail = f"projectId={project.get('projectId') or 'missing'} orgId={project.get('orgId') or 'missing'}"
    except Exception as exc:
        linked, detail = False, f"missing/invalid .vercel/project.json: {exc}"
    checks.append(_check("vercel-project-link", linked, detail))

    if which("vercel"):
        auth = runner(["vercel", "whoami"], cwd=root, env=None)
        detail = auth.stdout.strip().splitlines()[-1] if auth.exit_code == 0 and auth.stdout.strip() else "vercel whoami failed"
        checks.append(_check("vercel-auth", auth.exit_code == 0, detail))

    access_script = root / "scripts/build_news_access_indexes.py"
    if digest and DIGEST_RE.fullmatch(str(digest)) and access_script.exists():
        diag = runner([python_executable, str(access_script.relative_to(root)), "--storage-dir", "storage", "--digest-at", str(digest), "--diagnose"], cwd=root, env=None)
        try:
            payload = json.loads(diag.stdout) if diag.exit_code == 0 else {}
            inputs = payload.get("inputs") or []
            ready = bool(inputs) and all(row.get("exists") and int(row.get("rows") or 0) > 0 for row in inputs)
            detail = ", ".join(f"{row.get('export_name')} rows={row.get('rows', 0)} digest={row.get('digest_at')}" for row in inputs) or "no inputs reported"
        except Exception as exc:
            ready, detail = False, f"invalid diagnosis JSON: {exc}"
        checks.append(_check("publish-inputs", ready, detail))

    blocked = [row for row in checks if row["status"] == "fail"]
    report = {"schema_name": "media_doctor.v1", "status": "fail" if blocked else "ok", "ready": not blocked, "site_id": site_id, "target": target, "digest_at": digest, "checks": checks}
    return report, 1 if blocked else 0


def publish(
    site_id: str,
    target: str,
    repo_root: Path,
    *,
    digest_at: str | None = None,
    runner: Callable[..., Result] = command_runner,
    doctor_fn: Callable[..., tuple[dict[str, Any], int]] = doctor,
    roll_fn: Callable[..., tuple[dict[str, Any], int]] = roll,
) -> tuple[dict[str, Any], int]:
    if target not in TARGETS:
        raise ValueError(f"target must be one of {TARGETS}")
    root = repo_root.resolve()
    base = {"schema_name": "media_publish.v1", "site_id": site_id, "target": target}
    try:
        digest = resolve_digest(root, digest_at)
    except Exception as exc:
        return base | {"status": "failed", "digest_at": digest_at, "failed_stage": "digest", "error": str(exc)}, 1

    doctor_report, code = doctor_fn(site_id, target, root, digest_at=digest, runner=runner)
    if code or not doctor_report.get("ready"):
        return base | {"status": "failed", "digest_at": digest, "failed_stage": "doctor", "error": "publish readiness checks failed", "doctor": doctor_report}, 1

    built = runner(["make", "build-news-access-indexes", f"DIGEST_AT={digest}", f"PYTHON={sys.executable}"], cwd=root, env=None)
    if built.exit_code:
        return base | {"status": "failed", "digest_at": digest, "failed_stage": "access-indexes", "error": "build-news-access-indexes failed"}, 1

    record, code = roll_fn(site_id, digest, target, root, runner=runner)
    if code:
        return base | {"status": "failed", "digest_at": digest, "failed_stage": record.get("failed_stage") or "roll-site", "error": record.get("error") or "site roll failed", "roll": record}, 1

    return base | {
        "status": "ok", "digest_at": digest, "snapshot_id": record.get("snapshot_id"), "snapshot_sha256": record.get("snapshot_sha256"),
        "item_count": (record.get("expected") or {}).get("item_count"), "section_count": (record.get("expected") or {}).get("section_count"),
        "deployment_host": record.get("deployment_host"), "git_sha": record.get("git_sha"),
        "production_identity": "match" if target == "production" else None, "roll": record,
    }, 0


def _print_status(r: dict[str, Any]) -> None:
    print(f"MEDIA STATUS: {r['status'].upper()}\nsite={r['site_id']} target={r['target']}")
    if r.get("local"):
        x = r["local"]
        print(f"local digest={x.get('digest_at')} snapshot={x.get('snapshot_id')} items={x.get('item_count')} age_hours={x.get('age_hours')}")
    if r.get("roll"):
        x = r["roll"]
        print(f"roll status={x.get('status')} digest={x.get('digest_at')} host={x.get('deployment_host')}")
    if r.get("remote"):
        x = r["remote"]
        print(f"remote matches_roll={x.get('matches_roll_record')} matches_local={x.get('matches_local_snapshot')}")
    print(f"heartbeat={(r.get('heartbeat') or {}).get('state')}")
    for x in r.get("warnings") or []:
        print(f"WARN {x}")
    for x in r.get("failures") or []:
        print(f"FAIL {x}")


def _print_doctor(r: dict[str, Any]) -> None:
    print(f"MEDIA DOCTOR: {'READY' if r.get('ready') else 'BLOCKED'}\nsite={r['site_id']} target={r['target']} digest={r.get('digest_at')}")
    for x in r.get("checks") or []:
        print(f"[{x['status'].upper()}] {x['name']} — {x['detail']}")


def _print_publish(r: dict[str, Any]) -> None:
    print(f"MEDIA PUBLISH: {r['status'].upper()}\nsite={r['site_id']} target={r['target']} digest={r.get('digest_at')}")
    if r["status"] == "ok":
        print(f"snapshot={r.get('snapshot_id')} items={r.get('item_count')} sections={r.get('section_count')} host={r.get('deployment_host')}")
        if r.get("production_identity"):
            print("production_identity=MATCH")
    else:
        print(f"failed_stage={r.get('failed_stage')} error={r.get('error')}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Operational control surface for media_monitor source-site publication")
    p.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("status", help="Read local/deployed publication state without mutation")
    s.add_argument("--site-id", default=DEFAULT_SITE_ID)
    s.add_argument("--target", choices=TARGETS, default="production")
    s.add_argument("--local-only", action="store_true")
    s.add_argument("--json", action="store_true")
    d = sub.add_parser("doctor", help="Check publish readiness without mutation")
    d.add_argument("--site-id", default=DEFAULT_SITE_ID)
    d.add_argument("--target", choices=TARGETS, default="preview")
    d.add_argument("--digest-at")
    d.add_argument("--json", action="store_true")
    x = sub.add_parser("publish", help="Refresh source indexes and roll one verified snapshot")
    x.add_argument("--site-id", default=DEFAULT_SITE_ID)
    x.add_argument("--target", choices=TARGETS, default="preview")
    x.add_argument("--digest-at")
    x.add_argument("--json", action="store_true")
    return p


def main() -> int:
    args = build_parser().parse_args()
    root = args.repo_root
    if args.command == "status":
        report, code = status(args.site_id, args.target, root, local_only=args.local_only)
        printer = _print_status
    elif args.command == "doctor":
        report, code = doctor(args.site_id, args.target, root, digest_at=args.digest_at)
        printer = _print_doctor
    else:
        report, code = publish(args.site_id, args.target, root, digest_at=args.digest_at)
        printer = _print_publish
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        printer(report)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
