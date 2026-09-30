from __future__ import annotations

import html
import logging
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from agent import DealMemoryAgent
from agent.analytics import filter_deals, risk_level, summarize_deals
from agent.models import Analysis, Deal, EvidenceItem

logging.basicConfig(level=logging.INFO)
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

st.set_page_config(page_title="DealMemory", page_icon="DM", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
    :root {
        --text-primary: #15202b;
        --text-secondary: #354452;
        --text-muted: #53616e;
        --border: #c7d1d9;
        --surface: #ffffff;
        --surface-subtle: #f1f4f6;
        --canvas: #f4f6f8;
        --accent: #155f8a;
        --accent-hover: #0d4f75;
        --accent-soft: #e8f2f8;
        --focus: #0b63ce;
        --warning: #80500d;
        --warning-soft: #fff4df;
        --danger: #8f2f2f;
        --danger-soft: #fcebea;
        --success: #17643f;
        --success-soft: #e7f4ed;
    }
    html, body { font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--text-primary); }
    .stApp { background: var(--canvas); color: var(--text-primary); }
    .stApp p, .stApp li, .stApp label, .stApp [data-testid="stMarkdownContainer"] { color: var(--text-primary); }
    .stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p { color: var(--text-secondary) !important; }
    [data-testid="stHeader"], #MainMenu, footer { visibility: hidden; height: 0; }
    [data-testid="stAppViewContainer"] > .main .block-container { max-width: 1440px; padding: 2rem 3.25rem 4rem; }
    [data-testid="stSidebar"] { display: none; }
    h1, h2, h3 { color: var(--text-primary); letter-spacing: -0.025em; }
    h1 { font-size: 2rem !important; line-height: 1.1 !important; margin: 0.15rem 0 0.35rem !important; }
    h2 { font-size: 1.28rem !important; margin: 0.2rem 0 0.8rem !important; }
    h3 { font-size: 0.74rem !important; text-transform: uppercase; letter-spacing: 0.11em; color: var(--text-secondary); margin: 1.25rem 0 0.65rem !important; }
    p { line-height: 1.5; }
    .product-header { display: flex; align-items: center; gap: 1rem; min-height: 3rem; border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 1.5rem; }
    .brand { font-size: 1.15rem; font-weight: 760; letter-spacing: 0.08em; white-space: nowrap; }
    .brand-subtitle { color: var(--text-secondary); font-size: 0.74rem; letter-spacing: 0.03em; white-space: nowrap; }
    .nav-wrap { flex: 1; }
    .status-line { display: flex; align-items: center; justify-content: flex-end; gap: 0.85rem; white-space: nowrap; }
    .mode { color: var(--text-secondary); font-size: 0.73rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
    .memory-status { color: var(--accent); font-size: 0.8rem; font-weight: 700; }
    div[role="radiogroup"] { gap: 0.15rem; }
    div[role="radiogroup"] > label { border-radius: 5px; padding: 0.32rem 0.7rem; color: var(--text-primary) !important; }
    div[role="radiogroup"] > label p, [data-testid="stRadio"] label p { color: var(--text-primary) !important; }
    div[role="radiogroup"] > label:hover { background: var(--accent-soft); }
    .page-intro { color: var(--text-secondary); font-size: 0.93rem; max-width: 700px; margin-bottom: 1.2rem; }
    .surface { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 1.2rem 1.35rem; }
    .surface-tight { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 0.85rem 1rem; }
    .eyebrow { color: var(--text-secondary); font-size: 0.7rem; font-weight: 750; letter-spacing: 0.12em; text-transform: uppercase; }
    .muted { color: var(--text-secondary); }
    .deal-title { font-size: 1.48rem; font-weight: 720; letter-spacing: -0.025em; margin: 0.25rem 0; }
    .deal-meta { color: var(--text-secondary); font-size: 0.86rem; }
    .tag { display: inline-block; border: 1px solid var(--border); border-radius: 4px; color: var(--text-secondary); font-size: 0.72rem; font-weight: 650; margin: 0 0.25rem 0.25rem 0; padding: 0.2rem 0.42rem; }
    .tag-accent { border-color: #9fc1d5; color: var(--accent); background: var(--accent-soft); }
    .outcome-won { color: var(--success); font-weight: 750; }
    .outcome-lost { color: var(--danger); font-weight: 750; }
    .outcome-stalled { color: var(--warning); font-weight: 750; }
    .outcome-open { color: var(--text-secondary); font-weight: 700; }
    .risk-high { color: var(--danger); font-weight: 700; }
    .risk-medium { color: var(--warning); font-weight: 700; }
    .risk-low { color: var(--success); font-weight: 700; }
    .brief-label { color: var(--text-secondary); font-size: 0.72rem; font-weight: 750; letter-spacing: 0.1em; text-transform: uppercase; }
    .brief-strategy { color: var(--text-primary); border-left: 3px solid var(--accent); background: var(--accent-soft); padding: 0.8rem 0.95rem; font-size: 1.08rem; font-weight: 650; line-height: 1.45; margin: 0.55rem 0 1rem; }
    .brief-why { font-size: 0.94rem; line-height: 1.55; }
    .action-row { border-top: 1px solid var(--border); padding: 0.72rem 0; display: flex; gap: 0.75rem; line-height: 1.4; }
    .action-number { color: var(--accent); font-weight: 800; min-width: 1.5rem; }
    .evidence-row { border-top: 1px solid var(--border); padding: 0.8rem 0; }
    .evidence-row:first-child { border-top: 0; padding-top: 0; }
    .evidence-title { font-weight: 700; }
    .evidence-meta { color: var(--text-secondary); font-size: 0.75rem; margin-top: 0.18rem; }
    .evidence-copy { font-size: 0.86rem; line-height: 1.48; margin-top: 0.35rem; }
    .metric-strip { border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); padding: 0.9rem 0; margin: 1rem 0 1.4rem; }
    .metric-label { color: var(--text-secondary); font-size: 0.69rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; }
    .metric-value { color: var(--text-primary); font-size: 1.35rem; font-weight: 760; margin-top: 0.15rem; }
    .insight-row { border-top: 1px solid var(--border); padding: 0.9rem 0; }
    .insight-row:first-child { border-top: 0; }
    .insight-name { font-weight: 720; }
    .insight-detail { color: var(--text-secondary); font-size: 0.85rem; line-height: 1.45; margin-top: 0.2rem; }
    .empty-state { color: var(--text-secondary); background: var(--surface); border: 1px dashed var(--border); border-radius: 6px; padding: 2rem; text-align: center; }
    .stButton > button, [data-testid="stFormSubmitButton"] button { border-radius: 5px; font-weight: 650; color: var(--text-primary) !important; background: var(--surface) !important; border: 1px solid var(--border) !important; min-height: 2.45rem; }
    .stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover { color: var(--accent-hover) !important; border-color: var(--accent) !important; background: var(--accent-soft) !important; }
    .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] { color: #ffffff !important; background: var(--accent) !important; border-color: var(--accent) !important; }
    .stButton > button[kind="primary"] *, [data-testid="stFormSubmitButton"] button[kind="primary"] * { color: #ffffff !important; }
    .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover { color: #ffffff !important; background: var(--accent-hover) !important; border-color: var(--accent-hover) !important; }
    .stButton > button[kind="primary"]:hover *, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover * { color: #ffffff !important; }
    button:focus-visible, input:focus-visible, textarea:focus-visible, [role="combobox"]:focus-visible { outline: 3px solid var(--focus) !important; outline-offset: 2px !important; }
    button:disabled { color: var(--text-muted) !important; background: var(--surface-subtle) !important; border-color: var(--border) !important; }
    .stTextInput input, .stTextArea textarea, .stNumberInput input { border-radius: 5px; color: var(--text-primary) !important; background: var(--surface) !important; border: 1px solid var(--border) !important; }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder { color: var(--text-muted) !important; opacity: 1 !important; }
    .stNumberInput button { color: var(--text-primary) !important; background: var(--surface) !important; border-color: var(--border) !important; }
    .stNumberInput button:hover { color: var(--accent-hover) !important; background: var(--accent-soft) !important; }
    [data-testid="stWidgetLabel"] label, [data-testid="stWidgetLabel"] p { color: var(--text-primary) !important; font-weight: 600; }
    [data-baseweb="select"] > div { border-radius: 5px; color: var(--text-primary) !important; background: var(--surface) !important; border-color: var(--border) !important; }
    [data-baseweb="select"] *, [role="listbox"] *, [role="option"] { color: var(--text-primary) !important; }
    [data-baseweb="popover"], [role="listbox"] { color: var(--text-primary) !important; background: var(--surface) !important; border: 1px solid var(--border) !important; }
    [role="option"][aria-selected="true"], [role="option"]:hover { background: var(--accent-soft) !important; }
    .stSelectbox [role="group"] { border: 1px solid var(--border) !important; border-radius: 5px !important; background: var(--surface) !important; }
    .stSelectbox [role="group"] input { color: var(--text-primary) !important; background: var(--surface) !important; }
    .stSelectbox [role="group"] button { color: var(--text-secondary) !important; background: var(--surface) !important; }
    [data-testid="stCheckbox"] label { color: var(--text-primary) !important; }
    [data-testid="stCheckbox"] label > div:first-of-type { background: var(--accent) !important; }
    [data-testid="stCheckbox"] label[data-selected="false"] > div:first-of-type { background: var(--border) !important; }
    [data-testid="stCheckbox"] label > div:first-of-type > div { background: #ffffff !important; }
    [data-testid="stExpander"] { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; }
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary p { color: var(--text-primary) !important; }
    [data-testid="stAlert"] { color: var(--text-primary) !important; background: var(--surface) !important; border: 1px solid var(--border) !important; }
    [data-testid="stAlert"] p { color: var(--text-primary) !important; }
    .business-table { width: 100%; border-collapse: collapse; color: var(--text-primary); background: var(--surface); border: 1px solid var(--border); font-size: 0.86rem; }
    .business-table th { color: var(--text-secondary); background: var(--surface-subtle); font-size: 0.71rem; font-weight: 750; letter-spacing: 0.08em; text-align: left; text-transform: uppercase; }
    .business-table th, .business-table td { padding: 0.72rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: top; }
    .business-table td { color: var(--text-primary); line-height: 1.35; }
    .business-table tbody tr:hover { background: var(--accent-soft); }
    .business-table tbody tr:last-child td { border-bottom: 0; }
    .table-scroll { overflow-x: auto; border-radius: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_agent() -> DealMemoryAgent:
    return DealMemoryAgent(PROJECT_ROOT)


def main() -> None:
    agent = get_agent()
    _initialize_state()
    render_header(agent)
    page = st.session_state.page
    if page == "Deals":
        render_deals(agent)
    elif page == "Insights":
        render_insights(agent)
    else:
        render_memory(agent)


def _initialize_state() -> None:
    st.session_state.setdefault("page", "Deals")
    st.session_state.setdefault("memory_enabled", True)
    st.session_state.setdefault("active_deal_id", None)
    st.session_state.setdefault("analysis", None)
    st.session_state.setdefault("show_new_deal", False)
    st.session_state.setdefault("outcome_saved", None)


def render_header(agent: DealMemoryAgent) -> None:
    brand, navigation, status = st.columns([1.55, 3.8, 1.65], vertical_alignment="center")
    with brand:
        st.markdown('<div class="brand">DEALMEMORY</div><div class="brand-subtitle">Organizational deal intelligence</div>', unsafe_allow_html=True)
    with navigation:
        st.session_state.page = st.radio(
            "Navigation",
            ["Deals", "Insights", "Memory"],
            index=["Deals", "Insights", "Memory"].index(st.session_state.page),
            horizontal=True,
            label_visibility="collapsed",
        )
    with status:
        memory_col, mode_col = st.columns([1.15, 1])
        with memory_col:
            st.session_state.memory_enabled = st.toggle("Memory", value=st.session_state.memory_enabled, help="Use historical deal experiences in recommendations.")
        with mode_col:
            runtime = "LIVE" if (agent.memory.live or agent.knowledge.live or agent.reasoner.live) else "DEMO MODE"
            st.markdown(f'<div class="status-line"><span class="mode">{runtime}</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="product-header-spacer"></div>', unsafe_allow_html=True)


def render_deals(agent: DealMemoryAgent) -> None:
    deals = agent.list_deals()
    if st.session_state.show_new_deal:
        render_new_deal(agent)
        return
    if st.session_state.active_deal_id:
        render_workspace(agent)
        return

    title_col, action_col = st.columns([4, 1], vertical_alignment="bottom")
    with title_col:
        st.markdown('<div class="eyebrow">Revenue workspace</div><h1>Deals</h1><div class="page-intro">A working view of the organization\'s active deal experience. Open any deal to see the evidence behind its next move.</div>', unsafe_allow_html=True)
    with action_col:
        if st.button("+ Analyze New Deal", type="primary", width="stretch"):
            st.session_state.show_new_deal = True
            st.rerun()

    summary = summarize_deals(deals)
    with st.container():
        st.markdown('<div class="metric-strip">', unsafe_allow_html=True)
        metric_columns = st.columns(4)
        _metric(metric_columns[0], "Experiences", summary.total_experiences)
        _metric(metric_columns[1], "Won", summary.successful_outcomes)
        _metric(metric_columns[2], "Lost", summary.failed_outcomes)
        _metric(metric_columns[3], "Stalled", summary.stalled_outcomes)
        st.markdown('</div>', unsafe_allow_html=True)

    search_col, stage_col, industry_col, outcome_col, risk_col = st.columns([2.4, 1.1, 1.2, 1.1, 1])
    with search_col:
        query = st.text_input("Search deals", placeholder="Search deals…", label_visibility="collapsed")
    with stage_col:
        stage = st.selectbox("Stage", ["All", *sorted({deal.stage for deal in deals})], label_visibility="collapsed")
    with industry_col:
        industry = st.selectbox("Industry", ["All", *sorted({deal.industry for deal in deals})], label_visibility="collapsed")
    with outcome_col:
        outcome = st.selectbox("Outcome", ["All", "WON", "LOST", "STALLED", "OPEN"], label_visibility="collapsed")
    with risk_col:
        risk = st.selectbox("Risk", ["All", "High", "Medium", "Low"], label_visibility="collapsed")

    filtered = filter_deals(deals, query, stage, industry, outcome, risk)
    st.markdown(f'<div class="eyebrow" style="margin: 1.15rem 0 0.45rem;">{len(filtered)} deals</div>', unsafe_allow_html=True)
    rows = [
        [
            deal.deal_id,
            deal.company,
            deal.industry,
            deal.stage,
            _currency(deal.deal_size),
            (f"risk-{risk_level(deal).lower()}", risk_level(deal)),
            (f"outcome-{(deal.outcome or 'OPEN').lower()}", deal.outcome or "OPEN"),
            "Outcome captured" if deal.deal_id.startswith("NEW-") else "Historical record",
        ]
        for deal in filtered
    ]
    if rows:
        _render_business_table(["Deal", "Company", "Industry", "Stage", "Value", "Risk", "Outcome", "Last activity"], rows)
        options = {f"{deal.deal_id} · {deal.company}": deal.deal_id for deal in filtered}
        selection_col, open_col = st.columns([3.2, 1], vertical_alignment="bottom")
        with selection_col:
            selected_label = st.selectbox("Open deal intelligence", list(options), label_visibility="collapsed")
        with open_col:
            if st.button("Open intelligence", width="stretch"):
                _open_deal(agent, options[selected_label])
    else:
        st.markdown('<div class="empty-state">No deals match these filters.</div>', unsafe_allow_html=True)


def render_new_deal(agent: DealMemoryAgent) -> None:
    if st.button("← Back to deals"):
        st.session_state.show_new_deal = False
        st.rerun()
    st.markdown('<div class="eyebrow">New analysis</div><h1>Analyze a new deal</h1><div class="page-intro">Give the deal desk enough context to retrieve relevant organizational experience and produce a structured AI brief.</div>', unsafe_allow_html=True)
    with st.form("new-deal-form"):
        first, second = st.columns(2, gap="large")
        with first:
            company = st.text_input("Company", value="Pinecrest Systems")
            industry = st.selectbox("Industry", ["Logistics", "Technology", "Healthcare", "Financial Services", "Manufacturing", "Retail"], index=0)
            deal_size = st.number_input("Deal value ($)", min_value=0, value=240000, step=5000)
            stage = st.selectbox("Stage", ["Discovery", "Evaluation", "Negotiation", "Procurement"], index=1)
        with second:
            competitor = st.text_input("Competitor", value="Competitor X")
            primary_objection = st.selectbox("Primary objection", ["Pricing Objection", "Competitor Displacement", "Stakeholder Change", "Security / Compliance", "Implementation Risk"], index=0)
            stakeholders = st.text_input("Stakeholders", value="VP Operations, Finance Director, Technical evaluator")
            context = st.text_area("Customer context", value="The customer wants measurable savings but is concerned about the annual price and integration effort.", height=126)
        submitted = st.form_submit_button("ANALYZE DEAL", type="primary", width="stretch")
    if submitted:
        deal = Deal.from_dict(
            {
                "deal_id": "NEW-DEAL",
                "company": company,
                "industry": industry,
                "segment": "Mid-market" if deal_size < 150000 else "Enterprise",
                "deal_size": deal_size,
                "stage": stage,
                "stakeholders": stakeholders,
                "objections": [primary_objection],
                "competitor": competitor,
                "customer_context": context,
            }
        )
        with st.spinner("Building deal brief…"):
            st.session_state.analysis = agent.analyze_deal(deal, st.session_state.memory_enabled)
        st.session_state.active_deal_id = "NEW-DEAL"
        st.session_state.show_new_deal = False
        st.session_state.outcome_saved = None
        st.rerun()


def render_workspace(agent: DealMemoryAgent) -> None:
    analysis: Analysis | None = st.session_state.analysis
    if analysis is None:
        active_id = st.session_state.active_deal_id
        deal = next((item for item in agent.list_deals() if item.deal_id == active_id), None)
        if deal is None:
            st.session_state.active_deal_id = None
            st.rerun()
        analysis = agent.analyze_deal(deal, st.session_state.memory_enabled)
        st.session_state.analysis = analysis

    if st.button("← Back to deals"):
        st.session_state.active_deal_id = None
        st.session_state.analysis = None
        st.session_state.outcome_saved = None
        st.rerun()

    deal = analysis.deal
    header_left, header_right = st.columns([3.2, 1], vertical_alignment="bottom")
    with header_left:
        st.markdown(f'<div class="eyebrow">Deal intelligence workspace</div><div class="deal-title">{_safe(deal.company)}</div><div class="deal-meta">{_currency(deal.deal_size)} &nbsp;·&nbsp; {_safe(deal.stage)} &nbsp;·&nbsp; {_safe(deal.industry)} &nbsp;·&nbsp; <span class="memory-status">● Memory {"active" if analysis.memory_enabled else "off"}</span></div>', unsafe_allow_html=True)
    with header_right:
        st.markdown(f'<div style="text-align:right;"><span class="mode">{_safe(analysis.runtime_mode)}</span><br><span class="muted" style="font-size:0.75rem;">{_safe(analysis.retrieval_method)}</span></div>', unsafe_allow_html=True)

    summary_col, brief_col = st.columns([1, 1.45], gap="large")
    with summary_col:
        render_deal_summary(deal)
    with brief_col:
        render_brief(analysis)
    render_evidence(analysis)
    render_outcome_capture(agent, analysis)


def render_deal_summary(deal: Deal) -> None:
    with st.container(border=True):
        st.markdown('<div class="eyebrow">Current situation</div>', unsafe_allow_html=True)
        st.markdown(f'<p style="margin:0.35rem 0 1rem;">{_safe(deal.customer_context)}</p>', unsafe_allow_html=True)
        st.markdown('<h3>Objections</h3>', unsafe_allow_html=True)
        st.markdown("".join(f'<span class="tag tag-accent">{_safe(item)}</span>' for item in deal.objections) or '<span class="muted">None recorded</span>', unsafe_allow_html=True)
        st.markdown('<h3>Stakeholders</h3>', unsafe_allow_html=True)
        st.markdown("".join(f'<span class="tag">{_safe(item)}</span>' for item in deal.stakeholders) or '<span class="muted">None recorded</span>', unsafe_allow_html=True)
        st.markdown('<h3>Competition</h3>', unsafe_allow_html=True)
        st.markdown(f'<p style="margin:0;">{_safe(deal.competitor)}</p>', unsafe_allow_html=True)
        st.markdown('<h3>Risk signals</h3>', unsafe_allow_html=True)
        st.markdown(f'<p class="risk-{risk_level(deal).lower()}" style="margin:0;">{risk_level(deal)} risk</p>', unsafe_allow_html=True)


def render_brief(analysis: Analysis) -> None:
    recommendation = analysis.recommendation
    with st.container(border=True):
        st.markdown('<div class="eyebrow">AI deal brief</div>', unsafe_allow_html=True)
        st.markdown('<div class="brief-label" style="margin-top:0.8rem;">Recommended approach</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="brief-strategy">{_safe(recommendation.recommended_strategy)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="brief-label">Why this matters</div>', unsafe_allow_html=True)
        st.markdown(f'<p class="brief-why">{_safe(recommendation.why)}</p>', unsafe_allow_html=True)
        st.markdown('<div class="brief-label" style="margin-top:1rem;">Recommended next move</div>', unsafe_allow_html=True)
        for index, action in enumerate(recommendation.next_actions[:3], start=1):
            st.markdown(f'<div class="action-row"><span class="action-number">{index:02d}</span><span>{_safe(action)}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-strip" style="margin:1rem 0 0;"><span class="metric-label">Evidence strength</span><br><span class="metric-value">{_safe(recommendation.confidence)}</span><br><span class="muted" style="font-size:0.82rem;">{_safe(recommendation.memory_impact)}</span></div>', unsafe_allow_html=True)

    with st.expander("Why this recommendation?", expanded=False):
        for index, step in enumerate(recommendation.reasoning_steps, start=1):
            st.markdown(f"**{index}.** {_safe(step)}")
        if not recommendation.reasoning_steps:
            st.markdown(_safe(recommendation.why))
    if recommendation.risks:
        st.markdown('<div class="surface-tight" style="margin-top:0.8rem;"><span class="brief-label">Risk signals</span><br>' + "".join(f'<div class="evidence-copy">{_safe(item)}</div>' for item in recommendation.risks) + '</div>', unsafe_allow_html=True)


def render_evidence(analysis: Analysis) -> None:
    recommendation = analysis.recommendation
    st.markdown('<div style="margin-top:1.6rem;"><div class="eyebrow">Evidence</div><h2>What informed this brief</h2><p class="page-intro" style="margin-bottom:0.8rem;">Historical experience and Vault knowledge are shown separately. Relevance is based on the retrieval method displayed above.</p></div>', unsafe_allow_html=True)
    history_col, knowledge_col = st.columns(2, gap="large")
    with history_col:
        with st.container(border=True):
            st.markdown("**Historical experience**")
            if analysis.memory_enabled and recommendation.historical_evidence:
                for evidence in recommendation.historical_evidence:
                    _render_evidence_item(evidence)
            else:
                st.markdown('<p class="muted">Memory is off. No historical experience was used.</p>', unsafe_allow_html=True)
    with knowledge_col:
        with st.container(border=True):
            st.markdown("**Knowledge**")
            for evidence in recommendation.knowledge_evidence:
                _render_evidence_item(evidence)


def _render_evidence_item(evidence: EvidenceItem) -> None:
    outcome = f' <span class="outcome-{evidence.outcome.lower()}">{_safe(evidence.outcome)}</span>' if evidence.outcome else ""
    source = f" · {_safe(evidence.source)}" if evidence.source else ""
    st.markdown(f'<div class="evidence-row"><div class="evidence-title">{_safe(evidence.title)}{outcome}</div><div class="evidence-meta">{_safe(evidence.relevance)}{source}</div><div class="evidence-copy">{_safe(evidence.explanation)}</div></div>', unsafe_allow_html=True)


def render_outcome_capture(agent: DealMemoryAgent, analysis: Analysis) -> None:
    st.markdown('<div style="margin-top:1.6rem;"><div class="eyebrow">Learning loop</div><h2>Record outcome</h2><p class="page-intro" style="margin-bottom:0.8rem;">Capture what happened so this experience can influence future DealMemory recommendations.</p></div>', unsafe_allow_html=True)
    with st.container(border=True):
        with st.form("outcome-form"):
            outcome = st.radio("Outcome", ["WON", "LOST", "STALLED"], horizontal=True, label_visibility="collapsed")
            notes = st.text_area("Outcome notes", placeholder="What happened? What should the organization remember?", height=90)
            saved = st.form_submit_button("Save outcome", type="primary")
        if saved:
            agent.record_outcome(analysis, outcome, notes or None)
            analysis.deal.outcome = outcome
            st.session_state.outcome_saved = outcome
            st.success(f"Outcome recorded: {outcome}. This experience is now available to future recommendations.")
        elif st.session_state.outcome_saved:
            st.success(f"Outcome recorded: {st.session_state.outcome_saved}. This experience is now part of organizational memory.")


def render_insights(agent: DealMemoryAgent) -> None:
    summary = summarize_deals(agent.list_deals())
    st.markdown('<div class="eyebrow">Pattern intelligence</div><h1>Insights</h1><div class="page-intro">Patterns derived from recorded deal outcomes—not decorative analytics. Use these signals to guide deal reviews and coaching.</div>', unsafe_allow_html=True)
    metric_columns = st.columns(4)
    _metric(metric_columns[0], "Experiences", summary.total_experiences)
    _metric(metric_columns[1], "Won", summary.successful_outcomes)
    _metric(metric_columns[2], "Lost", summary.failed_outcomes)
    _metric(metric_columns[3], "Lessons", summary.lessons_generated)
    st.markdown('<div style="margin-top:1.6rem;"><div class="eyebrow">Deal patterns</div><h2>What the team is learning</h2></div>', unsafe_allow_html=True)
    if summary.patterns:
        with st.container(border=True):
            for name, unit, count, detail in summary.patterns:
                st.markdown(f'<div class="insight-row"><span class="insight-name">{_safe(name)}</span> <span class="muted">· {count} {unit}</span><div class="insight-detail">{_safe(detail)}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-state">More outcome history is needed before reliable patterns can be shown.</div>', unsafe_allow_html=True)

    risk_col, distribution_col = st.columns([1.15, 1], gap="large")
    with risk_col:
        st.markdown('<div style="margin-top:1.6rem;"><div class="eyebrow">Emerging risks</div><h2>Signals to watch</h2></div>', unsafe_allow_html=True)
        with st.container(border=True):
            for risk in summary.emerging_risks:
                st.markdown(f'<div class="insight-row">{_safe(risk)}</div>', unsafe_allow_html=True)
    with distribution_col:
        st.markdown('<div style="margin-top:1.6rem;"><div class="eyebrow">Portfolio shape</div><h2>Outcome distribution</h2></div>', unsafe_allow_html=True)
        with st.container(border=True):
            distribution_rows = [
                [(f"outcome-{key.lower()}", key), value]
                for key, value in summary.outcome_distribution.items()
            ]
            _render_business_table(["Outcome", "Deals"], distribution_rows)
            st.caption("Derived from the current DealMemory dataset.")


def render_memory(agent: DealMemoryAgent) -> None:
    deals = agent.list_deals()
    summary = summarize_deals(deals)
    st.markdown('<div class="eyebrow">Experience layer</div><h1>Organizational memory</h1><div class="page-intro">DealMemory is the record of what the organization experienced: the objections, tactics, outcomes, and lessons that should travel to the next deal.</div>', unsafe_allow_html=True)
    metric_columns = st.columns(4)
    _metric(metric_columns[0], "Experiences remembered", summary.total_experiences)
    _metric(metric_columns[1], "Successful patterns", summary.successful_outcomes)
    _metric(metric_columns[2], "Failed patterns", summary.failed_outcomes)
    _metric(metric_columns[3], "Lessons generated", summary.lessons_generated)

    st.markdown('<div style="margin-top:1.6rem;"><div class="eyebrow">Accumulated experience</div><h2>Patterns the organization can reuse</h2></div>', unsafe_allow_html=True)
    for name, unit, count, detail in summarize_deals(deals).patterns:
        related = [deal for deal in deals if _pattern_matches(deal, name)]
        successful_tactic = _successful_tactic(related)
        with st.container(border=True):
            st.markdown(f'<div class="brief-label">{_safe(name)}</div><div class="deal-title" style="font-size:1.15rem;">Observed across {count} {unit}</div><p class="muted">{_safe(detail)}</p><div class="evidence-meta">Successful tactic</div><div style="font-weight:700; margin-top:0.2rem;">{_safe(successful_tactic)}</div><div class="evidence-meta" style="margin-top:0.45rem;">Confidence: {"High" if count >= 3 else "Moderate"}</div>', unsafe_allow_html=True)

    st.markdown('<div style="margin-top:1.6rem;"><div class="eyebrow">Memory ledger</div><h2>Recent experiences</h2></div>', unsafe_allow_html=True)
    ledger = [
        [deal.deal_id, (f"outcome-{(deal.outcome or 'OPEN').lower()}", deal.outcome or "OPEN"), ", ".join(deal.objections), deal.lessons_learned]
        for deal in deals
    ]
    _render_business_table(["Deal", "Outcome", "Objections", "Lesson"], ledger)


def _open_deal(agent: DealMemoryAgent, deal_id: str) -> None:
    deal = next((item for item in agent.list_deals() if item.deal_id == deal_id), None)
    if deal is None:
        return
    st.session_state.active_deal_id = deal_id
    st.session_state.analysis = agent.analyze_deal(deal, st.session_state.memory_enabled)
    st.session_state.outcome_saved = None
    st.rerun()


def _metric(column, label: str, value: int) -> None:
    with column:
        st.markdown(f'<div class="metric-label">{_safe(label)}</div><div class="metric-value">{value}</div>', unsafe_allow_html=True)


def _render_business_table(headers: list[str], rows: list[list[object]]) -> None:
    header_html = "".join(f"<th scope=\"col\">{_safe(header)}</th>" for header in headers)
    body_html = []
    for row in rows:
        cells = []
        for value in row:
            if isinstance(value, tuple) and len(value) == 2:
                class_name, text = value
                content = f'<span class="{_safe(class_name)}">{_safe(text)}</span>'
            else:
                content = _safe(value)
            cells.append(f"<td>{content}</td>")
        body_html.append(f"<tr>{''.join(cells)}</tr>")
    st.markdown(
        f'<div class="table-scroll"><table class="business-table"><thead><tr>{header_html}</tr></thead><tbody>{"".join(body_html)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def _pattern_matches(deal: Deal, pattern: str) -> bool:
    text = " ".join(deal.objections + deal.successful_tactics + deal.failed_tactics + [deal.sales_response]).lower()
    terms = {
        "Pricing objections": ["pricing"],
        "ROI-first strategy": ["roi", "payback", "labor savings"],
        "Early discounting": ["discount"],
        "Technical validation": ["technical", "integration", "security", "sandbox"],
    }
    return any(term in text for term in terms.get(pattern, []))


def _successful_tactic(deals: list[Deal]) -> str:
    for deal in deals:
        if deal.outcome == "WON" and deal.successful_tactics:
            return deal.successful_tactics[0]
    return "No successful tactic recorded yet"


def _currency(value: int) -> str:
    return f"${value:,.0f}"


def _safe(value: object) -> str:
    return html.escape(str(value))


if __name__ == "__main__":
    main()
