from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_live_publication_golden_path_is_explicit_and_preserves_gate():
    docs = (ROOT / "LIVE_PUBLICATION.md").read_text(encoding="utf-8")
    assert "bin/media-refresh --target preview" in docs
    assert "bin/media-refresh --target production" in docs
    assert "human publication gate" in docs
    assert "git branch --set-upstream-to=origin/main main" in docs
