"""Southland editorial reasoning DAG on Microsoft Agent Framework."""
import asyncio
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Never, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .ai_runtime import AIWorkItem, AIWorkResult, StructuredAINode
from .southland_models import (
    EvidenceAnalysis,
    SouthlandAlias,
    SouthlandDecision,
    SouthlandDraft,
    SouthlandReview,
    SouthlandWorkflowResult,
)


WORKFLOW_ID = "southland-editorial-v2"


@dataclass(frozen=True)
class SouthlandEditorialPolicy:
    target_min_words: int = 450
    target_max_words: int = 700
    hard_min_words: int = 300
    hard_max_words: int = 850
    max_sections: int = 4
    max_literalizations: int = 2
    max_fictional_escalations: int = 2
    alias_registry: tuple[SouthlandAlias, ...] = ()

    def __post_init__(self) -> None:
        if not (1 <= self.hard_min_words <= self.target_min_words):
            raise ValueError("hard_min_words must be positive and <= target_min_words")
        if not (self.target_min_words <= self.target_max_words <= self.hard_max_words):
            raise ValueError("target word bounds must sit inside hard word bounds")
        if self.max_sections < 1:
            raise ValueError("max_sections must be positive")
        if self.max_literalizations < 0 or self.max_fictional_escalations < 0:
            raise ValueError("fictional-device limits must be non-negative")


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


def _word_count(value: str) -> int:
    return len(re.findall(r"\b[\wÁÉÍÓÚáéíóúÑñÜü]+\b", value, flags=re.UNICODE))


def draft_metrics(draft: SouthlandDraft, policy: SouthlandEditorialPolicy) -> dict[str, Any]:
    words = _word_count(draft.body_md)
    sections = len(draft.sections)
    return {
        "word_count": words,
        "section_count": sections,
        "target_min_words": policy.target_min_words,
        "target_max_words": policy.target_max_words,
        "hard_min_words": policy.hard_min_words,
        "hard_max_words": policy.hard_max_words,
        "max_sections": policy.max_sections,
        "target_length_ok": policy.target_min_words <= words <= policy.target_max_words,
        "hard_length_ok": policy.hard_min_words <= words <= policy.hard_max_words,
        "section_count_ok": sections <= policy.max_sections,
    }


ANALYST_INSTRUCTIONS = """You are the evidence analyst inside a satirical-news editorial system.
Work only from the supplied source article. Separate documented facts/actions from attributed claims,
publisher interpretation, and uncertainty. Do not infer private motives. Do not invent quotations,
events, crimes, relationships, or factual details. Humor is not your task. Be concise: identify the
small factual kernel and the few uncertainties that materially constrain a later satire editor."""

EDITOR_INSTRUCTIONS = """You are the Southland editorial gate. Southland is a clearly fictional,
deadpan satirical mirror of Argentine public news.

Accept only when there is ONE strong, story-specific comic mechanism that can carry a compact article.
The mechanism should expose or literalize something already structurally present in the real event:
an incentive, euphemism, institutional ritual, market convention, prestige game, bureaucratic rule,
or contradiction. Reject stories whose joke would mainly be renaming people, stacking metaphors,
retelling a complicated hypothetical scenario, or explaining the source with decorative absurdity.

Preserve the real event topology. Reject rather than forcing a joke. Never advocate for or against a
political actor, party, policy, vote, or electoral choice. Never invent real quotations, criminal
conduct, private facts, or unsupported factual allegations.

Alias discipline is strict: use ONLY aliases present in the supplied canonical alias registry.
If an actor/entity has no canonical alias, keep the real public name. Do not invent a new alias.
Use no more fictional devices than the supplied editorial policy allows. The writer should be able
to express the dominant mechanism in one sentence and reuse it economically rather than introducing
a new conceit in every section."""

WRITER_INSTRUCTIONS = """Write a compact Southland article from the approved transformation plan.

Use dry straight-news prose in an obviously fictional satirical universe. ONE dominant comic
mechanism should organize the article. Do not add unrelated metaphors, departments, machines,
inspectors, counters, terminals, forms, weather systems, or other comic furniture merely to sustain
length. Stop the joke before it is exhausted.

Aim for the target word range and section count supplied in the editorial policy. Prefer 2-4 short
sections. The result should read like a newspaper story, not a research memo.

Preserve the sourced event topology. Do not invent quotes. Do not turn publisher interpretation into
fact. Attribute material claims once where needed. Do not repeatedly leak analyst language such as
"no está confirmado", "no implica", "no existe evidencia", "según el material analizado", or long
methodological caveats into the body when the same safety can be achieved by simply not asserting
the unsupported claim. The public article already has a reality/fiction disclosure and source links.

Use only the aliases explicitly approved in the transformation plan; otherwise retain real public
names. Do not tell readers how to vote or support/oppose political actors. Produce the complete
article draft, not notes."""

