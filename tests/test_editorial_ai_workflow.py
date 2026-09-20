from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

from pydantic import BaseModel

from apps.news_editorial.src.news_editorial.ai_runtime import (
    AIWorkItem,
    BackendResponse,
    StructuredAINode,
)
from apps.news_editorial.src.news_editorial.draft_bus_writer import validate_article_draft
from apps.news_editorial.src.news_editorial.piece_brief_bus import validate_piece_brief
from apps.news_editorial.src.news_editorial.southland_models import (
    EvidenceAnalysis,
    SouthlandDecision,
    SouthlandAlias,
    SouthlandDraft,
    SouthlandReview,
)
from apps.news_editorial.src.news_editorial.southland_workflow import (
    EvidencePacket,
    SouthlandEditorialNode,
    SouthlandEditorialPolicy,
)
from scripts.run_outlet_ai import run_outlet_ai


DIGEST = "20260918T21"
CREATED_AT = "2026-09-18T21:40:00Z"

TEST_EDITORIAL_POLICY = SouthlandEditorialPolicy(
    target_min_words=8,
    target_max_words=40,
    hard_min_words=5,
    hard_max_words=80,
    max_sections=4,
    max_literalizations=2,
    max_fictional_escalations=2,
    alias_registry=(
        SouthlandAlias(real_name="Actor público", southland_name="Actor Público del Sur"),
    ),
)


class EchoModel(BaseModel):
    value: str


class FixtureBackend:
    backend_name = "fixture_backend"
    provider_name = "fixture_provider"
    model_name = "fixture_model"

    def __init__(self, *, fail_first: set[str] | None = None) -> None:
        self.fail_first = fail_first or set()
        self.attempts = defaultdict(int)
        self.active = 0
        self.max_active = 0

    async def invoke(self, item: AIWorkItem) -> BackendResponse:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.005)
            self.attempts[item.work_id] += 1
            if item.work_id in self.fail_first and self.attempts[item.work_id] == 1:
                raise RuntimeError("transient fixture error")
            return BackendResponse(value=self._value(item))
        finally:
            self.active -= 1

    def _value(self, item: AIWorkItem):
        index_id = str(item.metadata.get("index_id") or "")
        if item.task == "echo":
            return EchoModel(value=index_id)
        if item.task == "southland_analyze":
            return EvidenceAnalysis(
                factual_kernel=[f"hecho verificable {index_id}"],
                actors=["Actor público"],
                documented_actions=["acción documentada"],
                attributed_claims=["LPO atribuye una interpretación"],
                publisher_interpretations=["lectura editorial de LPO"],
                uncertainties=[],
                candidate_mechanisms=["la metáfora institucional se vuelve literal"],
                risk_flags=[],
            )
        if item.task == "southland_decide":
            if "reject" in index_id:
                return SouthlandDecision(
                    decision="reject",
                    reason="No hay mecanismo cómico suficientemente específico.",
                )
            return SouthlandDecision(
                decision="accept",
                reason="La mecánica surge directamente del evento.",
                comic_mechanism="la metáfora institucional se vuelve literal",
                preserved_event_topology="Actor A realiza acción B frente a institución C.",
                aliases=[{"real_name": "Actor público", "southland_name": "Actor Público del Sur"}],
                literalizations=["una fórmula retórica se materializa"],
                fictional_escalations=["la institución instala literalmente el mecanismo"],
                forbidden_distortions=["no inventar citas", "no cambiar quién hizo qué"],
            )
        if item.task in {"southland_write", "southland_revise"}:
            revised = item.task == "southland_revise"
            return SouthlandDraft(
                title=f"{'Versión revisada' if revised else 'Southland'} {index_id}",
                summary="Una síntesis satírica pero anclada en el evento.",
                dek="El mecanismo se vuelve literal sin cambiar la secuencia factual.",
                lede="En Southland, la metáfora apareció físicamente en la sala.",
                sections=[
                    {
                        "heading": "La escena",
                        "summary": "El evento conserva actores, acción e institución.",
                    }
                ],
                body_md=(
                    "# Southland\n\n"
                    "La fuente documenta una acción pública. En la ficción de Southland, "
                    "la metáfora asociada a esa acción adquiere forma literal."
                ),
                fact_check_flags=[],
                revision_notes=["revisión aplicada"] if revised else [],
            )
        if item.task == "southland_review":
            if "revise" in index_id:
                return SouthlandReview(
                    decision="revise",
                    notes=["Aclarar mejor la separación entre fuente y ficción."],
                    topology_preserved=True,
                    fiction_separated=False,
                    attribution_preserved=True,
                    alias_consistent=True,
                    mechanism_disciplined=True,
                    analysis_leakage_absent=True,
                    comic_payoff_present=True,
                    concise_enough=True,
                    revision_instruction="Hacer explícito que la literalización ocurre sólo en Southland.",
                )
            return SouthlandReview(
                decision="approve",
                notes=[],
                topology_preserved=True,
                fiction_separated=True,
                attribution_preserved=True,
                alias_consistent=True,
                mechanism_disciplined=True,
                analysis_leakage_absent=True,
                comic_payoff_present=True,
                concise_enough=True,
            )
        if item.task == "southland_review_final":
            return SouthlandReview(
                decision="approve",
                notes=["La revisión resolvió la separación factual."],
                topology_preserved=True,
                fiction_separated=True,
                attribution_preserved=True,
                alias_consistent=True,
                mechanism_disciplined=True,
                analysis_leakage_absent=True,
                comic_payoff_present=True,
                concise_enough=True,
            )
        raise AssertionError(f"unexpected task {item.task}")


