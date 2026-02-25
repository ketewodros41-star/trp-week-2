import os
import logging
from src.state import AgentState, Evidence
from src.tools.repo_tools import RepoInvestigator
from src.tools.doc_tools import DocAnalyst
from src.tools.vision_tools import VisionInspector

logger = logging.getLogger(__name__)


def context_builder_node(state: AgentState) -> dict:
    """Pre-checks artifact availability and builds orchestration context."""
    available = []
    
    # Check Repo
    if state.get("repo_url") and state["repo_url"].startswith("http"):
        available.append("repo")
    
    # Check PDF
    pdf_path = state.get("pdf_path")
    if pdf_path and os.path.exists(pdf_path):
        available.append("pdf")
    
    logger.info(f"Orchestration Context: Available artifacts = {available}")
    return {"available_artifacts": available}


def repo_investigator_node(state: AgentState) -> dict:
    """Node for forensic analysis of the repository."""
    repo_url = state["repo_url"]
    if not repo_url:
        return {"evidences": {}}
        
    inv = RepoInvestigator()

    try:
        repo_path = inv.clone_repo(repo_url)
    except Exception as e:
        logger.error(f"RepoInvestigator failed to clone: {e}")
        return {"evidences": {"safe_tool_engineering": [Evidence(
            goal="Clone repository safely",
            found=False,
            location=repo_url,
            rationale=f"Clone failed: {str(e)}",
            confidence=1.0
        )]}}

    try:
        git_log = inv.get_git_log(repo_path)
        ast_data = inv.analyze_ast(repo_path)

        evidences = {}

        # -------------------------------------------------------------------
        # Evidence: Git Forensic Analysis
        # -------------------------------------------------------------------
        commit_count = len(git_log)
        messages = [c["message"] for c in git_log]
        has_progression = (
            commit_count > 3
            and any(kw in " ".join(messages).lower() for kw in ["setup", "init", "environment"])
            and any(kw in " ".join(messages).lower() for kw in ["tool", "engineer", "detective"])
        )
        evidences["git_forensic_analysis"] = [Evidence(
            goal="Analyze commit history for atomic progression",
            found=commit_count > 3,
            content="\n".join([f"{c['hash']} {c['timestamp']}: {c['message']}" for c in git_log]),
            location="git log --oneline --reverse",
            rationale=f"Found {commit_count} commits. Progression pattern detected: {has_progression}.",
            confidence=1.0,
        )]

        # -------------------------------------------------------------------
        # Evidence: State Management Rigor
        # -------------------------------------------------------------------
        state_defs = ast_data["state_definitions"]
        evidences["state_management_rigor"] = [Evidence(
            goal="Verify Pydantic/TypedDict AgentState with reducers",
            found=len(state_defs) > 0,
            content="\n".join(state_defs),
            location="src/state.py",
            rationale=f"Found {len(state_defs)} typed class definitions (BaseModel/TypedDict).",
            confidence=0.95,
        )]

        # -------------------------------------------------------------------
        # Evidence: Graph Orchestration
        # -------------------------------------------------------------------
        graph_defs = ast_data["graph_definitions"]
        parallel_edges = ast_data["parallel_edges"]
        evidences["graph_orchestration"] = [Evidence(
            goal="Verify LangGraph parallel fan-out/fan-in architecture",
            found=len(graph_defs) > 0,
            content="\n".join(graph_defs + parallel_edges),
            location="src/graph.py",
            rationale=(
                f"StateGraph instantiated: {len(graph_defs) > 0}. "
                f"Edge calls found: {len(parallel_edges)}. "
                "Parallelism implied by multiple edges from START."
            ),
            confidence=0.9,
        )]

        # -------------------------------------------------------------------
        # Evidence: Safe Tool Engineering
        # -------------------------------------------------------------------
        safe_tool_evidence = _check_safe_tool_engineering(repo_path)
        evidences["safe_tool_engineering"] = [safe_tool_evidence]

        # -------------------------------------------------------------------
        # Evidence: Structured Output Enforcement
        # -------------------------------------------------------------------
        structured_output_calls = ast_data.get("structured_output_calls", [])
        evidences["structured_output_enforcement"] = [Evidence(
            goal="Verify Judges use .with_structured_output() or .bind_tools()",
            found=len(structured_output_calls) > 0,
            content="\n".join(structured_output_calls),
            location="src/nodes/judges.py",
            rationale=f"Found {len(structured_output_calls)} structured output call(s) via AST scan.",
            confidence=0.9,
        )]

        return {"evidences": evidences}
    finally:
        inv.cleanup(repo_path)


