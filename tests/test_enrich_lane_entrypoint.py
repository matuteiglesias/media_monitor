from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_enrich_compatibility_entrypoint_resolves_to_owner_wrapper() -> None:
    env = {**os.environ, "MODE": "batch"}
    result = subprocess.run(
        [sys.executable, "scripts/06_scrape_enrich.py", "--dry-run"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "apps.news_enrich.src.news_enrich.scrape_enrich" in result.stdout


def test_canonical_lane_no_longer_targets_an_absent_file() -> None:
    lane_runner = (REPO_ROOT / "bin" / "run_minimal_loop_once.sh").read_text(
        encoding="utf-8"
    )

    assert "scripts/06_scrape_enrich.py" in lane_runner
    assert (REPO_ROOT / "scripts" / "06_scrape_enrich.py").is_file()
