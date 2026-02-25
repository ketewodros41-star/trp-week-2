from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.nodes.detectives import (
    repo_investigator_node,
    doc_analyst_node,
    vision_inspector_node,
    evidence_aggregator_node,
)
from src.nodes.judges import prosecutor_node, defense_node, tech_lead_node
from src.nodes.justice import chief_justice_node
import json
import argparse
import os
from dotenv import load_dotenv


def create_graph():
    workflow = StateGraph(AgentState)

    # --- Add all nodes ---
    workflow.add_node("repo_investigator", repo_investigator_node)
    workflow.add_node("doc_analyst", doc_analyst_node)
    workflow.add_node("vision_inspector", vision_inspector_node)
    workflow.add_node("evidence_aggregator", evidence_aggregator_node)

    workflow.add_node("prosecutor", prosecutor_node)
    workflow.add_node("defense", defense_node)
    workflow.add_node("tech_lead", tech_lead_node)

    workflow.add_node("chief_justice", chief_justice_node)

    # --- Layer 1: Detective Fan-Out (Parallel) ---
    workflow.add_edge(START, "repo_investigator")
    workflow.add_edge(START, "doc_analyst")
    workflow.add_edge(START, "vision_inspector")

    # --- Fan-In: All detectives converge on aggregator ---
    workflow.add_edge("repo_investigator", "evidence_aggregator")
    workflow.add_edge("doc_analyst", "evidence_aggregator")
    workflow.add_edge("vision_inspector", "evidence_aggregator")

    # --- Layer 2: Judicial Fan-Out (Parallel) ---
    workflow.add_edge("evidence_aggregator", "prosecutor")
    workflow.add_edge("evidence_aggregator", "defense")
    workflow.add_edge("evidence_aggregator", "tech_lead")

    # --- Fan-In: All judges converge on Chief Justice ---
    workflow.add_edge("prosecutor", "chief_justice")
    workflow.add_edge("defense", "chief_justice")
    workflow.add_edge("tech_lead", "chief_justice")

    workflow.add_edge("chief_justice", END)

    return workflow.compile()


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Automaton Auditor: Run the Digital Courtroom swarm against a target repo."
    )
    parser.add_argument(
        "--repo-url",
        required=True,
        help="GitHub repository URL to audit (e.g. https://github.com/user/repo)",
    )
    parser.add_argument(
        "--pdf-path",
        required=True,
        help="Path to the architectural PDF report to audit",
    )
    parser.add_argument(
        "--rubric",
        default="rubric.json",
        help="Path to rubric JSON file (default: rubric.json)",
    )
    parser.add_argument(
        "--output-dir",
        default="audit/report_onself_generated",
        help="Output directory for the generated Markdown report",
    )
    args = parser.parse_args()

    with open(args.rubric, "r") as f:
        rubric = json.load(f)

    app = create_graph()

    initial_state = {
        "repo_url": args.repo_url,
        "pdf_path": args.pdf_path,
        "rubric_dimensions": rubric["dimensions"],
        "evidences": {},
        "opinions": [],
        "final_report": None,
    }

    # Override the output directory used by ChiefJustice
    os.environ["AUDIT_OUTPUT_DIR"] = args.output_dir

    print(f"[Auditor] Starting audit of: {args.repo_url}")
    print(f"[Auditor] PDF Report: {args.pdf_path}")
    print(f"[Auditor] Output: {args.output_dir}/report.md")
    print("[Auditor] LangSmith tracing:", os.getenv("LANGCHAIN_TRACING_V2", "false"))

    result = app.invoke(initial_state)
    print(f"\n[Auditor] ✅ Audit complete. Overall score: {result['final_report'].overall_score:.2f}/5.00")
    print(f"[Auditor] Report saved to: {args.output_dir}/report.md")


if __name__ == "__main__":
    main()
