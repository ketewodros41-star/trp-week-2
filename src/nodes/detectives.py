from src.state import AgentState, Evidence
from src.tools.repo_tools import RepoInvestigator
from src.tools.doc_tools import DocAnalyst
import os

def repo_investigator_node(state: AgentState) -> dict:
    """Node for forensic analysis of the repository."""
    repo_url = state["repo_url"]
    inv = RepoInvestigator()
    
    repo_path = inv.clone_repo(repo_url)
    try:
        git_log = inv.get_git_log(repo_path)
        ast_data = inv.analyze_ast(repo_path)
        
        evidences = {}
        
        # Git Forensic Analysis
        evidences["git_forensic_analysis"] = [Evidence(
            goal="Analyze commit history progression",
            found=True,
            content=str(git_log),
            location="git log",
            rationale="Extracted full git history using GitPython.",
            confidence=1.0
        )]
        
        # State Management Rigor
        evidences["state_management_rigor"] = [Evidence(
            goal="Verify Pydantic/TypedDict state",
            found=len(ast_data["state_definitions"]) > 0,
            content="\n".join(ast_data["state_definitions"]),
            location="src/",
            rationale="Scanned repository for state definitions using AST.",
            confidence=0.9
        )]
        
        # Graph Orchestration
        evidences["graph_orchestration"] = [Evidence(
            goal="Verify LangGraph architecture",
            found=len(ast_data["graph_definitions"]) > 0,
            content="\n".join(ast_data["graph_definitions"] + ast_data["parallel_edges"]),
            location="src/graph.py",
            rationale="Analyzed StateGraph instantiation and edge wiring using AST.",
            confidence=0.9
        )]

        return {"evidences": evidences}
    finally:
        inv.cleanup(repo_path)

def doc_analyst_node(state: AgentState) -> dict:
    """Node for forensic analysis of the PDF report."""
    pdf_path = state["pdf_path"]
    analyst = DocAnalyst()
    
    if not os.path.exists(pdf_path):
        return {"evidences": {"theoretical_depth": [Evidence(
            goal="Analyze theoretical depth in PDF",
            found=False,
            location=pdf_path,
            rationale="PDF file not found at specified path.",
            confidence=1.0
        )]}}

    doc_text = analyst.ingest_pdf(pdf_path)
    keywords = ["Dialectical Synthesis", "Fan-In / Fan-Out", "Metacognition", "State Synchronization"]
    concept_data = analyst.query_concepts(doc_text, keywords)
    extracted_paths = analyst.extract_file_paths(doc_text)
    
    evidences = {}
    
    # Theoretical Depth
    evidences["theoretical_depth"] = [Evidence(
        goal="Verify deep understanding of concepts",
        found=any("Term not found" not in v for v in concept_data.values()),
        content=str(concept_data),
        location=pdf_path,
        rationale="Performed RAG-lite keyword search on the PDF.",
        confidence=0.8
    )]
    
    # Host Analysis Accuracy (Cross-reference prep)
    evidences["report_accuracy_extraction"] = [Evidence(
        goal="Extract file paths from report for cross-referencing",
        found=len(extracted_paths) > 0,
        content=", ".join(extracted_paths),
        location=pdf_path,
        rationale="Extracted file paths mentioned in documentation.",
        confidence=0.7
    )]
    
    return {"evidences": evidences}

def evidence_aggregator_node(state: AgentState) -> dict:
    """Sync node (Fan-In) that technically just passes state, but ensures synchronization."""
    # In LangGraph, fan-in happens automatically when multiple branches lead to one node.
    # This node can also perform cross-referencing between repo and doc evidence.
    return {}
