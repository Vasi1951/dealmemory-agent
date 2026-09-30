from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .models import Deal, MemoryHit

LOGGER = logging.getLogger(__name__)


class MemoryProvider(Protocol):
    name: str
    live: bool

    def recall(self, deal: Deal, limit: int = 4) -> list[MemoryHit]: ...

    def retain(self, deal: Deal, outcome: str, lesson: str, recommendation: str) -> None: ...

    def reflect(self, deal: Deal, memories: list[MemoryHit]) -> str: ...


class LocalMemoryProvider:
    name = "DealMemory JSON"
    live = False

    def __init__(self, seed_path: Path, memory_path: Path | None = None):
        self.seed_path = seed_path
        self.memory_path = memory_path or seed_path.with_name("memories.json")
        self._seed = self._load(seed_path)

    def recall(self, deal: Deal, limit: int = 4) -> list[MemoryHit]:
        candidates = self.all_deals()
        ranked = []
        for candidate in candidates:
            if candidate.deal_id == deal.deal_id:
                continue
            score, reasons = similarity_breakdown(deal, candidate)
            ranked.append(
                MemoryHit(
                    deal=candidate,
                    similarity=score,
                    key_lesson=candidate.lessons_learned,
                    match_reasons=reasons,
                )
            )
        ranked.sort(key=lambda hit: (hit.similarity, hit.deal.outcome == "WON"), reverse=True)
        return ranked[:limit]

    def retain(self, deal: Deal, outcome: str, lesson: str, recommendation: str) -> None:
        records = self._load_memories()
        record = deal.as_dict()
        record.update(
            {
                "deal_id": deal.deal_id if deal.deal_id != "NEW-DEAL" else f"NEW-{len(records) + 1:03d}",
                "outcome": outcome,
                "lessons_learned": lesson,
                "recorded_recommendation": recommendation,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "source": "outcome-capture",
            }
        )
        records.append(record)
        self.memory_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def reflect(self, deal: Deal, memories: list[MemoryHit]) -> str:
        if not memories:
            return "No prior deal memories are available for reflection."
        wins = [item.deal for item in memories if item.deal.outcome == "WON"]
        losses = [item.deal for item in memories if item.deal.outcome == "LOST"]
        parts = []
        if wins:
            parts.append(f"Successful patterns: {wins[0].successful_tactics[0] if wins[0].successful_tactics else wins[0].lessons_learned}")
        if losses:
            parts.append(f"Failure pattern: {losses[0].failed_tactics[0] if losses[0].failed_tactics else losses[0].lessons_learned}")
        return " ".join(parts)

    def memory_count(self) -> int:
        return len(self.all_deals())

    def all_deals(self) -> list[Deal]:
        return [Deal.from_dict(item) for item in self._seed + self._load_memories()]

    def _load_memories(self) -> list[dict[str, Any]]:
        if not self.memory_path.exists():
            return []
        return self._load(self.memory_path)

    @staticmethod
    def _load(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Could not load memory data from %s: %s", path, exc)
            return []


class HindsightMemoryProvider:
    name = "Hindsight"

    def __init__(self, api_key: str, base_url: str, bank_id: str):
        from hindsight_client import Hindsight

        self.client = Hindsight(base_url=base_url, api_key=api_key)
        self.bank_id = bank_id
        self.live = True

    def recall(self, deal: Deal, limit: int = 4) -> list[MemoryHit]:
        result = self.client.recall(
            bank_id=self.bank_id,
            query=_deal_query(deal),
            max_tokens=3000,
            budget="low",
        )
        hits = []
        for item in getattr(result, "results", [])[:limit]:
            parsed = _parse_hindsight_deal(getattr(item, "text", ""))
            if parsed:
                hits.append(MemoryHit(parsed, 80, parsed.lessons_learned, source=self.name, match_reasons=["Hindsight recall"]))
        return hits

    def retain(self, deal: Deal, outcome: str, lesson: str, recommendation: str) -> None:
        payload = {
            "deal": deal.as_dict(),
            "outcome": outcome,
            "lesson": lesson,
            "recommendation": recommendation,
        }
        self.client.retain(
            bank_id=self.bank_id,
            content=json.dumps(payload),
            context="deal outcome",
            metadata={"deal_id": deal.deal_id, "outcome": outcome},
        )

    def reflect(self, deal: Deal, memories: list[MemoryHit]) -> str:
        result = self.client.reflect(
            bank_id=self.bank_id,
            query=f"What should the team learn before advancing this deal? {_deal_query(deal)}",
            context="DealMemory recommendation",
            budget="low",
        )
        return str(getattr(result, "text", ""))


class ResilientMemoryProvider:
    name = "DealMemory + Hindsight"

    def __init__(self, local: LocalMemoryProvider, remote: HindsightMemoryProvider | None = None):
        self.local = local
        self.remote = remote
        self.live = remote is not None

    def recall(self, deal: Deal, limit: int = 4) -> list[MemoryHit]:
        local_hits = self.local.recall(deal, limit=limit)
        if not self.remote:
            return local_hits
        try:
            remote_hits = self.remote.recall(deal, limit=limit)
            return _merge_hits(remote_hits, local_hits, limit)
        except Exception as exc:
            LOGGER.warning("Hindsight recall failed; using local memory: %s", exc)
            return local_hits

    def retain(self, deal: Deal, outcome: str, lesson: str, recommendation: str) -> None:
        self.local.retain(deal, outcome, lesson, recommendation)
        if self.remote:
            try:
                self.remote.retain(deal, outcome, lesson, recommendation)
            except Exception as exc:
                LOGGER.warning("Hindsight retain failed; local memory was kept: %s", exc)

    def reflect(self, deal: Deal, memories: list[MemoryHit]) -> str:
        if self.remote:
            try:
                return self.remote.reflect(deal, memories)
            except Exception as exc:
                LOGGER.warning("Hindsight reflect failed; using local reflection: %s", exc)
        return self.local.reflect(deal, memories)

    def memory_count(self) -> int:
        return self.local.memory_count()

    def all_deals(self) -> list[Deal]:
        return self.local.all_deals()


def build_memory_provider(project_root: Path) -> ResilientMemoryProvider:
    local = LocalMemoryProvider(project_root / "data" / "deals.json")
    api_key = os.getenv("HINDSIGHT_API_KEY")
    if not api_key:
        return ResilientMemoryProvider(local)
    try:
        remote = HindsightMemoryProvider(
            api_key=api_key,
            base_url=os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io"),
            bank_id=os.getenv("HINDSIGHT_BANK_ID", "dealmemory-demo"),
        )
        return ResilientMemoryProvider(local, remote)
    except Exception as exc:
        LOGGER.warning("Hindsight is configured but unavailable; using local memory: %s", exc)
        return ResilientMemoryProvider(local)


def similarity_score(left: Deal, right: Deal) -> int:
    return similarity_breakdown(left, right)[0]


def similarity_breakdown(left: Deal, right: Deal) -> tuple[int, list[str]]:
    score = 0.0
    reasons = []
    if left.industry.lower() == right.industry.lower():
        score += 20
        reasons.append("Industry match")
    if left.segment.lower() == right.segment.lower():
        score += 10
        reasons.append("Segment match")
    if left.stage.lower() == right.stage.lower():
        score += 8
        reasons.append("Stage match")
    if left.competitor.lower() == right.competitor.lower() and left.competitor.lower() not in {"", "none identified"}:
        score += 14
        reasons.append("Competitor match")
    objection_overlap = _jaccard(left.objections, right.objections)
    if objection_overlap:
        reasons.append("Objection match")
    score += 28 * objection_overlap
    stakeholder_overlap = _jaccard(left.stakeholders, right.stakeholders)
    if stakeholder_overlap:
        reasons.append("Stakeholder match")
    score += 10 * stakeholder_overlap
    context_overlap = _text_overlap(left.customer_context, right.customer_context)
    score += 12 * context_overlap
    if context_overlap >= 0.05:
        reasons.append("Customer context match")
    size_gap = abs(left.deal_size - right.deal_size) / max(left.deal_size, right.deal_size, 1)
    size_score = max(0.0, 10 * (1 - size_gap))
    score += size_score
    if size_score >= 7:
        reasons.append("Similar deal size")
    return max(1, min(99, round(score))), reasons or ["Context overlap"]


def _jaccard(left: list[str], right: list[str]) -> float:
    left_tokens = {item.lower() for item in left}
    right_tokens = {item.lower() for item in right}
    if not left_tokens and not right_tokens:
        return 1.0
    return len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)


def _text_overlap(left: str, right: str) -> float:
    stopwords = {"the", "and", "for", "with", "from", "that", "this", "was", "were", "are", "but", "has", "have"}
    left_tokens = {token for token in left.lower().replace("/", " ").split() if len(token) > 3 and token not in stopwords}
    right_tokens = {token for token in right.lower().replace("/", " ").split() if len(token) > 3 and token not in stopwords}
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)


def _deal_query(deal: Deal) -> str:
    return " ".join([deal.industry, deal.segment, deal.competitor, *deal.objections, deal.customer_context])


def _parse_hindsight_deal(text: str) -> Deal | None:
    try:
        value = json.loads(text)
        return Deal.from_dict(value.get("deal", value))
    except (json.JSONDecodeError, TypeError, AttributeError):
        return None


def _merge_hits(primary: list[MemoryHit], secondary: list[MemoryHit], limit: int) -> list[MemoryHit]:
    merged: dict[str, MemoryHit] = {}
    for hit in primary + secondary:
        existing = merged.get(hit.deal.deal_id)
        if existing is None or hit.similarity > existing.similarity:
            merged[hit.deal.deal_id] = hit
    return sorted(merged.values(), key=lambda hit: hit.similarity, reverse=True)[:limit]