REVIEWER_INSTRUCTIONS = """Act as a strict Southland editor, not only a safety checker.

Check factual integrity: event topology preserved, fiction clearly separate from sourced reality,
material attribution preserved, canonical aliases followed, no invented quotation, unsupported
factual accusation, or political advocacy.

Also check editorial quality:
- ONE dominant mechanism carries the piece;
- the mechanism has an actual comic payoff rather than merely translating the source into metaphor;
- the writer does not introduce multiple competing conceits;
- source-analysis/caveat language does not leak repeatedly into the prose;
- the draft is compact and within the supplied target whenever practical;
- the joke stops before it is exhausted.

Use the deterministic draft metrics supplied with the prompt. A draft outside hard word/section
bounds cannot be approved. If the story is fundamentally weak, reject it. If it is good but bloated,
over-explained, or mechanically repetitive, request ONE concrete rewrite rather than approving it."""

REVISER_INSTRUCTIONS = """Rewrite the Southland draft decisively in response to the review.
Do not merely patch individual sentences. Preserve the approved single comic mechanism and the real
event topology, but cut aggressively. Remove repeated caveats, duplicate explanations, extra comic
devices, and unnecessary sections. Hit the target word range if possible and stay inside the hard
bounds. Use only canonical approved aliases. Return a complete replacement draft."""


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
        editorial_policy: SouthlandEditorialPolicy | None = None,
    ) -> None:
        if max_revisions not in {0, 1}:
            raise ValueError("Southland v2 supports max_revisions of 0 or 1")
        self.ai_node = ai_node
        self.max_revisions = max_revisions
        self.editorial_policy = editorial_policy or SouthlandEditorialPolicy()

    def _policy_payload(self) -> dict[str, Any]:
        policy = self.editorial_policy
        return {
            "target_min_words": policy.target_min_words,
            "target_max_words": policy.target_max_words,
            "hard_min_words": policy.hard_min_words,
            "hard_max_words": policy.hard_max_words,
            "max_sections": policy.max_sections,
            "max_literalizations": policy.max_literalizations,
            "max_fictional_escalations": policy.max_fictional_escalations,
        }

    def _alias_payload(self) -> list[dict[str, str]]:
        return [alias.model_dump(mode="json") for alias in self.editorial_policy.alias_registry]

    def _aliases_are_canonical(self, decision: SouthlandDecision) -> bool:
        allowed = {
            alias.real_name.casefold(): alias.southland_name.casefold()
            for alias in self.editorial_policy.alias_registry
        }
        seen: set[str] = set()
        for alias in decision.aliases:
            key = alias.real_name.casefold()
            if key in seen:
                return False
            seen.add(key)
            if allowed.get(key) != alias.southland_name.casefold():
                return False
        return True

    def _decision_passes_gate(self, decision: SouthlandDecision) -> bool:
        if decision.decision != "accept" or not decision.comic_mechanism.strip():
            return False
        if len(decision.literalizations) > self.editorial_policy.max_literalizations:
            return False
        if len(decision.fictional_escalations) > self.editorial_policy.max_fictional_escalations:
            return False
        return self._aliases_are_canonical(decision)

    def _review_style_checks(self, review: SouthlandReview) -> bool:
        return (
            review.mechanism_disciplined
            and review.analysis_leakage_absent
            and review.comic_payoff_present
            and review.concise_enough
        )

    def _review_safety_checks(self, review: SouthlandReview) -> bool:
        return (
            review.topology_preserved
            and review.fiction_separated
            and review.attribution_preserved
            and review.alias_consistent
        )

    def _needs_revision(self, state: ReviewedStory) -> bool:
        if state.review.decision == "reject" or self.max_revisions == 0:
            return False
        metrics = draft_metrics(state.draft, self.editorial_policy)
        return (
            state.review.decision == "revise"
            or not self._review_safety_checks(state.review)
            or not self._review_style_checks(state.review)
            or not metrics["hard_length_ok"]
            or not metrics["section_count_ok"]
        )

    def _terminal_failures(self, state: ReviewedStory) -> list[str]:
        metrics = draft_metrics(state.draft, self.editorial_policy)
        failed: list[str] = []
        if state.review.decision != "approve":
            failed.append(f"review_decision={state.review.decision}")
        for name in (
            "topology_preserved",
            "fiction_separated",
            "attribution_preserved",
            "alias_consistent",
            "mechanism_disciplined",
            "analysis_leakage_absent",
            "comic_payoff_present",
            "concise_enough",
        ):
            if not getattr(state.review, name):
                failed.append(name)
        if not metrics["hard_length_ok"]:
            failed.append("hard_length")
        if not metrics["section_count_ok"]:
            failed.append("section_count")
        return failed

    def _terminal_accepts(self, state: ReviewedStory) -> bool:
        return not self._terminal_failures(state)

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
            await ctx.send_message(AnalyzedStory(packet=packet, analysis=analysis))

        @executor(id="southland_decide")
        async def decide(
            state: AnalyzedStory,
            ctx: WorkflowContext[DecidedStory],
        ) -> None:
            decision = await self._call(
                packet=state.packet,
                stage="southland_decide",
                instructions=EDITOR_INSTRUCTIONS,
                prompt=json.dumps(
                    {
                        "instruction": "Decide whether this article should be Southlandized.",
                        "source": state.packet.model_dump(mode="json", exclude={"text"}),
                        "analysis": state.analysis.model_dump(mode="json"),
                        "editorial_policy": self._policy_payload(),
                        "canonical_alias_registry": self._alias_payload(),
                    },
                    ensure_ascii=False,
                    indent=2,
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
                error=(
                    ""
                    if state.decision.decision == "reject"
                    else "editorial decision failed deterministic mechanism/alias discipline"
                ),
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
                        "editorial_policy": self._policy_payload(),
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
            metrics = draft_metrics(state.draft, self.editorial_policy)
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
                        "draft_metrics": metrics,
                        "editorial_policy": self._policy_payload(),
                        "canonical_alias_registry": self._alias_payload(),
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
            await ctx.send_message(await run_review(state, stage="southland_review"))

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
                        "draft_metrics": draft_metrics(state.draft, self.editorial_policy),
                        "editorial_policy": self._policy_payload(),
                        "canonical_alias_registry": self._alias_payload(),
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
            failures = self._terminal_failures(state)
            checks_pass = not failures
            metrics = draft_metrics(state.draft, self.editorial_policy)
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
                error=(
                    ""
                    if checks_pass
                    else (
                        "final editorial quality gate did not approve "
                        f"(words={metrics['word_count']}, sections={metrics['section_count']}, "
                        f"failed={','.join(failures)})"
                    )
                ),
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
            condition=lambda state: not self._decision_passes_gate(state.decision),
        )
        builder.add_edge(
            decide,
            write,
            condition=lambda state: self._decision_passes_gate(state.decision),
        )
        builder.add_edge(write, review)
        builder.add_edge(
            review,
            revise,
            condition=lambda state: self._needs_revision(state),
        )
        builder.add_edge(
            review,
            review_terminal,
            condition=lambda state: not self._needs_revision(state),
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
        editorial_policy: SouthlandEditorialPolicy | None = None,
    ) -> None:
        if story_concurrency < 1:
            raise ValueError("story_concurrency must be positive")
        self.ai_node = ai_node
        self.story_concurrency = story_concurrency
        self.max_revisions = max_revisions
        self.editorial_policy = editorial_policy or SouthlandEditorialPolicy()

    async def run_many(
        self, packets: Sequence[EvidencePacket]
    ) -> list[SouthlandRunEvidence]:
        semaphore = asyncio.Semaphore(self.story_concurrency)

        async def run_packet(packet: EvidencePacket) -> SouthlandRunEvidence:
            async with semaphore:
                workflow_runner = SouthlandEditorialWorkflow(
                    self.ai_node,
                    max_revisions=self.max_revisions,
                    editorial_policy=self.editorial_policy,
                )
                return await workflow_runner.run(packet)

        return list(await asyncio.gather(*(run_packet(packet) for packet in packets)))


def ai_result_record(result: AIWorkResult) -> dict[str, Any]:
    return asdict(result)
