# DealMemory

DealMemory is an AI sales intelligence prototype that turns previous deal outcomes into evidence for the next deal decision.

## The Problem

Sales teams repeatedly meet the same pricing, competition, security, and implementation objections. A general-purpose AI assistant can give advice, but it does not naturally remember what the organization tried or what happened next.

## The Insight

The most valuable sales knowledge is not only market knowledge. It is organizational experience:

```text
Experience → Memory → Retrieval → Reasoning → Recommendation → Outcome → Learning
```

DealMemory keeps experience, Vault knowledge, and model reasoning distinct so a recommendation can be inspected rather than trusted blindly.

## How DealMemory Works

1. A seller opens the Deals workspace or analyzes a new deal.
2. DealMemory recalls comparable historical experiences when Memory is ON.
3. Vybe Intelligence Vault supplies supporting sales and technical knowledge.
4. The reasoning layer produces a structured AI Deal Brief.
5. The seller records `WON`, `LOST`, or `STALLED` with an outcome note.
6. The new experience becomes available to future retrieval.

## Architecture

- **DealMemory / Hindsight:** what happened — deal context, outcome, tactics, and lessons.
- **Vybe Intelligence Vault:** what the organization can use as supporting knowledge.
- **Reasoning:** how current context and evidence become a strategy, risks, and next actions.
- **Demo fallback:** local JSON memory and deterministic reasoning keep the selection demo runnable without credentials or internet.

## Product Walkthrough

The app has three focused views:

- **Deals:** filter the deal history, open a deal intelligence workspace, or use `+ Analyze New Deal`.
- **Insights:** see only patterns and risks derived from the current dataset.
- **Memory:** browse accumulated experiences and reusable organizational patterns.

The deal workspace separates the current situation, AI Deal Brief, evidence, explanation, and outcome capture. It does not expose raw JSON or MCP messages.

## Memory ON vs OFF

Memory is a small workspace control, not a separate application mode.

- **ON:** historical experiences change the strategy and appear in the Evidence section.
- **OFF:** the recommendation uses the current deal and general knowledge only, and explicitly says no historical memory was used.

The retrieval label is honest: Demo Mode uses a deterministic structured field match across industry, segment, stage, objection, stakeholder, competitor, and deal-size signals. It does not claim semantic similarity.

## Demo Scenario

- **D-097:** pricing objection, immediate discounting, `LOST`.
- **D-104:** similar pricing objection, quantified ROI and technical validation, `WON`.
- **New deal:** Memory retrieves both experiences and recommends an ROI-first approach supported by technical proof.
- **Outcome:** record `WON`; the new experience is written to local memory and appears in later retrieval.

## Technology

- Python 3.10+
- Streamlit
- Local JSON demo data
- Optional Hindsight Python client
- Optional Vybe MCP client
- Optional Groq reasoning provider

The prototype intentionally excludes CRM integrations, authentication, billing, graph databases, vector databases, and deployment infrastructure.

## Running Locally

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`. No environment variables are required for Demo Mode.

## Live Integrations

Install the optional provider dependencies:

```bash
pip install -r requirements-live.txt
```

Then copy `.env.example` to `.env` and configure only the providers you want:

- `GROQ_API_KEY` and `GROQ_MODEL` enable live reasoning.
- `HINDSIGHT_API_KEY`, `HINDSIGHT_BASE_URL`, and `HINDSIGHT_BANK_ID` enable Hindsight retain/recall/reflect.
- `VYBE_MCP_COMMAND`, `VYBE_MCP_ARGS`, and `VYBE_MCP_CWD` enable the Vault MCP `vault_search` tool.

Any unavailable live provider falls back locally. The UI shows `DEMO MODE` or `LIVE` without making configuration the centerpiece.

## Project Structure

```text
app.py                  Streamlit product shell and views
agent/agent.py          Deal analysis and outcome pipeline
agent/analytics.py      Dataset validation and derived insights
agent/memory.py         Local/Hindsight retain, recall, reflect
agent/vybe.py           Local/Vybe MCP knowledge retrieval
agent/llm.py            Demo/Groq structured reasoning
agent/models.py         Typed deal, evidence, and analysis models
agent/schemas.py        Recommendation output validation
data/deals.json         Synthetic historical deal experiences
data/knowledge.json     Local Vault knowledge fallback
demo/demo-script.md     Two-to-three minute walkthrough
tests/test_agent.py     Core behavior and learning-loop tests
```

## Tests

```bash
python -m pytest -q
```

The suite covers application import, dataset validation, parsing, field-match retrieval, structured recommendation evidence, Memory OFF behavior, outcome persistence, and the learning loop.

## Demo Script

See [demo/demo-script.md](demo/demo-script.md) for the selection-round walkthrough. The intended closing line is:

> “The system does not just retrieve information. It accumulates experience.”
