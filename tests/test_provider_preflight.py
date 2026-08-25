from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from provider_preflight import vercel_cli_preflight
from roll_site import Result


def _exe(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


class VersionRunner:
    def __init__(self, selected_version: str, versions: dict[str, str] | None = None):
        self.selected_version = selected_version
        self.versions = versions or {}
        self.calls: list[list[str]] = []

    def __call__(self, command, *, cwd, env=None):
        self.calls.append(command)
        if command == ["vercel", "--version"]:
            return Result(command, 0, f"Vercel CLI {self.selected_version}\n", "")
        version = self.versions.get(command[0])
        if version is not None:
            return Result(command, 0, f"Vercel CLI {version}\n", "")
        return Result(command, 1, "", "unknown candidate")


def test_preflight_reports_compatible_pnpm_binary_shadowed_by_old_vercel(tmp_path):
    old = tmp_path / ".local" / "bin" / "vercel"
    new = tmp_path / ".local" / "share" / "pnpm" / "bin" / "vercel"
    _exe(old)
    _exe(new)
    path_value = os.pathsep.join([str(old.parent), str(new.parent)])
    runner = VersionRunner("46.0.5", {str(old): "46.0.5", str(new): "59.5.0"})

    report = vercel_cli_preflight(runner, cwd=tmp_path, path_value=path_value)

    assert report["status"] == "failed"
    assert report["selected_path"] == str(old)
    assert report["version"] == "46.0.5"
    assert any(row["path"] == str(new) and row["compatible"] for row in report["candidates"])
    assert "PATH shadowing" in report["error"]
    assert str(new) in report["error"]
    assert 'export PNPM_HOME=' in report["error"]
    assert 'hash -r' in report["error"]
    assert "pnpm add -g" not in report["error"]


def test_preflight_does_not_scan_alternates_when_selected_vercel_is_compatible(tmp_path):
    current = tmp_path / "bin" / "vercel"
    _exe(current)
    runner = VersionRunner("59.5.0", {str(current): "59.5.0"})

    report = vercel_cli_preflight(runner, cwd=tmp_path, path_value=str(current.parent))

    assert report["status"] == "ok"
    assert report["selected_path"] == str(current)
    assert report["version"] == "59.5.0"
    assert report["candidates"] == []
    assert runner.calls == [["vercel", "--version"]]
