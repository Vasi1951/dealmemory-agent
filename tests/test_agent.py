from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from agent.agent import DealMemoryAgent
from agent.analytics import validate_dataset
from agent.llm import ResilientReasoner
from agent.memory import LocalMemoryProvider, ResilientMemoryProvider
from agent.models import Deal
from agent.vybe import LocalKnowledgeProvider, ResilientKnowledgeProvider


ROOT = Path(__file__).resolve().parents[1]


def make_deal(**overrides):
    value = {
        "deal_id": "NEW-DEAL",
        "company": "Pinecrest Systems",
        "industry": "Logistics",
        "segment": "Mid-market",
        "deal_size": 90000,
        "stage": "Negotiation",
        "stakeholders": ["VP Operations", "Finance Director"],
        "objections": ["Pricing Objection", "Implementation Risk"],
        "competitor": "RoutePilot",
        "customer_context": "The buyer wants measurable savings and is concerned about integration effort.",
    }
    value.update(overrides)
    return Deal.from_dict(value)


def make_agent(tmp_path):
    memory = ResilientMemoryProvider(
        LocalMemoryProvider(ROOT / "data" / "deals.json", tmp_path / "memories.json")
    )
    knowledge = ResilientKnowledgeProvider(LocalKnowledgeProvider(ROOT / "data" / "knowledge.json"))
    return DealMemoryAgent(memory=memory, knowledge=knowledge, reasoner=ResilientReasoner())


def test_deal_parsing_normalizes_lists_and_defaults():
    deal = Deal.from_dict({"company": "Example", "objections": "Pricing Objection, Security / Compliance"})

    assert deal.company == "Example"
    assert deal.objections == ["Pricing Objection", "Security / Compliance"]
    assert deal.stage == "Discovery"
    assert deal.deal_size == 0


def test_similar_deal_retrieval_surfaces_the_pricing_contrast(tmp_path):
    agent = make_agent(tmp_path)

    analysis = agent.analyze_deal(make_deal(), memory_enabled=True)
    deal_ids = {hit.deal.deal_id for hit in analysis.similar_deals}

    assert {"D-097", "D-104"}.issubset(deal_ids)
    assert analysis.similar_deals[0].similarity >= analysis.similar_deals[-1].similarity
    assert any("Customer context match" in hit.match_reasons for hit in analysis.similar_deals)


def test_recommendation_generation_connects_won_and_lost_evidence(tmp_path):
    agent = make_agent(tmp_path)

    analysis = agent.analyze_deal(make_deal(), memory_enabled=True)
    recommendation = analysis.recommendation

    assert "ROI" in recommendation.recommended_strategy
    assert any(item.title == "D-104" for item in recommendation.historical_evidence)
    assert any(item.title == "D-097" for item in recommendation.historical_evidence)
    assert recommendation.knowledge_evidence
    assert recommendation.memory_impact.startswith("Evidence-informed")
    assert recommendation.next_actions


def test_memory_recording_is_retrievable(tmp_path):
    provider = LocalMemoryProvider(ROOT / "data" / "deals.json", tmp_path / "memories.json")
    deal = make_deal()

    provider.retain(deal, "WON", "ROI proof worked", "Lead with quantified ROI")
    hits = provider.recall(make_deal(deal_id="ANOTHER-DEAL"), limit=20)

    assert (tmp_path / "memories.json").exists()
    assert any(hit.deal.lessons_learned == "ROI proof worked" for hit in hits)


def test_outcome_recording_writes_learning_loop(tmp_path):
    agent = make_agent(tmp_path)
    analysis = agent.analyze_deal(make_deal(), memory_enabled=True)

    agent.record_outcome(analysis, "WON", "The ROI case and proof reduced price resistance.")
    records = json.loads((tmp_path / "memories.json").read_text(encoding="utf-8"))

    assert records[-1]["outcome"] == "WON"
    assert records[-1]["lessons_learned"].startswith("The ROI case")


def test_demo_mode_works_without_external_services(tmp_path):
    agent = make_agent(tmp_path)

    analysis = agent.analyze_deal(make_deal(), memory_enabled=False)
    memory_analysis = agent.analyze_deal(make_deal(), memory_enabled=True)

    assert analysis.runtime_mode == "DEMO MODE"
    assert not analysis.similar_deals
    assert analysis.knowledge
    assert analysis.recommendation.recommended_strategy
    assert analysis.recommendation.memory_impact.startswith("Generic recommendation")
    assert memory_analysis.recommendation.memory_impact.startswith("Evidence-informed")


def test_dataset_validation_passes_for_seed_data():
    provider = LocalMemoryProvider(ROOT / "data" / "deals.json")

    assert validate_dataset(provider.all_deals()) == []


def test_learning_loop_makes_recorded_deal_retrievable(tmp_path):
    agent = make_agent(tmp_path)
    first_analysis = agent.analyze_deal(make_deal(), memory_enabled=True)

    agent.record_outcome(first_analysis, "WON", "ROI proof converted price resistance.")
    second_analysis = agent.analyze_deal(make_deal(deal_id="NEXT-DEAL"), memory_enabled=True)

    assert any(
        hit.deal.deal_id == "NEW-001" and hit.key_lesson == "ROI proof converted price resistance."
        for hit in second_analysis.similar_deals
    )


def test_application_imports_cleanly():
    result = subprocess.run([sys.executable, "-c", "import app"], cwd=ROOT, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
