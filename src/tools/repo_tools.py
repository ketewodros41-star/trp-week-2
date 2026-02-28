import os
import tempfile
import ast
import subprocess
from typing import List, Dict, Optional
from collections import defaultdict
from git import Repo


class RepoInvestigator:
    """Forensic tools for analyzing GitHub repositories."""

    @staticmethod
    def clone_repo(repo_url: str) -> str:
        """Clones a repository into a sandboxed temporary directory."""
        temp_dir = tempfile.mkdtemp()
        try:
            Repo.clone_from(repo_url, temp_dir)
            return temp_dir
        except Exception as e:
            # Clean up if clone fails
            import shutil
            shutil.rmtree(temp_dir)
            raise RuntimeError(f"Failed to clone repository {repo_url}: {e}")

    @staticmethod
    def get_git_log(repo_path: str) -> List[Dict[str, str]]:
        """Extracts git log --oneline --reverse with full metadata."""
        repo = Repo(repo_path)
        commits = list(repo.iter_commits(reverse=True))
        return [
            {
                "hash": commit.hexsha[:7],
                "message": commit.message.strip(),
                "timestamp": commit.committed_datetime.isoformat(),
                "author": commit.author.name
            }
            for commit in commits
        ]

    @staticmethod
    def analyze_git_progression(git_log: List[Dict[str, str]]) -> Dict[str, any]:
        """
        Analyzes commit history for progression patterns vs. bulk uploads.
        Detects: phase-based development, commit cadence, and topical clustering.
        """
        if not git_log:
            return {"is_progression": False, "pattern": "empty", "details": "No commits found."}

        messages = [c["message"].lower() for c in git_log]
        timestamps = [c["timestamp"] for c in git_log]
        commit_count = len(git_log)

        # Phase detection: look for infrastructure → implementation → refinement
        phase_keywords = {
            "setup": ["setup", "init", "initial", "scaffold", "create", "install", "configure", "environment", "boilerplate"],
            "implementation": ["implement", "add", "feature", "node", "detective", "judge", "tool", "agent", "graph", "state"],
            "refinement": ["fix", "refactor", "improve", "update", "polish", "test", "document", "readme", "clean"],
        }

        phases_found = {}
        for phase, keywords in phase_keywords.items():
            matching_commits = [
                i for i, msg in enumerate(messages)
                if any(kw in msg for kw in keywords)
            ]
            if matching_commits:
                phases_found[phase] = {
                    "first_commit_index": min(matching_commits),
                    "last_commit_index": max(matching_commits),
                    "count": len(matching_commits),
                }

        # Check temporal ordering of phases
        is_ordered = True
        phase_order = ["setup", "implementation", "refinement"]
        last_first_index = -1
        for phase in phase_order:
            if phase in phases_found:
                if phases_found[phase]["first_commit_index"] < last_first_index:
                    is_ordered = False
                last_first_index = phases_found[phase]["first_commit_index"]

        # Bulk upload detection: all commits within a very short timeframe
        is_bulk = False
        if commit_count > 1 and len(timestamps) >= 2:
            from datetime import datetime, timezone
            try:
                first_ts = datetime.fromisoformat(timestamps[0])
                last_ts = datetime.fromisoformat(timestamps[-1])
                total_span_hours = (last_ts - first_ts).total_seconds() / 3600
                # If all commits are within 1 hour and > 5 commits, suspicious
                is_bulk = total_span_hours < 1 and commit_count > 5
            except (ValueError, TypeError):
                pass

        has_progression = (
            len(phases_found) >= 2
            and is_ordered
            and not is_bulk
            and commit_count > 3
        )

        return {
            "is_progression": has_progression,
            "is_bulk_upload": is_bulk,
            "phases_found": phases_found,
            "phase_order_correct": is_ordered,
            "commit_count": commit_count,
            "pattern": "progressive" if has_progression else ("bulk_upload" if is_bulk else "unclear"),
            "details": (
                f"Detected {len(phases_found)} development phases "
                f"({', '.join(phases_found.keys())}). "
                f"Phase ordering {'correct' if is_ordered else 'incorrect'}. "
                f"Bulk upload: {is_bulk}."
            ),
        }


    @staticmethod
    def analyze_ast(repo_path: str) -> Dict[str, any]:
        """
        Deep AST analysis: finds StateGraph definitions, Pydantic/TypedDict models,
        edge wiring, structured output calls, reducer usage, and topology shape.
        """
        results = {
            "state_definitions": [],
            "graph_definitions": [],
            "parallel_edges": [],
            "structured_output_calls": [],
            # New: reducer detection
            "reducer_annotations": [],
            # New: topology analysis
            "topology": {
                "nodes_added": [],
                "edges": [],           # (source, target)
                "conditional_edges": [],  # (source, targets_list)
                "fan_out_sources": [],   # nodes with multiple outgoing edges
                "fan_in_targets": [],    # nodes with multiple incoming edges
                "has_fan_out_fan_in": False,
                "error_handling_edges": [],
            },
        }

        for root, dirs, files in os.walk(repo_path):
            # Skip noise directories
            dirs[:] = [d for d in dirs if d not in [".venv", ".git", "__pycache__", "node_modules"]]
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, repo_path)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            source = f.read()
                        tree = ast.parse(source)

                        for node in ast.walk(tree):
                            # --- Pydantic / TypedDict class detection ---
                            if isinstance(node, ast.ClassDef):
                                for base in node.bases:
                                    if (isinstance(base, ast.Name) and base.id in ["BaseModel", "TypedDict"]) or \
                                       (isinstance(base, ast.Attribute) and base.attr in ["BaseModel", "TypedDict"]):
                                        results["state_definitions"].append(f"{relative_path}: {node.name}")

                            # --- Call-based detection ---
                            if isinstance(node, ast.Call):
                                func = node.func

                                # StateGraph instantiation
                                if isinstance(func, ast.Name) and func.id == "StateGraph":
                                    results["graph_definitions"].append(f"{relative_path}: Line {node.lineno}")

                                if isinstance(func, ast.Attribute):
                                    # .add_edge / .add_conditional_edges
                                    if func.attr in ["add_edge", "add_conditional_edges"]:
                                        results["parallel_edges"].append(
                                            f"{relative_path}: {func.attr} at line {node.lineno}"
                                        )
                                        # Extract topology information
                                        _extract_edge_topology(node, func.attr, results["topology"])

                                    # .add_node
                                    if func.attr == "add_node" and node.args:
                                        node_name = _get_string_value(node.args[0])
                                        if node_name:
                                            results["topology"]["nodes_added"].append(
                                                f"{relative_path}: {node_name} at line {node.lineno}"
                                            )

                                    # .with_structured_output / .bind_tools
                                    if func.attr in ["with_structured_output", "bind_tools"]:
                                        results["structured_output_calls"].append(
                                            f"{relative_path}: {func.attr} at line {node.lineno}"
                                        )

                            # --- Reducer annotation detection ---
                            # Look for Annotated[..., operator.ior] or Annotated[..., operator.add]
                            if isinstance(node, ast.Subscript):
                                if isinstance(node.value, ast.Name) and node.value.id == "Annotated":
                                    reducer_info = _extract_reducer_info(node, relative_path)
                                    if reducer_info:
                                        results["reducer_annotations"].append(reducer_info)

                    except Exception as e:
                        print(f"Error parsing {file_path}: {e}")

        # --- Post-processing: validate topology shape ---
        _analyze_topology_shape(results["topology"])

        return results

    @staticmethod
    def cleanup(repo_path: str):
        """Removes the temporary directory, ignoring errors on Windows."""
        import shutil
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path, ignore_errors=True)


