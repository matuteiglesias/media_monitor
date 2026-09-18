"""Southland editorial reasoning DAG on Microsoft Agent Framework."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Never, Sequence

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


class AnalyzedStory(BaseModel):
    packet: EvidencePacket
    analysis: EvidenceAnalysis


class DecidedStory(BaseModel):
    packet: EvidencePacket
    analysis: EvidenceAnalysis
    decision: SouthlandDecision


class DraftedStory(BaseModel):
    packet: EvidencePacket
    analysis: EvidenceAnalysis
    decision: SouthlandDecision
    draft: SouthlandDraft
    revisions_used: int = 0


class ReviewedStory(BaseModel):
    packet: EvidencePacket
    analysis: EvidenceAnalysis
    decision: SouthlandDecision
    draft: SouthlandDraft
    review: SouthlandReview
    revisions_used: int = 0


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
    """Build a fresh MAF graph for one evidence packet.

    Topology:
      analyze -> decide
                 | reject -> terminal
                 | accept -> write -> review
                                      | approve/reject -> terminal
                                      | revise -> revise -> final_review -> terminal
    """

    def __init__(
        self,
        ai_node: StructuredAINode,
        *,
        max_revisions: int = 1,
    ) -> None:
        if max_revisions not in {0, 1}:
            raise ValueError("Southland v1 supports max_revisions of 0 or 1")
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

    def _build_graph(self, ai_results: list[AIWorkResult]):
        from agent_framework import WorkflowBuilder, WorkflowContext, executor

        @executor(id="southland_analyze")
        async def analyze(
            packet: EvidencePacket,
            ctx: WorkflowContext[AnalyzedStory],
        ) -> None:
            analysis = await self._call(
                packet=packet,
                stage="southland_analyze",
                instructions=ANALYST_INSTRUCTIONS,
                prompt="Analyze this source article.\n\n" + _packet_json(packet),
                response_model=EvidenceAnalysis,
                ai_results=ai_results,
            )
            await ctx.send_message(
                AnalyzedStory(packet=packet, analysis=analysis)
            )

        @executor(id="southland_decide")
        async def decide(
            state: AnalyzedStory,
            ctx: WorkflowContext[DecidedStory],
        ) -> None:
            decision = await self._call(
                packet=state.packet,
                stage="southland_decide",
                instructions=EDITOR_INSTRUCTIONS,
                prompt=(
                    "Decide whether this article should be Southlandized.\n\n"
                    + json.dumps(
                        {
                            "source": state.packet.model_dump(
                                mode="json", exclude={"text"}
                            ),
                            "analysis": state.analysis.model_dump(mode="json"),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                ),
                response_model=SouthlandDecision,
                ai_results=ai_results,
            )
            await ctx.send_message(
                DecidedStory(
                    packet=state.packet,
                    analysis=state.analysis,
                    decision=decision,
                )
            )

        @executor(id="southland_reject_terminal")
        async def reject_terminal(
            state: DecidedStory,
            ctx: WorkflowContext[Never, dict[str, Any]],
        ) -> None:
            result = SouthlandWorkflowResult(
                status="rejected",
                index_id=state.packet.index_id,
                workflow_id=WORKFLOW_ID,
                analysis=state.analysis,
                decision=state.decision,
                stage_work_ids=[row.work_id for row in ai_results],
            )
            await ctx.yield_output(result.model_dump(mode="json"))

        @executor(id="southland_write")
        async def write(
            state: DecidedStory,
            ctx: WorkflowContext[DraftedStory],
        ) -> None:
            draft = await self._call(
                packet=state.packet,
                stage="southland_write",
                instructions=WRITER_INSTRUCTIONS,
                prompt=json.dumps(
                    {
                        "source": state.packet.model_dump(mode="json"),
                        "analysis": state.analysis.model_dump(mode="json"),
                        "decision": state.decision.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                response_model=SouthlandDraft,
                ai_results=ai_results,
            )
            await ctx.send_message(
                DraftedStory(
                    packet=state.packet,
                    analysis=state.analysis,
                    decision=state.decision,
                    draft=draft,
                    revisions_used=0,
                )
            )

        async def run_review(
            state: DraftedStory,
            *,
            stage: str,
        ) -> ReviewedStory:
            review = await self._call(
                packet=state.packet,
                stage=stage,
                revision=state.revisions_used,
                instructions=REVIEWER_INSTRUCTIONS,
                prompt=json.dumps(
                    {
                        "analysis": state.analysis.model_dump(mode="json"),
                        "decision": state.decision.model_dump(mode="json"),
                        "draft": state.draft.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                response_model=SouthlandReview,
                ai_results=ai_results,
            )
            return ReviewedStory(
                packet=state.packet,
                analysis=state.analysis,
                decision=state.decision,
                draft=state.draft,
                review=review,
                revisions_used=state.revisions_used,
            )

        @executor(id="southland_review")
        async def review(
            state: DraftedStory,
            ctx: WorkflowContext[ReviewedStory],
        ) -> None:
            await ctx.send_message(
                await run_review(state, stage="southland_review")
            )

        @executor(id="southland_revise")
        async def revise(
            state: ReviewedStory,
            ctx: WorkflowContext[DraftedStory],
        ) -> None:
            draft = await self._call(
                packet=state.packet,
                stage="southland_revise",
                revision=1,
                instructions=REVISER_INSTRUCTIONS,
                prompt=json.dumps(
                    {
                        "analysis": state.analysis.model_dump(mode="json"),
                        "decision": state.decision.model_dump(mode="json"),
                        "draft": state.draft.model_dump(mode="json"),
                        "review": state.review.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                response_model=SouthlandDraft,
                ai_results=ai_results,
            )
            await ctx.send_message(
                DraftedStory(
                    packet=state.packet,
                    analysis=state.analysis,
                    decision=state.decision,
                    draft=draft,
                    revisions_used=1,
                )
            )

        @executor(id="southland_review_final")
        async def final_review(
            state: DraftedStory,
            ctx: WorkflowContext[ReviewedStory],
        ) -> None:
            await ctx.send_message(
                await run_review(state, stage="southland_review_final")
            )

        @executor(id="southland_review_terminal")
        async def review_terminal(
            state: ReviewedStory,
            ctx: WorkflowContext[Never, dict[str, Any]],
        ) -> None:
            checks_pass = (
                state.review.decision == "approve"
                and state.review.topology_preserved
                and state.review.fiction_separated
                and state.review.attribution_preserved
                and state.review.alias_consistent
            )
            result = SouthlandWorkflowResult(
                status="accepted" if checks_pass else "rejected",
                index_id=state.packet.index_id,
                workflow_id=WORKFLOW_ID,
                analysis=state.analysis,
                decision=state.decision,
                draft=state.draft,
                review=state.review,
                revisions_used=state.revisions_used,
                stage_work_ids=[row.work_id for row in ai_results],
                error="" if checks_pass else "final editorial review did not approve",
            )
            await ctx.yield_output(result.model_dump(mode="json"))

        builder = WorkflowBuilder(
            start_executor=analyze,
            output_from=[reject_terminal, review_terminal],
        )
        builder.add_edge(analyze, decide)
        builder.add_edge(
            decide,
            reject_terminal,
            condition=lambda state: state.decision.decision == "reject",
        )
        builder.add_edge(
            decide,
            write,
            condition=lambda state: state.decision.decision == "accept",
        )
        builder.add_edge(write, review)
        builder.add_edge(
            review,
            revise,
            condition=lambda state: (
                state.review.decision == "revise" and self.max_revisions == 1
            ),
        )
        builder.add_edge(
            review,
            review_terminal,
            condition=lambda state: (
                state.review.decision != "revise" or self.max_revisions == 0
            ),
        )
        builder.add_edge(revise, final_review)
        builder.add_edge(final_review, review_terminal)
        return builder.build()

    async def run(self, packet: EvidencePacket) -> SouthlandRunEvidence:
        ai_results: list[AIWorkResult] = []
        workflow = self._build_graph(ai_results)
        try:
            run_result = await workflow.run(packet)
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
    """Outer pipeline AI node: batch stories while isolating each MAF DAG."""

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
