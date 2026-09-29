from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Deal:
    deal_id: str
    company: str
    industry: str
    segment: str
    deal_size: int
    stage: str
    stakeholders: list[str]
    objections: list[str]
    competitor: str
    customer_context: str
    actions_taken: list[str]
    sales_response: str
    customer_reaction: str
    outcome: str
    successful_tactics: list[str]
    failed_tactics: list[str]
    lessons_learned: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Deal":
        fields = {
            "deal_id": str(value.get("deal_id", "NEW-DEAL")),
            "company": str(value.get("company", "Prospect")),
            "industry": str(value.get("industry", "Technology")),
            "segment": str(value.get("segment", "Mid-market")),
            "deal_size": int(value.get("deal_size", 0) or 0),
            "stage": str(value.get("stage", "Discovery")),
            "stakeholders": _list(value.get("stakeholders")),
            "objections": _list(value.get("objections")),
            "competitor": str(value.get("competitor", "None identified")),
            "customer_context": str(value.get("customer_context", "")),
            "actions_taken": _list(value.get("actions_taken")),
            "sales_response": str(value.get("sales_response", "")),
            "customer_reaction": str(value.get("customer_reaction", "")),
            "outcome": str(value.get("outcome", "OPEN")),
            "successful_tactics": _list(value.get("successful_tactics")),
            "failed_tactics": _list(value.get("failed_tactics")),
            "lessons_learned": str(value.get("lessons_learned", "")),
        }
        return cls(**fields)

    def as_dict(self) -> dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "company": self.company,
            "industry": self.industry,
            "segment": self.segment,
            "deal_size": self.deal_size,
            "stage": self.stage,
            "stakeholders": self.stakeholders,
            "objections": self.objections,
            "competitor": self.competitor,
            "customer_context": self.customer_context,
            "actions_taken": self.actions_taken,
            "sales_response": self.sales_response,
            "customer_reaction": self.customer_reaction,
            "outcome": self.outcome,
            "successful_tactics": self.successful_tactics,
            "failed_tactics": self.failed_tactics,
            "lessons_learned": self.lessons_learned,
        }


@dataclass
class MemoryHit:
    deal: Deal
    similarity: int
    key_lesson: str
    source: str = "DealMemory"
    match_reasons: list[str] = field(default_factory=list)


@dataclass
class KnowledgeHit:
    title: str
    category: str
    summary: str
    guidance: str
    source: str = "Vybe Vault"
    relevance_score: int = 0


@dataclass
class EvidenceItem:
    source_type: str
    title: str
    relevance: str
    explanation: str
    outcome: str = ""
    source: str = ""


@dataclass
class Recommendation:
    recommended_strategy: str
    why: str
    historical_evidence: list[EvidenceItem]
    knowledge_evidence: list[EvidenceItem]
    risks: list[str]
    next_actions: list[str]
    confidence: str
    memory_impact: str
    reasoning_steps: list[str] = field(default_factory=list)
    reasoning_source: str = "Demo reasoning"

    def validate(self) -> "Recommendation":
        if not self.recommended_strategy.strip():
            raise ValueError("Recommendation strategy cannot be empty")
        if not self.why.strip():
            raise ValueError("Recommendation explanation cannot be empty")
        if self.confidence not in {"Foundational", "Moderate", "High"}:
            self.confidence = "Moderate"
        if not self.memory_impact.strip():
            self.memory_impact = "No historical memory was used."
        return self


@dataclass
class Analysis:
    deal: Deal
    similar_deals: list[MemoryHit]
    knowledge: list[KnowledgeHit]
    recommendation: Recommendation
    memory_enabled: bool
    runtime_mode: str
    provider_status: dict[str, str] = field(default_factory=dict)
    retrieval_method: str = "Structured field match"


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item) for item in value if str(item).strip()]
