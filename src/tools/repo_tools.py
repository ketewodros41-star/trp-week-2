import os
import tempfile
import ast
import subprocess
from typing import List, Dict, Optional
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
        """Extracts git log --oneline --reverse."""
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
    def analyze_ast(repo_path: str) -> Dict[str, List[str]]:
        """Parses Python files in the repo to find StateGraph and Pydantic models."""
        results = {
            "state_definitions": [],
            "graph_definitions": [],
            "parallel_edges": [],
            "structured_output_calls": []
        }

        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, repo_path)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            tree = ast.parse(f.read())
                        
                        for node in ast.walk(tree):
                            # Check for Pydantic/TypedDict
                            if isinstance(node, ast.ClassDef):
                                for base in node.bases:
                                    if (isinstance(base, ast.Name) and base.id in ["BaseModel", "TypedDict"]) or \
                                       (isinstance(base, ast.Attribute) and base.attr in ["BaseModel", "TypedDict"]):
                                        results["state_definitions"].append(f"{relative_path}: {node.name}")

                            # Check for StateGraph
                            if isinstance(node, ast.Call):
                                if isinstance(node.func, ast.Name) and node.func.id == "StateGraph":
                                    results["graph_definitions"].append(f"{relative_path}: Line {node.lineno}")
                                
                                # Check for .add_edge or .add_conditional_edges
                                if isinstance(node.func, ast.Attribute) and node.func.attr in ["add_edge", "add_conditional_edges"]:
                                    results["parallel_edges"].append(f"{relative_path}: {node.func.attr} at {node.lineno}")
                                
                                # Check for .with_structured_output or .bind_tools
                                if isinstance(node.func, ast.Attribute) and node.func.attr in ["with_structured_output", "bind_tools"]:
                                    results["structured_output_calls"].append(f"{relative_path}: {node.func.attr} at {node.lineno}")

                    except Exception as e:
                        print(f"Error parsing {file_path}: {e}")
        
        return results

    @staticmethod
    def cleanup(repo_path: str):
        """Removes the temporary directory."""
        import shutil
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)
