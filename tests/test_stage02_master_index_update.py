from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pandas as pd


def test_load_master_ref_csv_tolerates_empty_file(tmp_path: Path, monkeypatch):
    # stage02 transitively imports db.py which imports psycopg; stub it for unit test isolation.
    monkeypatch.setitem(sys.modules, "psycopg", types.SimpleNamespace())

    stage02 = importlib.import_module("apps.news_acquire.src.news_acquire.stage02_master_index_update")

    empty_master = tmp_path / "master_ref.csv"
    empty_master.write_text("", encoding="utf-8")

    monkeypatch.setattr(stage02, "MASTER_REF_CSV", empty_master)
    df = stage02.load_master_ref_csv()

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["index_id", "source", "link", "first_seen", "last_seen", "topics", "meta"]
    assert df.empty
