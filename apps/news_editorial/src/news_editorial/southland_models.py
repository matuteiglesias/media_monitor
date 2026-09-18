"""Typed internal outputs for the Southland editorial AI workflow.

These are execution schemas, not promoted Media Monitor contracts.  Stable
outputs remain news_piece_brief.v1 and news_article_draft.v1.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceAnalysis(StrictModel):
    factual_kernel: list[str] = Field(min_length=1)
    actors: list[str] = Field(default_factory=list)
    documented_actions: list[str] = Field(default_factory=list)
    attributed_claims: list[str] = Field(default_factory=list)
    publisher_interpretations: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    candidate_mechanisms: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class SouthlandDecision(StrictModel):
    decision: Literal["accept", "reject"]
    reason: str = Field(min_length=1)
    comic_mechanism: str = ""
    preserved_event_topology: str = ""
    aliases: dict[str, str] = Field(default_factory=dict)
    literalizations: list[str] = Field(default_factory=list)
    fictional_escalations: list[str] = Field(default_factory=list)
    forbidden_distortions: list[str] = Field(default_factory=list)


class DraftSection(StrictModel):
    heading: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class DraftFactCheckFlag(StrictModel):
    flag: str = Field(min_length=1)
    severity: Literal["low", "medium", "high"]
    note: str = Field(min_length=1)


class SouthlandDraft(StrictModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    dek: str = Field(min_length=1)
    lede: str = Field(min_length=1)
    sections: list[DraftSection] = Field(min_length=1)
    body_md: str = Field(min_length=1)
    fact_check_flags: list[DraftFactCheckFlag] = Field(default_factory=list)
    revision_notes: list[str] = Field(default_factory=list)


class SouthlandReview(StrictModel):
    decision: Literal["approve", "revise", "reject"]
    notes: list[str] = Field(default_factory=list)
    topology_preserved: bool
    fiction_separated: bool
    attribution_preserved: bool
    alias_consistent: bool
    revision_instruction: str = ""


class SouthlandWorkflowResult(StrictModel):
    status: Literal["accepted", "rejected", "failed"]
    index_id: str = Field(min_length=1)
    workflow_id: str = Field(min_length=1)
    analysis: EvidenceAnalysis | None = None
    decision: SouthlandDecision | None = None
    draft: SouthlandDraft | None = None
    review: SouthlandReview | None = None
    revisions_used: int = 0
    stage_work_ids: list[str] = Field(default_factory=list)
    error: str = ""
