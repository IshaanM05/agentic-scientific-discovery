"""Typed handoff payloads (design Section 7).

Agents exchange these structured objects, never free text alone. Free-text
rationale rides along in dedicated fields.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

HypId = str


class Evidence(BaseModel):
    id: str
    source_id: str                     # DOI / arXiv ID / OpenAlex ID or run_id
    source_type: Literal["doi", "arxiv", "openalex", "run"] = "arxiv"
    title: str = ""
    claim: str
    supports: list[HypId] = Field(default_factory=list)
    contradicts: list[HypId] = Field(default_factory=list)
    confidence: float = 0.7
    resolved: Optional[bool] = None    # None = not checked, True/False = resolver outcome
    url: str = ""


class PredictedSignature(BaseModel):
    test_id: str
    expected_outcome: str


class HypothesisProposal(BaseModel):
    id: str
    name: str
    parent: HypId                      # which differential class it rolls up into
    mechanism: str
    predicted_signatures: list[PredictedSignature] = Field(default_factory=list)
    origin: Literal["agent_generated", "default"] = "agent_generated"
    proposed_by: str = "house"


class TestSpec(BaseModel):
    test_id: str
    target_id: str
    params: dict = Field(default_factory=dict)
    cost_units: float
    expected_discriminates: list[HypId] = Field(default_factory=list)
    approved_by: str = "cuddy"
    rationale_ref: str = ""


class TestResult(BaseModel):
    test_id: str
    target_id: str
    run_id: str
    metrics: dict
    uncertainties: dict = Field(default_factory=dict)
    outcome_bin: int
    outcome_label: str
    plot_path: str = ""
    code_hash: str = ""
    seed: int = 0
    runtime_s: float = 0.0
    params: dict = Field(default_factory=dict)


class ResultAssessment(BaseModel):
    test_id: str
    run_id: str
    quality: Literal["ok", "marginal", "unreliable"]
    weight: float
    likelihoods: dict[HypId, float]
    critique: str
    surprise: bool = False
    follow_up_request: Optional["CounterExperimentRequest"] = None


class CounterExperimentRequest(BaseModel):
    from_agent: str = "foreman"
    reason: str
    suggested_test_id: str
    params: dict = Field(default_factory=dict)
    targets_hypothesis: HypId


class PlannerCandidate(BaseModel):
    test_id: str
    eig_bits: float
    contrarian_bits: float = 0.0
    cost: float
    score: float


class PlannerRationale(BaseModel):
    round: int
    candidates: list[PlannerCandidate]
    chosen: list[str]
    runner_up: Optional[str] = None
    budget_left: dict
    stop: bool = False
    stop_reason: str = ""


class Dissent(BaseModel):
    agent: str
    objection: str


class Verdict(BaseModel):
    target_id: str
    label: HypId
    label_text: str
    posterior: dict[HypId, float]
    top_posterior: float
    interval: tuple[float, float]
    evidence_ids: list[str]
    run_ids: list[str]
    dissent: list[Dissent] = Field(default_factory=list)
    required_followup: list[str] = Field(default_factory=list)
    needs_human: bool = False
    claim_strength: Literal["candidate", "likely_false_positive", "undetermined"] = "candidate"
    tests_used: int = 0
    cost_used: float = 0.0


class LessonLearned(BaseModel):
    target_id: str
    lesson: str
    decisive_test: Optional[str] = None
    stats: dict = Field(default_factory=dict)


ResultAssessment.model_rebuild()
