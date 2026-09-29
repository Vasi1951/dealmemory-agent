from __future__ import annotations

import json
import logging
import os
from typing import Any

from .models import Deal, EvidenceItem, KnowledgeHit, MemoryHit, Recommendation
from .prompts import SYSTEM_PROMPT, recommendation_prompt
from .schemas import recommendation_from_payload

LOGGER = logging.getLogger(__name__)


class DemoReasoner:
    name = "Deterministic demo reasoning"
    live = False

    def generate(self, deal: Deal, similar_deals: list[MemoryHit], knowledge: list[KnowledgeHit]) -> Recommendation:
        pricing = any("pricing" in item.lower() for item in deal.objections)
        won = next((hit for hit in similar_deals if hit.deal.outcome == "WON"), None)
        lost = next((hit for hit in similar_deals if hit.deal.outcome == "LOST"), None)
        context_signals = f"{deal.customer_context} {' '.join(deal.objections)}".lower()
        implementation = any(term in context_signals for term in ("implementation", "integration"))
        security = "security" in context_signals or "compliance" in context_signals

        if pricing and won and lost:
            strategy = "Lead with quantified ROI before discussing commercial concessions, then support the case with technical proof."
            why = "Two comparable deals show a clear outcome contrast: value-led positioning won while early discounting lost."
            reasoning_steps = [
                f"Current deal has pricing resistance and {len(deal.objections)} recorded objection signals.",
                f"{won.deal.deal_id} succeeded with {', '.join(won.deal.successful_tactics[:2]) or 'value-led positioning'}.",
                f"{lost.deal.deal_id} was lost after {', '.join(lost.deal.failed_tactics[:2]) or 'an ineffective commercial response'}.",
                "The recommended response combines economic proof with execution confidence.",
            ]
            confidence = "High"
        elif pricing:
            strategy = "Quantify the business outcome and payback before discussing commercial concessions."
            why = "The current deal is signaling a value gap through its pricing objection; make the business case concrete before negotiating price."
            reasoning_steps = [
                "Current deal has pricing resistance.",
                "A quantified business case moves the conversation from list price to customer outcome.",
            ]
            confidence = "Moderate"
        else:
            strategy = "Align the buying committee on a measurable outcome, then reduce the highest execution risk with targeted proof."
            why = "The recommendation starts with the customer outcome and focuses proof on the objection most likely to block the next decision."
            reasoning_steps = [
                "Current deal context was normalized into objection and stakeholder signals.",
                "Targeted proof should address the highest-risk decision gate.",
            ]
            confidence = "Moderate" if similar_deals else "Foundational"

        risks = []
        if pricing:
            risks.append("Procurement may continue to anchor on price if the ROI case is not quantified.")
        if implementation:
            risks.append("Integration uncertainty could overshadow the commercial conversation.")
        if security:
            risks.append("A late security review could become the critical path.")
        if not risks:
            risks.append("A single-threaded evaluation could lose momentum if stakeholder priorities change.")

        next_actions = ["Build a customer-specific ROI case using the customer's baseline and target metric."]
        if implementation:
            next_actions.append("Prepare technical integration evidence and a phased rollout plan.")
        if security:
            next_actions.append("Schedule a security evidence review with the approval owner.")
        if not implementation and not security:
            next_actions.append("Confirm the buying committee, decision criteria, and mutual next step.")

        historical = [_memory_evidence(hit) for hit in similar_deals[:3]]
        knowledge_evidence = [_knowledge_evidence(hit) for hit in knowledge[:3]]
        impact = (
            f"Evidence-informed recommendation: {len(similar_deals)} historical experience(s) changed the strategy."
            if similar_deals
            else "Generic recommendation: current deal context and general knowledge only."
        )
        return Recommendation(
            recommended_strategy=strategy,
            why=why,
            historical_evidence=historical,
            knowledge_evidence=knowledge_evidence,
            risks=risks,
            next_actions=next_actions,
            confidence=confidence,
            memory_impact=impact,
            reasoning_steps=reasoning_steps,
        ).validate()


class GroqReasoner:
    name = "Groq LLM"
    live = True

    def __init__(self, api_key: str, model: str):
        from groq import Groq

        self.client = Groq(api_key=api_key)
        self.model = model

    def generate(self, deal: Deal, similar_deals: list[MemoryHit], knowledge: list[KnowledgeHit]) -> Recommendation:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": recommendation_prompt(deal, similar_deals, knowledge)},
            ],
        )
        payload = json.loads(response.choices[0].message.content)
        return recommendation_from_payload(payload, self.name)


class ResilientReasoner:
    def __init__(self, live: GroqReasoner | None = None):
        self.live_reasoner = live
        self.demo_reasoner = DemoReasoner()
        self.name = live.name if live else self.demo_reasoner.name
        self.live = live is not None

    def generate(self, deal: Deal, similar_deals: list[MemoryHit], knowledge: list[KnowledgeHit]) -> Recommendation:
        if self.live_reasoner:
            try:
                return self.live_reasoner.generate(deal, similar_deals, knowledge)
            except Exception as exc:
                LOGGER.warning("Groq reasoning failed; using deterministic demo response: %s", exc)
        return self.demo_reasoner.generate(deal, similar_deals, knowledge)


def build_reasoner() -> ResilientReasoner:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return ResilientReasoner()
    try:
        return ResilientReasoner(GroqReasoner(api_key, os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")))
    except Exception as exc:
        LOGGER.warning("Groq is configured but unavailable; using demo reasoning: %s", exc)
        return ResilientReasoner()


def _memory_evidence(hit: MemoryHit) -> EvidenceItem:
    reasons = ", ".join(hit.match_reasons[:4])
    return EvidenceItem(
        source_type="Historical experience",
        title=hit.deal.deal_id,
        relevance=f"{hit.similarity}% relevant",
        explanation=hit.key_lesson,
        outcome=hit.deal.outcome,
        source=f"Structured field match: {reasons}",
    )


def _knowledge_evidence(hit: KnowledgeHit) -> EvidenceItem:
    relevance = "High relevance" if hit.relevance_score >= 5 else "Relevant"
    return EvidenceItem(
        source_type="Knowledge",
        title=hit.title,
        relevance=relevance,
        explanation=hit.summary,
        source=hit.source,
    )
