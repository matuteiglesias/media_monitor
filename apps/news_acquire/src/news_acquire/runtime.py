"""Explicit runtime controls shared by the local sensing stages."""

from __future__ import annotations

import os
from dataclasses import dataclass


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError(f"{name} must be a boolean (0/1, false/true, no/yes, off/on)")


@dataclass(frozen=True)
class SensingControls:
    acquire_network: bool
    write_artifacts: bool
    enqueue_scrape: bool
    db_run_bookkeeping: bool

    @classmethod
    def from_env(cls) -> "SensingControls":
        """Resolve independent controls while retaining the legacy DRY_RUN shortcut.

        Explicit controls always win.  DRY_RUN remains a compatibility alias for
        disabling acquisition and enqueue.  DB bookkeeping is opt-in because the
        local sensing golden path has historically tolerated absent Postgres.
        """
        dry_run = env_bool("DRY_RUN", False)
        return cls(
            acquire_network=env_bool("ACQUIRE_NETWORK", not dry_run),
            write_artifacts=env_bool("WRITE_ARTIFACTS", True),
            enqueue_scrape=env_bool("ENQUEUE_SCRAPE", not dry_run),
            db_run_bookkeeping=env_bool("DB_RUN_BOOKKEEPING", False),
        )
