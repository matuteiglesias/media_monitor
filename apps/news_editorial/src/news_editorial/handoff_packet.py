from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_index(index_path: Path) -> dict[str, Any]:
    if not index_path.exists():
        return {}
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _collect_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    handoff = payload.get("human_handoff")
    if not isinstance(handoff, dict):
        return []
    action_candidates = handoff.get("action_candidates")
    if not isinstance(action_candidates, list):
        return []
    return [c for c in action_candidates if isinstance(c, dict)]


def _readme_content(index_path: Path, packet_dir: Path, payload: dict[str, Any], candidate_count: int) -> str:
    digest_at = payload.get("digest_at")
    status = payload.get("status")
    built_at = payload.get("built_at")
    return f"""# Editorial Handoff Packet

This packet is a human-readable handoff surface materialized from the Level 2 editorial index.

- **Input index:** `{index_path}`
- **Packet directory:** `{packet_dir}`
- **Index digest:** `{digest_at or 'unknown'}`
- **Index status:** `{status or 'no-data'}`
- **Index built_at:** `{built_at or 'unknown'}`
- **Candidate count:** `{candidate_count}`

## Command

```bash
python -m apps.news_editorial.src.news_editorial.handoff_packet \
  --index storage/indexes/editorial_latest.json \
  --out artifacts/editorial_handoff/latest
```

## What this packet proves

- The handoff can be consumed without reading raw PromptFlow output or draft mirrors.
- Contract/fallback posture is explicit from the index.
- Publication candidates (if any) are listed for editorial triage.

## Human next step

1. Review `publication_candidates.md`.
2. Review `fallback_status.md` for degradation/fallback context.
3. Review `source_pointers.json` for artifact trace links.
4. Publish or request revisions based on ready state and target format.
"""


def _publication_candidates_content(candidates: list[dict[str, Any]]) -> str:
    lines = ["# Publication Candidates", ""]
    if not candidates:
        lines.append("No candidates available in the current editorial index.")
        return "\n".join(lines)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in candidates:
        grouped[str(c.get("target_format") or "unknown")].append(c)

    for target_format in sorted(grouped.keys()):
        lines.extend([
            f"## Format: `{target_format}`",
            "",
            "| title | topic | ready state | source | brief id | draft path | candidate id |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ])

        for i, c in enumerate(grouped[target_format], start=1):
            title = str(c.get("title") or "")
            topic = str(c.get("topic") or "")
            ready_state = str(c.get("ready_state") or "")
            source = str(c.get("source") or "")
            brief_id = str(c.get("brief_id") or "")
            draft_path = str(c.get("path") or c.get("draft_path") or "")
            candidate_id = str(c.get("candidate_id") or c.get("id") or f"{target_format}_{i}")
            lines.append(f"| {title} | {topic} | {ready_state} | {source} | {brief_id} | {draft_path} | {candidate_id} |")

        lines.append("")

    return "\n".join(lines).rstrip()


def _fallback_status_content(payload: dict[str, Any]) -> str:
    contract_inputs = payload.get("contract_inputs") if isinstance(payload.get("contract_inputs"), dict) else {}
    fallback_inputs = payload.get("fallback_inputs") if isinstance(payload.get("fallback_inputs"), dict) else {}
    status = str(payload.get("status") or "no-data")

    bus_first = bool(any(bool(v) for v in contract_inputs.values()))
    pf_needed = bool(fallback_inputs.get("pf_out"))
    drafts_needed = bool(fallback_inputs.get("data_drafts"))

    lines = [
        "# Fallback Status",
        "",
        f"- index status: `{status}`",
        f"- bus-first handoff: `{'yes' if bus_first else 'no'}`",
        f"- used PF output fallback: `{'yes' if pf_needed else 'no'}`",
        f"- used legacy drafts fallback: `{'yes' if drafts_needed else 'no'}`",
        "",
        "## contract_inputs",
        "```json",
        json.dumps(contract_inputs, ensure_ascii=False, indent=2),
        "```",
        "",
        "## fallback_inputs",
        "```json",
        json.dumps(fallback_inputs, ensure_ascii=False, indent=2),
        "```",
    ]
    if status in {"degraded", "no-data"}:
        lines.extend([
            "",
            "## notes",
            "- Handoff is degraded or empty; verify upstream editorial run health before publication decisions.",
        ])

    return "\n".join(lines)


def _source_pointers_payload(payload: dict[str, Any], index_path: Path, out_dir: Path) -> dict[str, Any]:
    pointers = payload.get("pointers") if isinstance(payload.get("pointers"), dict) else {}
    return {
        "source_index": str(index_path),
        "packet_dir": str(out_dir),
        "pointers": pointers,
    }


def materialize_handoff_packet(index_path: Path, out_dir: Path) -> Path:
    payload = _read_index(index_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    candidates = _collect_candidates(payload)
    contract_inputs = payload.get("contract_inputs") if isinstance(payload.get("contract_inputs"), dict) else {}
    fallback_inputs = payload.get("fallback_inputs") if isinstance(payload.get("fallback_inputs"), dict) else {}

    _write_text(out_dir / "README.md", _readme_content(index_path, out_dir, payload, len(candidates)))
    _write_text(out_dir / "publication_candidates.md", _publication_candidates_content(candidates))
    _write_text(out_dir / "fallback_status.md", _fallback_status_content(payload))
    _write_json(out_dir / "editorial_latest.copy.json", payload)
    _write_json(out_dir / "source_pointers.json", _source_pointers_payload(payload, index_path, out_dir))

    provenance = {
        "built_at": _utc_now_iso(),
        "source_index": str(index_path),
        "packet_dir": str(out_dir),
        "contract_inputs": contract_inputs,
        "fallback_inputs": fallback_inputs,
        "candidate_count": len(candidates),
    }
    _write_json(out_dir / "provenance.json", provenance)
    return out_dir


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Materialize editorial handoff packet from editorial_latest index")
    p.add_argument("--index", default="storage/indexes/editorial_latest.json")
    p.add_argument("--out", default="artifacts/editorial_handoff/latest")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = materialize_handoff_packet(Path(args.index), Path(args.out))
    print(f"[handoff-packet] out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
