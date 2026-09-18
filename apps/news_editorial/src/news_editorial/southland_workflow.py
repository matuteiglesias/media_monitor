"""Southland editorial reasoning workflow on Microsoft Agent Framework."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .ai_runtime import AIWorkItem, AIWorkResult, StructuredAINode
from .southland_models import (
    EvidenceAnalysis,
    SouthlandDecision,
    SouthlandDraft,
    SouthlandReview,
    SouthlandWorkflowResult,
)


WORKFLOW_ID = "southland-editorial-v1"


class EvidencePacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index_id: str = Field(min_length=1)
    digest_at: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    fetched_at: str = Field(min_length=1)
    text_hash: str = Field(min_length=1)
    text: str = Field(min_length=1)


@dataclass(frozen=True)
class SouthlandRunEvidence:
    result: SouthlandWorkflowResult
    ai_results: list[AIWorkResult]


class SouthlandStageError(RuntimeError):
    pass


def _work_id(packet: EvidencePacket, stage: str, revision: int = 0) -> str:
    raw = f"{WORKFLOW_ID}|{packet.index_id}|{packet.text_hash}|{stage}|{revision}"
    return "ai_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _packet_json(packet: EvidencePacket) -> str:
    return json.dumps(
        {
            "index_id": packet.index_id,
            "title": packet.title,
            "source": packet.source,
            "topic": packet.topic,
            "source_url": packet.source_url,
            "text": packet.text,
        },
        ensure_ascii=False,
        indent=2,
    )


ANALYST_INSTRUCTIONS = """You are the evidence analyst inside a satirical-news editorial system.
Work only from the supplied source article. Separate documented facts/actions from attributed claims,
publisher interpretation, and uncertainty. Do not infer private motives. Do not invent quotations,
events, crimes, relationships, or factual details. Humor is not your task. Return concise structured
analysis suitable for a later editor."""

EDITOR_INSTRUCTIONS = """You are the Southland editorial gate. Southland is a clearly fictional,
deadpan satirical mirror of Argentine public news. Decide whether the supplied evidence has a strong,
story-specific comic mechanism. Preserve the real event topology while allowing metaphors,
euphemisms, prestige games, incentives, and institutional absurdities to become literal in fiction.
Reject weak stories rather than forcing a joke. Do not advocate for or against political actors,
parties, policies, votes, or electoral choices. Never invent direct quotations, criminal conduct,
private facts, or unsupported factual allegations. Clearly list transformations that a writer must
not blur back into factual claims."""

WRITER_INSTRUCTIONS = """Write a Southland article from the approved transformation plan.
Use dry straight-news prose in an obviously fictional satirical universe. Keep the underlying event
topology recognizable, but keep fictional escalation distinct from sourced reality. Do not invent
quotes. Do not turn publisher interpretation into fact. Do not tell readers how to vote or support
or oppose political actors. Escalate modestly rather than piling on unrelated absurdity. Produce a
complete article draft, not notes."""

REVIEWER_INSTRUCTIONS = """Review a Southland draft against its source analysis and transformation
plan. Check: event topology is preserved; fiction is not presented as sourced fact; attribution is
preserved; aliases are internally consistent; no invented quotations or unsupported factual
accusations appear; no political advocacy or voting recommendation appears. Approve only when all
checks pass. If fixable, request one concrete revision. Reject if the transformation is fundamentally
unsafe or detached from the source."""

REVISER_INSTRUCTIONS = """Revise the Southland draft only as instructed by the reviewer. Preserve
the approved comic mechanism and sourced event topology. Remove or repair any factual/fictional
blurring, attribution loss, alias inconsistency, invented quotation, unsupported allegation, or
political advocacy. Return a complete replacement draft."""


class SouthlandEditorialWorkflow:
    def __init__(
        self,
        ai_node: StructuredAINode,
        *,
        max_revisions: int = 1,
    ) -> None:
        if max_revisions < 0:
            raise ValueError("max_revisions must be >= 0")
        self.ai_node = ai_node
        self.max_revisions = max_revisions

    async def _call(
        self,
        *,
        packet: EvidencePacket,
        stage: str,
        instructions: str,
        prompt: str,
        response_model: type[BaseModel],
        ai_results: list[AIWorkResult],
        revision: int = 0,
    ) -> BaseModel:
        item = AIWorkItem(
            work_id=_work_id(packet, stage, revision),
            task=stage,
            instructions=instructions,
            prompt=prompt,
            response_model=response_model,
            metadata={
                "workflow_id": WORKFLOW_ID,
                "index_id": packet.index_id,
                "text_hash": packet.text_hash,
                "revision": revision,
            },
        )
        result = await self.ai_node.run_one(item)
        ai_results.append(result)
        if not result.ok or result.output is None:
            raise SouthlandStageError(
                f"{stage} failed: {result.error_type or 'unknown'}: "
                f"{result.error_message or 'no structured output'}"
            )
        return response_model.model_validate(result.output)

    async def _execute(
        self,
        packet: EvidencePacket,
        ai_results: list[AIWorkResult],
    ) -> dict[str, Any]:
        analysis = await self._call(
            packet=packet,
            stage="southland_analyze",
            instructions=ANALYST_INSTRUCTIONS,
            prompt="Analyze this source article.\n\n" + _packet_json(packet),
            response_model=EvidenceAnalysis,
            ai_results=ai_results,
        )
        assert isinstance(analysis, EvidenceAnalysis)

        decision = await self._call(
            packet=packet,
            stage="southland_decide",
            instructions=EDITOR_INSTRUCTIONS,
            prompt=(
                "Decide whether this article should be Southlandized.\n\n"
                + json.dumps(
                    {
                        "source": packet.model_dump(mode="json", exclude={"text"}),
                        "analysis": analysis.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            ),
            response_model=SouthlandDecision,
            ai_results=ai_results,
        )
        assert isinstance(decision, SouthlandDecision)

        if decision.decision == "reject":
            return SouthlandWorkflowResult(
                status="rejected",
                index_id=packet.index_id,
                workflow_id=WORKFLOW_ID,
                analysis=analysis,
                decision=decision,
                stage_work_ids=[row.work_id for row in ai_results],
            ).model_dump(mode="json")

        draft = await self._call(
            packet=packet,
            stage="southland_write",
            instructions=WRITER_INSTRUCTIONS,
            prompt=json.dumps(
                {
                    "source": packet.model_dump(mode="json"),
                    "analysis": analysis.model_dump(mode="json"),
                    "decision": decision.model_dump(mode="json"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            response_model=SouthlandDraft,
            ai_results=ai_results,
        )
        assert isinstance(draft, SouthlandDraft)

        review = await self._call(
            packet=packet,
            stage="southland_review",
            instructions=REVIEWER_INSTRUCTIONS,
            prompt=json.dumps(
                {
                    "analysis": analysis.model_dump(mode="json"),
                    "decision": decision.model_dump(mode="json"),
                    "draft": draft.model_dump(mode="json"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            response_model=SouthlandReview,
            ai_results=ai_results,
        )
        assert isinstance(review, SouthlandReview)

        revisions_used = 0
        while review.decision == "revise" and revisions_used < self.max_revisions:
            revisions_used += 1
            draft = await self._call(
                packet=packet,
                stage="southland_revise",
                revision=revisions_used,
                instructions=REVISER_INSTRUCTIONS,
                prompt=json.dumps(
                    {
                        "analysis": analysis.model_dump(mode="json"),
                        "decision": decision.model_dump(mode="json"),
                        "draft": draft.model_dump(mode="json"),
                        "review": review.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                response_model=SouthlandDraft,
                ai_results=ai_results,
            )
            assert isinstance(draft, SouthlandDraft)
            review = await self._call(
                packet=packet,
                stage="southland_review_final",
                revision=revisions_used,
                instructions=REVIEWER_INSTRUCTIONS,
                prompt=json.dumps(
                    {
                        "analysis": analysis.model_dump(mode="json"),
                        "decision": decision.model_dump(mode="json"),
                        "draft": draft.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                response_model=SouthlandReview,
                ai_results=ai_results,
            )
            assert isinstance(review, SouthlandReview)

        checks_pass = (
            review.decision == "approve"
            and review.topology_preserved
            and review.fiction_separated
            and review.attribution_preserved
            and review.alias_consistent
        )
        status = "accepted" if checks_pass else "rejected"
        return SouthlandWorkflowResult(
            status=status,
            index_id=packet.index_id,
            workflow_id=WORKFLOW_ID,
            analysis=analysis,
            decision=decision,
            draft=draft,
            review=review,
            revisions_used=revisions_used,
            stage_work_ids=[row.work_id for row in ai_results],
            error="" if checks_pass else "final editorial review did not approve",
        ).model_dump(mode="json")

    async def run(self, packet: EvidencePacket) -> SouthlandRunEvidence:
        # Build a fresh MAF workflow for each story.  FunctionalWorkflow instances
        # are stateful and should be scoped to one logical caller/session.
        from agent_framework import workflow

        ai_results: list[AIWorkResult] = []

        @workflow
        async def editorial_flow(payload: dict[str, Any]) -> dict[str, Any]:
            parsed = EvidencePacket.model_validate(payload)
            return await self._execute(parsed, ai_results)

        built = editorial_flow.build()
        try:
            run_result = await built.run(packet.model_dump(mode="json"))
            outputs = run_result.get_outputs()
            if not outputs:
                raise SouthlandStageError("MAF workflow produced no terminal output")
            result = SouthlandWorkflowResult.model_validate(outputs[-1])
        except Exception as exc:
            result = SouthlandWorkflowResult(
                status="failed",
                index_id=packet.index_id,
                workflow_id=WORKFLOW_ID,
                stage_work_ids=[row.work_id for row in ai_results],
                error=f"{type(exc).__name__}: {exc}",
            )
        return SouthlandRunEvidence(result=result, ai_results=ai_results)


class SouthlandEditorialNode:
    """Outer pipeline AI node: batch stories while isolating each MAF workflow."""

    def __init__(
        self,
        ai_node: StructuredAINode,
        *,
        story_concurrency: int = 4,
        max_revisions: int = 1,
    ) -> None:
        if story_concurrency < 1:
            raise ValueError("story_concurrency must be positive")
        self.ai_node = ai_node
        self.story_concurrency = story_concurrency
        self.max_revisions = max_revisions

    async def run_many(
        self, packets: Sequence[EvidencePacket]
    ) -> list[SouthlandRunEvidence]:
        semaphore = asyncio.Semaphore(self.story_concurrency)

        async def run_packet(packet: EvidencePacket) -> SouthlandRunEvidence:
            async with semaphore:
                workflow_runner = SouthlandEditorialWorkflow(
                    self.ai_node,
                    max_revisions=self.max_revisions,
                )
                return await workflow_runner.run(packet)

        return list(await asyncio.gather(*(run_packet(packet) for packet in packets)))


def ai_result_record(result: AIWorkResult) -> dict[str, Any]:
    return asdict(result)
