from __future__ import annotations

import logging
from pathlib import Path

from .llm import ResilientReasoner, build_reasoner
from .memory import ResilientMemoryProvider, build_memory_provider
from .models import Analysis, Deal
from .vybe import ResilientKnowledgeProvider, build_knowledge_provider

LOGGER = logging.getLogger(__name__)


class DealMemoryAgent:
    def __init__(
        self,
        project_root: Path | None = None,
        memory: ResilientMemoryProvider | None = None,
        knowledge: ResilientKnowledgeProvider | None = None,
        reasoner: ResilientReasoner | None = None,
    ):
        self.project_root = project_root or Path(__file__).resolve().parents[1]
        self.memory = memory or build_memory_provider(self.project_root)
        self.knowledge = knowledge or build_knowledge_provider(self.project_root)
        self.reasoner = reasoner or build_reasoner()

    def analyze_deal(self, deal: Deal | dict, memory_enabled: bool = True) -> Analysis:
        if isinstance(deal, Deal):
            normalized = deal
        elif hasattr(deal, "as_dict") and callable(deal.as_dict):
            normalized = Deal.from_dict(deal.as_dict())
        elif hasattr(deal, "__dict__"):
            normalized = Deal.from_dict(vars(deal))
        else:
            normalized = Deal.from_dict(deal)
        similar = self.memory.recall(normalized) if memory_enabled else []
        knowledge = self.knowledge.search(normalized)
        recommendation = self.reasoner.generate(normalized, similar, knowledge)
        recommendation.reasoning_source = self.reasoner.name
        recommendation.validate()
        providers = {
            "Memory": "LIVE" if self.memory.live else "LOCAL",
            "Vybe": "LIVE" if self.knowledge.live else "LOCAL",
            "Reasoning": "LIVE" if self.reasoner.live else "DEMO",
        }
        return Analysis(
            deal=normalized,
            similar_deals=similar,
            knowledge=knowledge,
            recommendation=recommendation,
            memory_enabled=memory_enabled,
            runtime_mode="LIVE MODE" if any(value == "LIVE" for value in providers.values()) else "DEMO MODE",
            provider_status=providers,
            retrieval_method="Structured field match" if not self.memory.live else "Hindsight recall + structured field match",
        )

    def list_deals(self) -> list[Deal]:
        return self.memory.all_deals()

    def record_outcome(self, analysis: Analysis, outcome: str, lesson: str | None = None) -> None:
        normalized_outcome = outcome.upper().strip()
        if normalized_outcome not in {"WON", "LOST", "STALLED"}:
            raise ValueError("Outcome must be WON, LOST, or STALLED")
        final_lesson = lesson or self._default_lesson(analysis, normalized_outcome)
        recommendation = analysis.recommendation.recommended_strategy
        self.memory.retain(analysis.deal, normalized_outcome, final_lesson, recommendation)

    @staticmethod
    def _default_lesson(analysis: Analysis, outcome: str) -> str:
        strategy = analysis.recommendation.recommended_strategy.rstrip(".")
        if outcome == "WON":
            return f"{strategy} was effective for this deal."
        if outcome == "LOST":
            return f"The recommendation was not enough to win; revisit {strategy.lower()} and the buyer's decision criteria."
        return f"The deal stalled; keep the recommendation but add a clearer mutual next step around {strategy.lower()}."