def _assert_no_open_ended_objects(schema: dict) -> None:
    if not isinstance(schema, dict):
        return
    if schema.get("type") == "object":
        additional = schema.get("additionalProperties")
        assert not isinstance(additional, dict), schema
    for value in schema.values():
        if isinstance(value, dict):
            _assert_no_open_ended_objects(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _assert_no_open_ended_objects(item)


def test_locked_character_bible_aliases_match_runtime_registry() -> None:
    bible = yaml.safe_load((ROOT / "config/southland_characters.v1.yaml").read_text(encoding="utf-8"))
    registry = yaml.safe_load((ROOT / "config/southland_aliases.v1.yaml").read_text(encoding="utf-8"))

    assert bible["schema_version"] == "southland_characters.v1"
    assert registry["schema_version"] == "southland_aliases.v1"

    locked = {
        row["real_name"]: row["southland_name"]
        for row in bible["characters"]
        if row["alias_status"] == "locked"
    }
    runtime = {
        row["real_name"]: row["southland_name"]
        for row in registry["aliases"]
        if row["real_name"] != "Casa Rosada"
    }

    assert locked == runtime
    assert len(locked) == len(set(locked))
    assert len(locked.values()) == len(set(locked.values()))
    assert all(row.get("source_urls") is not None for row in bible["characters"])


def test_live_structured_models_do_not_expose_open_ended_object_maps() -> None:
    assert SouthlandAlias(real_name="A", southland_name="B").southland_name == "B"
    for model in (EvidenceAnalysis, SouthlandDecision, SouthlandDraft, SouthlandReview):
        _assert_no_open_ended_objects(model.model_json_schema())


def test_structured_ai_node_bounds_concurrency_and_retries_per_item() -> None:
    backend = FixtureBackend()
    items = [
        AIWorkItem(
            work_id=f"work-{idx}",
            task="echo",
            instructions="echo",
            prompt="echo",
            response_model=EchoModel,
            metadata={"index_id": f"id-{idx}"},
        )
        for idx in range(6)
    ]
    backend.fail_first.add("work-2")
    node = StructuredAINode(backend, concurrency=2, max_attempts=2)

    results = asyncio.run(node.run_many(items))

    assert [row.output["value"] for row in results if row.output] == [
        f"id-{idx}" for idx in range(6)
    ]
    assert backend.max_active <= 2
    assert results[2].attempts == 2
    assert all(row.ok for row in results)


def _packet(index_id: str) -> EvidencePacket:
    return EvidencePacket(
        index_id=index_id,
        digest_at=DIGEST,
        title=f"Fuente {index_id}",
        source="La Política Online",
        topic="Política",
        source_url=f"https://www.lapoliticaonline.com/politica/{index_id}/",
        fetched_at="2026-09-18T21:20:00Z",
        text_hash=f"hash-{index_id}",
        text=("Texto de evidencia del artículo. " * 40),
    )


def test_southland_maf_workflow_accepts_rejects_and_revises() -> None:
    # Import smoke: the workflow itself uses Microsoft Agent Framework's
    # stable graph builder even though the provider is deterministic.
    from agent_framework import WorkflowBuilder

    assert WorkflowBuilder is not None
    backend = FixtureBackend()
    ai_node = StructuredAINode(backend, concurrency=3, max_attempts=1)
    editorial = SouthlandEditorialNode(
        ai_node,
        story_concurrency=3,
        max_revisions=1,
        editorial_policy=TEST_EDITORIAL_POLICY,
    )

    first = asyncio.run(
        editorial.run_many(
            [_packet("accept-1"), _packet("reject-1"), _packet("revise-1")]
        )
    )
    second = asyncio.run(
        editorial.run_many(
            [_packet("accept-1"), _packet("reject-1"), _packet("revise-1")]
        )
    )

    assert [row.result.status for row in first] == ["accepted", "rejected", "accepted"]
    assert first[2].result.revisions_used == 1
    assert first[1].result.draft is None
    assert first[0].result.review.decision == "approve"
    assert first[2].result.review.decision == "approve"
    assert first[0].result.stage_work_ids == second[0].result.stage_work_ids


def test_editorial_v2_revises_when_deterministic_length_gate_fails() -> None:
    class LongDraftBackend(FixtureBackend):
        def _value(self, item: AIWorkItem):
            if item.task == "southland_write":
                return SouthlandDraft(
                    title="Southland largo",
                    summary="Resumen",
                    dek="Bajada",
                    lede="Lede",
                    sections=[{"heading": "La escena", "summary": "Resumen"}],
                    body_md="palabra " * 120,
                    fact_check_flags=[],
                    revision_notes=[],
                )
            if item.task == "southland_revise":
                return SouthlandDraft(
                    title="Southland breve",
                    summary="Resumen",
                    dek="Bajada",
                    lede="Lede",
                    sections=[{"heading": "La escena", "summary": "Resumen"}],
                    body_md="palabra " * 20,
                    fact_check_flags=[],
                    revision_notes=["recorte editorial"],
                )
            return super()._value(item)

    backend = LongDraftBackend()
    node = StructuredAINode(backend, concurrency=1, max_attempts=1)
    editorial = SouthlandEditorialNode(
        node,
        story_concurrency=1,
        max_revisions=1,
        editorial_policy=TEST_EDITORIAL_POLICY,
    )

    run = asyncio.run(editorial.run_many([_packet("accept-long")]))[0]

    assert run.result.status == "accepted"
    assert run.result.revisions_used == 1
    assert run.result.draft is not None
    assert len(run.result.draft.body_md.split()) == 20
    assert any(result.task == "southland_revise" for result in run.ai_results)


def test_editorial_v2_rejects_unregistered_alias_before_writing() -> None:
    class BadAliasBackend(FixtureBackend):
        def _value(self, item: AIWorkItem):
            if item.task == "southland_decide":
                return SouthlandDecision(
                    decision="accept",
                    reason="Mechanism otherwise works.",
                    comic_mechanism="un mecanismo único",
                    preserved_event_topology="A hace B.",
                    aliases=[{"real_name": "Actor público", "southland_name": "Alias improvisado"}],
                    literalizations=["literalización"],
                    fictional_escalations=[],
                    forbidden_distortions=[],
                )
            return super()._value(item)

    backend = BadAliasBackend()
    node = StructuredAINode(backend, concurrency=1, max_attempts=1)
    editorial = SouthlandEditorialNode(
        node,
        story_concurrency=1,
        max_revisions=1,
        editorial_policy=TEST_EDITORIAL_POLICY,
    )

    run = asyncio.run(editorial.run_many([_packet("accept-badalias")]))[0]

    assert run.result.status == "rejected"
    assert [result.task for result in run.ai_results] == [
        "southland_analyze",
        "southland_decide",
    ]


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def seed_outlet(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config/aliases.yaml").write_text(
        """schema_version: southland_aliases.v1
aliases:
  - real_name: Actor público
    southland_name: Actor Público del Sur
""",
        encoding="utf-8",
    )
    (tmp_path / "config/editorial_ai.southland.yaml").write_text(
        """schema_version: editorial_ai.v1
workflow_id: southland-editorial-v2
backend:
  kind: maf_openai
  model_env: MEDIA_MONITOR_AI_MODEL
  api_key_env: OPENAI_API_KEY
execution:
  provider_concurrency: 3
  story_concurrency: 3
  max_attempts: 2
  max_revisions: 1
  minimum_inputs: 5
  publish_candidate_target: 3
editorial:
  alias_registry: config/aliases.yaml
  target_min_words: 8
  target_max_words: 40
  hard_min_words: 5
  hard_max_words: 80
  max_sections: 4
  max_literalizations: 2
  max_fictional_escalations: 2
""",
        encoding="utf-8",
    )
    write_json(
        tmp_path / "config/policy.json",
        {
            "policy_id": "fixture",
            "policy_version": "1",
            "max_age_minutes": 180,
            "future_tolerance_minutes": 5,
            "minimum_items": 1,
            "max_items": 10,
            "high_priority_threshold": 0,
            "default_topic_weight": 0,
            "topic_weights": {},
            "freshness_buckets": [
                {"max_age_minutes": 180, "score": 1, "reason_code": "fresh"}
            ],
            "first_source_bonus": 0,
            "first_topic_bonus": 0,
            "repeat_source_penalty": 0,
            "repeat_topic_penalty": 0,
        },
    )
    write_json(
        tmp_path / "sites/southland.json",
        {
            "site_id": "southland",
            "name": "Southland",
            "tagline": "fixture",
            "locale": "es-AR",
            "runtime": {
                "data_dir": ".runtime/southland/data",
                "storage_dir": ".runtime/southland/storage",
                "selection_policy": "config/policy.json",
                "ai_config": "config/editorial_ai.southland.yaml",
            },
            "selection": {
                "topics": ["All Topics"],
                "max_age_hours": 3,
                "minimum_items": 1,
                "max_items": 10,
            },
            "presentation": {"latest_count": 10, "show_sources": True},
        },
    )

    storage = tmp_path / ".runtime/southland/storage"
    ids = ["accept-1", "accept-2", "revise-1", "reject-1", "reject-2"]
    write_json(
        storage / "indexes/editorial_selection_latest.json",
        {
            "schema_name": "editorial_selection.v1",
            "digest_at": DIGEST,
            "selection_id": "a" * 64,
            "selected": [
                {
                    "rank": rank,
                    "index_id": index_id,
                    "title": f"Fuente {index_id}",
                    "topic": "Política",
                    "source": "La Política Online",
                    "link": f"https://www.lapoliticaonline.com/politica/{index_id}/",
                }
                for rank, index_id in enumerate(ids, start=1)
            ],
        },
    )
    write_json(
        storage / "observability/selected_enrichment_latest.json",
        {
            "schema_name": "selected_enrichment.v1",
            "status": "ok",
            "digest_at": DIGEST,
            "results": [
                {"index_id": index_id, "quality_ok": True}
                for index_id in ids
            ],
        },
    )
    now = "2026-09-18T21:20:00Z"
    write_jsonl(
        storage / "buses/scraped_article/v1/scraped_article_2026-09-18.jsonl",
        [
            {
                "schema_name": "scraped_article.v1",
                "schema_status": "experimental",
                "index_id": index_id,
                "source_url": f"https://www.lapoliticaonline.com/politica/{index_id}/",
                "final_url": f"https://www.lapoliticaonline.com/politica/{index_id}/",
                "fetched_at": now,
                "fetch_status": "success",
                "title": f"Fuente {index_id}",
                "source": "La Política Online",
                "topic": "Política",
                "text": "Texto completo y limpio. " * 50,
                "text_hash": f"hash-{index_id}",
                "byte_size": 1000,
                "char_count": 1000,
                "language": "es",
                "error_code": "",
                "error_message": "",
                "extractor": "html_article",
                "meta": {},
            }
            for index_id in ids
        ],
    )


def test_outlet_ai_materializes_only_approved_contract_artifacts_and_replays(tmp_path: Path) -> None:
    seed_outlet(tmp_path)
    backend = FixtureBackend()

    first, code_one = asyncio.run(
        run_outlet_ai(
            repo_root=tmp_path,
            site_id="southland",
            digest_at=DIGEST,
            created_at=CREATED_AT,
            backend=backend,
        )
    )
    second, code_two = asyncio.run(
        run_outlet_ai(
            repo_root=tmp_path,
            site_id="southland",
            digest_at=DIGEST,
            created_at=CREATED_AT,
            backend=backend,
        )
    )

    storage = tmp_path / ".runtime/southland/storage"
    data = tmp_path / ".runtime/southland/data"
    brief_files = sorted((storage / "buses/news_piece_brief/v1").glob("*.jsonl"))
    draft_files = sorted((storage / "buses/news_article_draft/v1").glob("*.jsonl"))
    evidence_files = sorted((data / "ai_runs" / DIGEST).glob("*.jsonl"))

    assert code_one == code_two == 0
    assert first["accepted_count"] == second["accepted_count"] == 3
    assert first["rejected_count"] == second["rejected_count"] == 2
    assert first["failed_count"] == 0
    assert first["publish_readiness"] == "ready"
    assert len(brief_files) == 3
    assert len(draft_files) == 3
    assert len(evidence_files) == 5

    briefs = [json.loads(path.read_text(encoding="utf-8")) for path in brief_files]
    drafts = [json.loads(path.read_text(encoding="utf-8")) for path in draft_files]
    for brief in briefs:
        validate_piece_brief(brief)
        assert brief["meta"]["editorial_mode"] == "satirical_mirror"
        assert brief["meta"]["workflow_id"] == "southland-editorial-v2"
        assert brief["source_refs"][0]["source"] == "La Política Online"
    for draft in drafts:
        validate_article_draft(draft)
        assert draft["status"] == "draft"
        assert draft["created_at"] == CREATED_AT
        assert draft["source_links"][0].startswith("https://www.lapoliticaonline.com/")

    rejected_ids = {"reject-1", "reject-2"}
    assert rejected_ids.isdisjoint({draft["source_ids"][0] for draft in drafts})
    editorial_index = json.loads(
        (storage / "indexes/editorial_latest.json").read_text(encoding="utf-8")
    )
    assert editorial_index["metrics"]["briefs_emitted"] == 3
    assert editorial_index["metrics"]["drafts_emitted"] == 3


def test_maf_openai_package_is_installed_for_live_backend() -> None:
    from agent_framework.openai import OpenAIChatClient

    assert OpenAIChatClient is not None
