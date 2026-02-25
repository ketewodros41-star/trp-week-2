from langgraph.graph import StateGraph, START, END
from src.state import AgentState
from src.nodes.detectives import repo_investigator_node, doc_analyst_node, evidence_aggregator_node
from src.nodes.judges import prosecutor_node, defense_node, tech_lead_node
from src.nodes.justice import chief_justice_node
import json

def create_graph():
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("repo_investigator", repo_investigator_node)
    workflow.add_node("doc_analyst", doc_analyst_node)
    workflow.add_node("evidence_aggregator", evidence_aggregator_node)
    
    workflow.add_node("prosecutor", prosecutor_node)
    workflow.add_node("defense", defense_node)
    workflow.add_node("tech_lead", tech_lead_node)
    
    workflow.add_node("chief_justice", chief_justice_node)

    # Layer 1: Detectives (Parallel Fan-Out)
    workflow.add_edge(START, "repo_investigator")
    workflow.add_edge(START, "doc_analyst")
    
    # Fan-In to Aggregator
    workflow.add_edge("repo_investigator", "evidence_aggregator")
    workflow.add_edge("doc_analyst", "evidence_aggregator")
    
    # Layer 2: Judges (Parallel Fan-Out)
    workflow.add_edge("evidence_aggregator", "prosecutor")
    workflow.add_edge("evidence_aggregator", "defense")
    workflow.add_edge("evidence_aggregator", "tech_lead")
    
    # Fan-In to Supreme Court
    workflow.add_edge("prosecutor", "chief_justice")
    workflow.add_edge("defense", "chief_justice")
    workflow.add_edge("tech_lead", "chief_justice")
    
    workflow.add_edge("chief_justice", END)

    return workflow.compile()

if __name__ == "__main__":
    # Example execution script
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Load Rubric
    with open("rubric.json", "r") as f:
        rubric = json.load(f)
        
    app = create_graph()
    
    initial_state = {
        "repo_url": "https://github.com/langchain-ai/langgraph", # Example
        "pdf_path": "reports/interim_report.pdf",
        "rubric_dimensions": rubric["dimensions"],
        "evidences": {},
        "opinions": [],
        "final_report": None
    }
    
    # For visualization/debug
    # print(app.get_graph().draw_ascii())
    
    result = app.invoke(initial_state)
    print("Audit Complete. Report generated in audit/report.md")
