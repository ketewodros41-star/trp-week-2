# Automaton Auditor

A production-grade autonomous auditing system ("Digital Courtroom") built with LangGraph. This system evaluates AI-generated code repositories and PDF reports using forensic rigor and dialectical reasoning.

## Architecture

The system implements a Hierarchical State Graph:
1. **Detective Layer (Parallel):** Forensic agents (`RepoInvestigator`, `DocAnalyst`) collect evidence from Git history, AST parsing, and PDF content.
2. **Judicial Layer (Parallel):** Distinct personas (`Prosecutor`, `Defense`, `Tech Lead`) analyze evidence for each rubric criterion.
3. **Supreme Court:** A `ChiefJusticeNode` applies deterministic rules to synthesize a final verdict and generates a Markdown report.

## Setup

1. **Install Dependencies:**
   Ensure you have `uv` installed.
   ```powershell
   uv sync
   ```

2. **Environment Variables:**
   Copy `.env.example` to `.env` and fill in your API keys.
   ```powershell
   cp .env.example .env
   ```
   Required keys: `OPENAI_API_KEY`, `LANGCHAIN_API_KEY`.

3. **Running the Auditor:**
   ```powershell
   uv run python src/graph.py
   ```

## Project Structure

- `src/state.py`: Core state and Pydantic models.
- `src/graph.py`: LangGraph orchestration.
- `src/tools/`: Forensic analysis tools.
- `src/nodes/`: Agent node implementations.
- `rubric.json`: The "Constitution" of the auditor.
- `audit/`: Generated audit reports.

## Features

- **AST Parsing:** Verifies code structure (StateGraph, Pydantic) without regex.
- **Git Forensics:** Analyzes commit history for atomic progression.
- **Dialectical Synthesis:** Three parallel judges provide conflicting views resolved by hardcoded rules.
- **Observability:** Built-in LangSmith tracing.