def _check_safe_tool_engineering(repo_path: str) -> Evidence:
    """Scan repo for tempfile usage vs. raw os.system calls."""
    import ast as ast_mod

    tools_dir = os.path.join(repo_path, "src", "tools")
    has_tempfile = False
    has_os_system = False
    has_subprocess = False
    locations_found = []

    if not os.path.exists(tools_dir):
        return Evidence(
            goal="Verify sandboxed git clone in src/tools/",
            found=False,
            content=None,
            location="src/tools/ (not found)",
            rationale="src/tools/ directory does not exist in the repository.",
            confidence=1.0,
        )

    for fname in os.listdir(tools_dir):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(tools_dir, fname)
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            source = f.read()
        try:
            tree = ast_mod.parse(source)
        except SyntaxError:
            continue
        for node in ast_mod.walk(tree):
            if isinstance(node, ast_mod.Call):
                func = node.func
                if isinstance(func, ast_mod.Attribute) and func.attr == "system":
                    has_os_system = True
                if isinstance(func, ast_mod.Attribute) and func.attr in ("mkdtemp", "TemporaryDirectory"):
                    has_tempfile = True
                    locations_found.append(f"{fname}: {func.attr} at line {node.lineno}")
                if isinstance(func, ast_mod.Attribute) and func.attr == "run":
                    has_subprocess = True
                    locations_found.append(f"{fname}: subprocess.run at line {node.lineno}")

    is_safe = has_tempfile and not has_os_system
    return Evidence(
        goal="Verify sandboxed git clone using tempfile, no raw os.system",
        found=is_safe,
        content="\n".join(locations_found) if locations_found else "No sandboxed cloning detected.",
        location="src/tools/repo_tools.py",
        rationale=(
            f"tempfile detected: {has_tempfile}, "
            f"subprocess.run detected: {has_subprocess}, "
            f"raw os.system detected: {has_os_system}. "
            f"{'SAFE: uses sandboxed temp dir.' if is_safe else 'UNSAFE: os.system or no sandboxing.'}"
        ),
        confidence=0.95,
    )


def doc_analyst_node(state: AgentState) -> dict:
    """Node for forensic analysis of the PDF report."""
    pdf_path = state["pdf_path"]
    if not pdf_path or not os.path.exists(pdf_path):
         return {"evidences": {}}

    analyst = DocAnalyst()
    try:
        doc_text = analyst.ingest_pdf(pdf_path)
    except Exception as e:
        logger.error(f"DocAnalyst failed to ingest PDF: {e}")
        return {"evidences": {"theoretical_depth": [Evidence(
            goal="Analyze PDF report",
            found=False,
            location=pdf_path,
            rationale=f"Ingestion failed: {str(e)}",
            confidence=1.0
        )]}}

    keywords = ["Dialectical Synthesis", "Fan-In / Fan-Out", "Metacognition", "State Synchronization"]
    concept_data = analyst.query_concepts(doc_text, keywords)
    extracted_paths = analyst.extract_file_paths(doc_text)

    keywords_found_in_context = []
    keywords_only_buzzword = []
    for kw, ctx in concept_data.items():
        if "Term not found" in ctx:
            keywords_only_buzzword.append(kw)
        elif len(ctx.split()) > 20:
            keywords_found_in_context.append(kw)
        else:
            keywords_only_buzzword.append(kw)

    theoretical_evidence = Evidence(
        goal="Verify deep understanding of architectural concepts (not just buzzwords)",
        found=len(keywords_found_in_context) >= 2,
        content=str(concept_data),
        location=pdf_path,
        rationale=(
            f"Found {len(keywords_found_in_context)} keywords with substantive context: {keywords_found_in_context}. "
            f"Buzzword-only drops: {keywords_only_buzzword}."
        ),
        confidence=0.85,
    )

    accuracy_evidence = Evidence(
        goal="Extract file paths from report for cross-referencing with repo",
        found=len(extracted_paths) > 0,
        content="\n".join(extracted_paths),
        location=pdf_path,
        rationale=f"Extracted {len(extracted_paths)} potential file paths from the PDF for cross-reference.",
        confidence=0.75,
    )

    return {"evidences": {
        "theoretical_depth": [theoretical_evidence],
        "report_accuracy_raw_paths": [accuracy_evidence],
    }}


