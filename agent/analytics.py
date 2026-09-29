from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .models import Deal


@dataclass
class InsightSummary:
    total_experiences: int
    successful_outcomes: int
    failed_outcomes: int
    stalled_outcomes: int
    lessons_generated: int
    outcome_distribution: dict[str, int]
    stage_distribution: dict[str, int]
    patterns: list[tuple[str, str, int, str]]
    emerging_risks: list[str]
    active_competitors: list[tuple[str, int]]


def risk_level(deal: Deal) -> str:
    objections = " ".join(deal.objections).lower()
    context = deal.customer_context.lower()
    if "security" in objections or len(deal.objections) >= 2:
        return "High"
    if any(term in objections or term in context for term in ("implementation", "integration", "stakeholder")):
        return "Medium"
    return "Low"


def filter_deals(
    deals: Iterable[Deal],
    query: str = "",
    stage: str = "All",
    industry: str = "All",
    outcome: str = "All",
    risk: str = "All",
) -> list[Deal]:
    query_lower = query.strip().lower()
    filtered = []
    for deal in deals:
        searchable = " ".join([deal.deal_id, deal.company, deal.industry, deal.competitor]).lower()
        if query_lower and query_lower not in searchable:
            continue
        if stage != "All" and deal.stage != stage:
            continue
        if industry != "All" and deal.industry != industry:
            continue
        if outcome != "All" and deal.outcome != outcome:
            continue
        if risk != "All" and risk_level(deal) != risk:
            continue
        filtered.append(deal)
    return filtered


def summarize_deals(deals: Iterable[Deal]) -> InsightSummary:
    values = list(deals)
    outcomes = Counter(deal.outcome for deal in values)
    stages = Counter(deal.stage for deal in values)
    won = outcomes.get("WON", 0)
    lost = outcomes.get("LOST", 0)
    stalled = outcomes.get("STALLED", 0)
    patterns = []

    pricing = _count_objection(values, "pricing")
    if pricing:
        patterns.append(("Pricing objections", "deals", pricing, "Value must be established before commercial concessions."))

    roi_success = sum(1 for deal in values if deal.outcome == "WON" and _contains(deal, "roi", "payback", "labor savings"))
    if roi_success:
        patterns.append(("ROI-first strategy", "successful outcomes", roi_success, "Quantified value helped buyers approve the investment."))

    discount_losses = sum(1 for deal in values if deal.outcome == "LOST" and _contains(deal, "discount"))
    if discount_losses:
        patterns.append(("Early discounting", "losses", discount_losses, "Discounting appeared before the customer value case was proven."))

    technical_wins = sum(1 for deal in values if deal.outcome == "WON" and _contains(deal, "technical", "integration", "security", "sandbox"))
    if technical_wins:
        patterns.append(("Technical validation", "successful outcomes", technical_wins, "Proof reduced perceived implementation or compliance risk."))

    active_competitors = Counter(
        deal.competitor
        for deal in values
        if deal.outcome not in {"WON", "LOST"} and deal.competitor not in {"", "None identified"}
    )
    emerging_risks = []
    enterprise_implementation = sum(
        1 for deal in values if deal.segment.lower() == "enterprise" and _contains(deal, "implementation")
    )
    if enterprise_implementation:
        emerging_risks.append(f"Implementation concerns appear in {enterprise_implementation} enterprise deal(s).")
    security_count = _count_objection(values, "security")
    if security_count:
        emerging_risks.append(f"Security and compliance is a decision gate in {security_count} deal(s).")
    if active_competitors:
        competitor, count = active_competitors.most_common(1)[0]
        emerging_risks.append(f"{competitor} appears in {count} active evaluation(s).")

    return InsightSummary(
        total_experiences=len(values),
        successful_outcomes=won,
        failed_outcomes=lost,
        stalled_outcomes=stalled,
        lessons_generated=sum(bool(deal.lessons_learned.strip()) for deal in values),
        outcome_distribution=dict(outcomes),
        stage_distribution=dict(stages),
        patterns=patterns,
        emerging_risks=emerging_risks,
        active_competitors=active_competitors.most_common(),
    )


def validate_dataset(deals: Iterable[Deal]) -> list[str]:
    values = list(deals)
    errors = []
    ids = [deal.deal_id for deal in values]
    if len(ids) != len(set(ids)):
        errors.append("Deal IDs must be unique")
    allowed_outcomes = {"WON", "LOST", "STALLED", "OPEN"}
    for deal in values:
        if not deal.company or not deal.industry or deal.deal_size < 0:
            errors.append(f"{deal.deal_id} is missing required deal fields")
        if deal.outcome not in allowed_outcomes:
            errors.append(f"{deal.deal_id} has unsupported outcome {deal.outcome}")
    return errors


def _count_objection(deals: Iterable[Deal], term: str) -> int:
    return sum(1 for deal in deals if any(term in objection.lower() for objection in deal.objections))


def _contains(deal: Deal, *terms: str) -> bool:
    text = " ".join(
        deal.successful_tactics + [deal.sales_response, deal.lessons_learned] + deal.actions_taken
    ).lower()
    return any(term.lower() in text for term in terms)