def _get_string_value(node) -> Optional[str]:
    """Extract string value from an AST node (Constant or Str)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_edge_topology(call_node, call_type: str, topology: dict):
    """Extract source/target pairs from add_edge or add_conditional_edges calls."""
    args = call_node.args

    if call_type == "add_edge" and len(args) >= 2:
        source = _get_string_value(args[0])
        target = _get_string_value(args[1])

        # Handle START/END constants (they're Name nodes, not strings)
        if source is None and isinstance(args[0], ast.Name):
            source = args[0].id  # "START" or "END"
        if target is None and isinstance(args[1], ast.Name):
            target = args[1].id

        if source and target:
            topology["edges"].append((source, target))

    elif call_type == "add_conditional_edges" and len(args) >= 2:
        source = _get_string_value(args[0])
        if source is None and isinstance(args[0], ast.Name):
            source = args[0].id

        # Try to extract target dict from kwargs or third positional arg
        target_map = None
        if len(args) >= 3 and isinstance(args[2], ast.Dict):
            target_map = args[2]
        elif call_node.keywords:
            for kw in call_node.keywords:
                if isinstance(kw.value, ast.Dict):
                    target_map = kw.value
                    break

        if source and target_map:
            targets = []
            for val in target_map.values:
                t = _get_string_value(val)
                if t:
                    targets.append(t)
            if targets:
                topology["conditional_edges"].append((source, targets))
                for t in targets:
                    topology["edges"].append((source, t))


def _extract_reducer_info(subscript_node, file_path: str) -> Optional[str]:
    """Extract reducer annotation info from Annotated[Type, operator.xxx] subscripts."""
    # Annotated is a subscript: Annotated[X, Y]
    slice_node = subscript_node.slice

    # Handle Tuple slice (Python 3.9+)
    if isinstance(slice_node, ast.Tuple) and len(slice_node.elts) >= 2:
        reducer_node = slice_node.elts[1]
        # Check for operator.ior, operator.add, etc.
        if isinstance(reducer_node, ast.Attribute):
            module = ""
            if isinstance(reducer_node.value, ast.Name):
                module = reducer_node.value.id
            reducer_name = reducer_node.attr
            return (
                f"{file_path}: Annotated reducer "
                f"{module}.{reducer_name} at line {subscript_node.lineno}"
            )
    return None


def _analyze_topology_shape(topology: dict):
    """
    Validates fan-out/fan-in topology from extracted edges.
    A fan-out is a node with >1 outgoing edges.
    A fan-in is a node with >1 incoming edges.
    """
    outgoing = defaultdict(list)  # source -> [targets]
    incoming = defaultdict(list)  # target -> [sources]

    for source, target in topology["edges"]:
        outgoing[source].append(target)
        incoming[target].append(source)

    # Find fan-out nodes (>1 outgoing edge)
    for source, targets in outgoing.items():
        if len(set(targets)) > 1:
            topology["fan_out_sources"].append({
                "node": source,
                "targets": list(set(targets)),
                "degree": len(set(targets)),
            })

    # Find fan-in nodes (>1 incoming edge)
    for target, sources in incoming.items():
        if len(set(sources)) > 1:
            topology["fan_in_targets"].append({
                "node": target,
                "targets": list(set(sources)),
                "degree": len(set(sources)),
            })

    # Validate true fan-out/fan-in pattern exists
    topology["has_fan_out_fan_in"] = (
        len(topology["fan_out_sources"]) >= 1
        and len(topology["fan_in_targets"]) >= 1
    )

    # NEW: Detect "Double Fan" pattern (Layer 1: Forensic, Layer 2: Judicial)
    # This specifically looks for multiple fan-out points that converged then fanned out again.
    detective_fanout = any(s["node"] in ["START", "context_builder"] for s in topology["fan_out_sources"])
    aggregator_converge = any("aggregator" in t["node"].lower() for t in topology["fan_in_targets"])
    
    # Check if we have a fan-out from an aggregator (Layer 2)
    aggregator_fanout = any("aggregator" in s["node"].lower() for s in topology["fan_out_sources"])
    
    topology["has_double_fan_pattern"] = (
        detective_fanout and aggregator_converge and aggregator_fanout
    )

    # Check for error-handling edges and their convergence
    for source, target in topology["edges"]:
        if any(kw in (target or "").lower() for kw in ["error", "fail", "fallback"]):
            topology["error_handling_edges"].append({"source": source, "target": target})

    # NEW: Assert Convergence - ensure judges/detectives converge BEFORE chief_justice/END
    midpoint_targets = [t["node"] for t in topology["fan_in_targets"] if t["node"] not in ["END", "chief_justice"]]
    topology["structural_convergence"] = len(midpoint_targets) >= 1
