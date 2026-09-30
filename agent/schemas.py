from __future__ import annotations

from typing import Any

from .models import EvidenceItem, Recommendation


def recommendation_from_payload(payload: dict[str, Any], source: str) -> Recommendation:
    recommendation = Recommendation(
        recommended_strategy=str(payload.get("recommended_strategy", "")),
        why=str(payload.get("why", "")),
        historical_evidence=_evidence_items(payload.get("historical_evidence", []), "Historical experience"),
        knowledge_evidence=_evidence_items(payload.get("knowledge_evidence", []), "Knowledge"),
        risks=_strings(payload.get("risks", [])),
        next_actions=_strings(payload.get("next_actions", [])),
        confidence=str(payload.get("confidence", "Moderate")),
        memory_impact=str(payload.get("memory_impact", "")),
        reasoning_steps=_strings(payload.get("reasoning_steps", [])),
        reasoning_source=source,
    )
    return recommendation.validate()


def _evidence_items(value: Any, default_type: str) -> list[EvidenceItem]:
    if not isinstance(value, list):
        value = [value] if value else []
    items = []
    for item in value:
        if isinstance(item, dict):
            items.append(
                EvidenceItem(
                    source_type=str(item.get("source_type", default_type)),
                    title=str(item.get("title", "Evidence")),
                    relevance=str(item.get("relevance", "Relevant")),
                    explanation=str(item.get("explanation", item.get("summary", ""))),
                    outcome=str(item.get("outcome", "")),
                    source=str(item.get("source", "")),
                )
            )
        else:
            items.append(EvidenceItem(default_type, "Evidence", "Relevant", str(item)))
    return items


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if not value:
        return []
    return [str(item) for item in value]