def vision_inspector_node(state: AgentState) -> dict:
    """Node for forensic analysis of diagrams in the PDF."""
    pdf_path = state["pdf_path"]
    if not pdf_path or not os.path.exists(pdf_path):
        return {"evidences": {}}

    viz = VisionInspector()
    images = viz.extract_images_from_pdf(pdf_path)

    evidences = {
        "swarm_visual": [Evidence(
            goal="Analyze architectural diagrams for fan-out/fan-in parallelism",
            found=len(images) > 0,
            content=(
                f"Found {len(images)} image(s). "
                + (viz.analyze_diagram(images[0]) if images else "No images to analyze.")
            ),
            location=pdf_path,
            rationale=(
                "VisionInspector extracted images and classified diagram type. "
                "Execution of multimodal model is optional per rubric."
            ),
            confidence=0.5 if not images else 0.7,
        )]
    }

    return {"evidences": evidences}


def evidence_aggregator_node(state: AgentState) -> dict:
    """
    Synchronization node (Fan-In): collects all Detective evidence and performs
    cross-referencing between repo findings and document claims.
    """
    evidences = state.get("evidences", {})
    available = state.get("available_artifacts", [])
    
    logger.info(f"Aggregating evidence. Available artifacts recorded: {available}")
    
    if not available:
        logger.warning("No artifacts were available for detection. Aggregating empty set.")
        return {"evidences": {"report_accuracy": [Evidence(
            goal="Collect evidence",
            found=False,
            location="N/A",
            rationale="No target artifacts provided or available.",
            confidence=1.0
        )]}}

    # Cross-reference: report claims vs. actual repo files
    raw_paths_evidence = evidences.get("report_accuracy_raw_paths", [])
    if raw_paths_evidence and raw_paths_evidence[0].found:
        claimed_paths = raw_paths_evidence[0].content.split("\n") if raw_paths_evidence[0].content else []
        actual_state_evidence = evidences.get("state_management_rigor", [])
        actual_graph_evidence = evidences.get("graph_orchestration", [])
        known_real_paths = set()
        for ev in actual_state_evidence + actual_graph_evidence:
            if ev.content:
                for line in ev.content.split("\n"):
                    if "/" in line or ".py" in line:
                        known_real_paths.add(line.split(":")[0].strip())

        verified = [p for p in claimed_paths if any(r in p or p in r for r in known_real_paths)]
        hallucinated = [p for p in claimed_paths if p not in verified]

        cross_ref = Evidence(
            goal="Cross-reference report file claims against actual repo contents",
            found=len(hallucinated) == 0,
            content=(
                f"Verified paths ({len(verified)}): {verified}\n"
                f"Hallucinated paths ({len(hallucinated)}): {hallucinated}"
            ),
            location="cross-reference: PDF vs Repo",
            rationale=(
                f"{len(verified)} claimed paths verified. "
                f"{len(hallucinated)} paths appear in report but not in repo (potential hallucinations)."
            ),
            confidence=0.8,
        )
        return {"evidences": {"report_accuracy": [cross_ref]}}

    return {}
