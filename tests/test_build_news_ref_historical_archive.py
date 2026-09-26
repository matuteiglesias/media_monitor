import hashlib
import json
import subprocess
import sys
from pathlib import Path


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _state(rows):
    h = hashlib.sha256()
    for key, value in sorted(rows.items()):
        h.update(key.encode()); h.update(b"\0"); h.update(value.encode()); h.update(b"\n")
    return h.hexdigest()


def test_build_and_verify_lossless_restartable_archive(tmp_path: Path):
    bus = tmp_path / "bus"; bus.mkdir()
    payloads = [
        [b'{"index_id":"a","value":1}\n', b'{"index_id":"b","value":2}\n'],
        [b'{"index_id":"a","value":3}\n', b'not-json\n'],
    ]
    snapshots = []
    for ordinal, rows in enumerate(payloads):
        name = f"news_ref_20260101T00000{ordinal}Z.jsonl"; raw = b"".join(rows); path = bus / name; path.write_bytes(raw)
        state = {}
        for line_no, row in enumerate(rows, 1):
            try:
                parsed = json.loads(row)
                value = json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode()
                state[parsed["index_id"]] = _sha(value)
            except json.JSONDecodeError:
                state[f"__malformed__:{name}:{line_no}"] = _sha(row.rstrip())
        snapshots.append({"filename": name, "source_bytes": len(raw), "source_file_sha256": _sha(raw), "semantic_sha256": _state(state)})
    (bus / "news_ref_current.jsonl").write_bytes(b'{"index_id":"current"}\n')
    audit = {"schema_name":"news_ref_historical_audit.v1", "input":{"snapshot_count":2,"source_bytes":sum(x["source_bytes"] for x in snapshots),"rows":4}, "snapshots":snapshots, "integrity":{"malformed_row_count":1}}
    audit_path = tmp_path / "audit.json"; audit_path.write_text(json.dumps(audit))
    root = tmp_path / "archive"; script = Path(__file__).parents[1] / "scripts/build_news_ref_historical_archive.py"
    build = [sys.executable, str(script), "build", "--bus-dir", str(bus), "--archive-root", str(root), "--audit", str(audit_path), "--checkpoint-every", "1"]
    subprocess.run(build, check=True)
    subprocess.run(build, check=True)  # completed roots restart without rewriting input
    consumer = tmp_path / "consumer.json"; consumer.write_text(json.dumps({"passed": True, "findings": []}))
    subprocess.run([sys.executable, str(script), "verify", "--bus-dir", str(bus), "--archive-root", str(root), "--consumer-audit", str(consumer)], check=True)
    report = json.loads((root / "verification.json").read_text())
    assert report["passed"]
    assert report["replay"]["all_snapshot_states_checked"] == 2
