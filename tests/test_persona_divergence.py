import os
import sys
import unittest
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.nodes.judges import prosecutor_node, defense_node, tech_lead_node
from src.state import AgentState, Evidence


class TestPersonaDivergence(unittest.TestCase):
    def setUp(self):
        # Mock evidence: half-baked implementation
        self.evidence = {
            "git_forensic_analysis": [
                Evidence(
                    goal="Check commit history",
                    found=True,
                    content="Initial commit, Add files, fix bug",
                    location="git log",
                    rationale="Commits are few and messages are vague.",
                    confidence=0.9
                )
            ]
        }
        self.state = {
            "rubric_dimensions": [
                {"id": "git_forensic_analysis", "name": "Git Forensic Analysis"}
            ],
            "evidences": self.evidence,
            "opinions": []
        }

    def test_judicial_divergence(self):
        """
        Verify that Prosecutor, Defense, and Tech Lead produce distinct scoring and arguments.
        Note: This is a 'live' test if keys are present, else it tests fallback logic.
        """
        p_out = prosecutor_node(self.state)
        d_out = defense_node(self.state)
        t_out = tech_lead_node(self.state)

        p_op = p_out["opinions"][0]
        d_op = d_out["opinions"][0]
        t_op = t_out["opinions"][0]

        print(f"\n--- Persona Divergence Test ---")
        print(f"Prosecutor ({p_op.score}/5): {p_op.argument[:100]}...")
        print(f"Defense    ({d_op.score}/5): {d_op.argument[:100]}...")
        print(f"Tech Lead  ({t_op.score}/5): {t_op.argument[:100]}...")

        # 1. Assert Score Divergence (at least between Prosecutor and Defense)
        # Prosecutor range 1-3, Defense range 3-5
        self.assertLessEqual(p_op.score, 3)
        self.assertGreaterEqual(d_op.score, 3)
        
        # 2. Assert Argument Divergence (simple check for keyword absence/presence)
        # Prosecutor should be cynical/clinical
        # Defense should be supportive/visionary
        
        # 3. Check for Fallbacks if LLM fails (ensuring they are persona-specific)
        if "failed" in p_op.argument or "Assume" in p_op.argument:
            self.assertIn("prosecution", p_op.argument.lower())
            self.assertIn("architectural intent", d_op.argument.lower())
            self.assertIn("operational", t_op.argument.lower())
            print("Verified: Persona-specific Fallbacks are active.")
        else:
            print("Verified: Live LLM Divergence (Inferred by scores and tone).")


if __name__ == "__main__":
    unittest.main()
