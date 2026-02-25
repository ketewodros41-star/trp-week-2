# Automaton Auditor 🏛️

A production-grade autonomous auditing system — a **"Digital Courtroom"** — built with LangGraph. The system evaluates GitHub repositories and PDF architectural reports using forensic rigor, dialectical reasoning, and deterministic judgment.

## Architecture

The system implements a **Hierarchical State Graph** with three layers:

```
START
  ├── RepoInvestigator ──┐
  ├── DocAnalyst ─────────┼──> EvidenceAggregator
  └── VisionInspector ───┘         │
                          ┌─────────┴──────────┐
                          ├── Prosecutor ───────┐
                          ├── Defense ──────────┼──> ChiefJustice ──> END
                          └── TechLead ─────────┘
```

1. **Detective Layer (Parallel Fan-Out):** Forensic agents collect evidence concurrently from Git history (AST), PDF content, and visual diagrams.
2. **Evidence Aggregator (Fan-In):** Synchronizes all evidence and performs cross-reference validation between report claims and actual repo files.
3. **Judicial Layer (Parallel Fan-Out):** Three distinct personas (`Prosecutor`, `Defense`, `Tech Lead`) analyze all evidence in parallel for each rubric criterion.
4. **Chief Justice (Fan-In + Synthesis):** Applies deterministic Python rules to resolve conflicts and generates a structured Markdown audit report.

## Setup

### Prerequisites
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) package manager

### 1. Install Dependencies
```powershell
uv sync
```

### 2. Configure Environment Variables
```powershell
Copy-Item .env.example .env
# Then edit .env and fill in your API keys
```

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | Powers the Prosecutor, Defense, and Tech Lead LLMs |
| `LANGCHAIN_API_KEY` | ✅ | LangSmith tracing and observability |
| `GOOGLE_API_KEY` | Optional | For Gemini-powered VisionInspector |
| `GITHUB_TOKEN` | Optional | For cloning private repositories |
| `LANGCHAIN_TRACING_V2` | Recommended | Set to `true` to enable LangSmith traces |

### 3. Run the Auditor

**Against any target repository:**
```powershell
uv run python src/graph.py \
  --repo-url https://github.com/<user>/<repo> \
  --pdf-path path/to/report.pdf
```

**With custom output directory:**
```powershell
uv run python src/graph.py \
  --repo-url https://github.com/<user>/<repo> \
  --pdf-path path/to/report.pdf \
  --output-dir audit/report_onpeer_generated
```

**Full options:**
```
--repo-url     GitHub repository URL to audit (required)
--pdf-path     Path to the architectural PDF report (required)
--rubric       Path to rubric JSON file (default: rubric.json)
--output-dir   Output directory for Markdown report (default: audit/report_onself_generated)
```

## Project Structure

```
trp-audit-challenge/
├── src/
│   ├── state.py                # Pydantic/TypedDict state definitions with reducers
│   ├── graph.py                # LangGraph orchestration (CLI entry point)
│   ├── nodes/
│   │   ├── detectives.py       # RepoInvestigator, DocAnalyst, VisionInspector
│   │   ├── judges.py           # Prosecutor, Defense, TechLead (structured output)
│   │   └── justice.py          # ChiefJustice with deterministic synthesis rules
│   └── tools/
│       ├── repo_tools.py       # Sandboxed git clone, git log, AST analysis
│       ├── doc_tools.py        # PDF ingestion (docling) + RAG-lite query
│       └── vision_tools.py     # Image extraction stub (optional execution)
├── audit/
│   ├── report_onself_generated/   # Self-audit output
│   ├── report_onpeer_generated/   # Peer-audit output
│   └── report_bypeer_received/    # Received peer report
├── reports/
│   └── final_report.pdf           # Architectural PDF report
├── rubric.json                    # The "Constitution" — machine-readable rubric
├── pyproject.toml                 # uv-managed dependencies
├── Dockerfile                     # Containerized runtime
└── .env.example                   # Environment variable template
```

## Key Features

| Feature | Implementation |
|---|---|
| **AST Forensics** | `src/tools/repo_tools.py` — verifies StateGraph, Pydantic, structured output without regex |
| **Sandboxed Cloning** | `tempfile.mkdtemp()` — untrusted repos never touch the live workspace |
| **Dialect Synthesis** | Three parallel judges with opposing philosophies; deterministic conflict resolution |
| **Observability** | LangSmith tracing enabled via `LANGCHAIN_TRACING_V2=true` |
| **Structured Output** | All Judges use `.with_structured_output(JudicialOpinion)` — no freeform parsing |

## LangSmith Trace

> **Trace link:** _(Run the agent and paste your LangSmith trace URL here)_

## Docker Runtime (Optional)

```powershell
docker build -t automaton-auditor .
docker run --env-file .env automaton-auditor \
  python src/graph.py \
  --repo-url https://github.com/<user>/<repo> \
  --pdf-path /app/reports/final_report.pdf
```
