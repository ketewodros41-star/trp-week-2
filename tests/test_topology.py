import os
import sys
import unittest

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tools.repo_tools import RepoInvestigator


class TestGraphTopology(unittest.TestCase):
    def setUp(self):
        self.repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.inv = RepoInvestigator()

    def test_high_tier_orchestration_patterns(self):
        """
        Asserts that the graph implementation hits the 'High' tier (25/25 pts) 
        for Graph Orchestration as defined in the rubric.
        """
        ast_data = self.inv.analyze_ast(self.repo_path)
        topology = ast_data["topology"]

        print("\n--- Topology Verification ---")
        print(f"Nodes found: {len(topology['nodes_added'])}")
        print(f"Edges found: {len(topology['edges'])}")
        print(f"Fan-outs: {[s['node'] for s in topology['fan_out_sources']]}")
        print(f"Fan-ins: {[t['node'] for t in topology['fan_in_targets']]}")

        # 1. Assert Fan-Out / Fan-In Parallelism (Basic)
        self.assertTrue(topology["has_fan_out_fan_in"], "Missing fan-out/fan-in pattern.")

        # 2. Assert Double Fan Pattern (Forensic + Judicial Layers)
        self.assertTrue(topology["has_double_fan_pattern"], 
                        "Missing Double Fan pattern (Layers 1 & 2 fanning out via aggregators).")

        # 3. Assert Structural Convergence (Explicit Aggregators)
        self.assertTrue(topology["structural_convergence"], 
                        "Missing structural convergence on midpoint aggregators.")

        # 4. Assert Error Handling Edges
        self.assertGreater(len(topology["error_handling_edges"]), 0, 
                           "Missing explicit error-handling or fallback edges.")
        
        # 5. Assert Explicit Aggregator Node Presence
        aggregator_names = [n.lower() for n in topology["nodes_added"]]
        self.assertTrue(any("evidence_aggregator" in n for n in aggregator_names), 
                        "Missing explicit evidence_aggregator node.")
        self.assertTrue(any("judicial_aggregator" in n for n in aggregator_names), 
                        "Missing explicit judicial_aggregator node.")

        print("--- SUCCESS: High-Tier Orchestration Verified ---")


if __name__ == "__main__":
    unittest.main()
