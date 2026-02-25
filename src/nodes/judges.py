from typing import List
from langchain_openai import ChatOpenAI
from src.state import AgentState, JudicialOpinion, Evidence
from langchain_core.prompts import ChatPromptTemplate

# Initialize LLM
llm = ChatOpenAI(model="gpt-4o", temperature=0)

PROSECUTOR_PROMPT = """You are the PROSECUTOR in a Digital Courtroom.
Your philosophy: "Trust No One. Assume Vibe Coding."
Your objective: Scrutinize the evidence for gaps, security flaws, and laziness.
If the evidence shows linear execution when parallelism is required, argue for a Score of 1.
Look for bypassed structure, hallucination, and technical neglect.

You will be given a rubric dimension and the evidence collected.
You must return a JudicialOpinion using the provided schema.
"""

DEFENSE_PROMPT = """You are the DEFENSE ATTORNEY in a Digital Courtroom.
Your philosophy: "Reward Effort and Intent. Look for the 'Spirit of the Law'."
Your objective: Highlight creative workarounds, deep thought, and effort, even if the implementation is imperfect.
If the code is buggy but shows deep understanding of concepts, argue for a higher score.
Look at the process and the 'Master Thinker' profile.

You will be given a rubric dimension and the evidence collected.
You must return a JudicialOpinion using the provided schema.
"""

TECH_LEAD_PROMPT = """You are the TECH LEAD in a Digital Courtroom.
Your philosophy: "Does it actually work? Is it maintainable?"
Your objective: Evaluate architectural soundness, code cleanliness, and practical viability.
Ignore the 'Vibe' and the 'Struggle'. Focus on the Artifacts.
Are tools isolated? Is state management robust? You are the tie-breaker.

You will be given a rubric dimension and the evidence collected.
You must return a JudicialOpinion using the provided schema.
"""

def get_judge_node(judge_name: str, system_prompt: str):
    structured_llm = llm.with_structured_output(JudicialOpinion)
    
    def judge_node(state: AgentState) -> dict:
        evidences = state["evidences"]
        dimensions = state["rubric_dimensions"]
        opinions = []
        
        for dim in dimensions:
            dim_id = dim["id"]
            relevant_evidence = evidences.get(dim_id, [])
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "Rubric Dimension: {dimension}\n\nEvidence: {evidence}")
            ])
            
            # Format evidence for the prompt
            evidence_str = "\n".join([f"- {e.goal}: {e.content} (Source: {e.location})" for e in relevant_evidence])
            
            chain = prompt | structured_llm
            opinion = chain.invoke({
                "dimension": str(dim),
                "evidence": evidence_str or "No evidence collected for this dimension."
            })
            
            # Ensure the judge and dimension ID are correctly set
            opinion.judge = judge_name
            opinion.criterion_id = dim_id
            opinions.append(opinion)
            
        return {"opinions": opinions}
    
    return judge_node

prosecutor_node = get_judge_node("Prosecutor", PROSECUTOR_PROMPT)
defense_node = get_judge_node("Defense", DEFENSE_PROMPT)
tech_lead_node = get_judge_node("TechLead", TECH_LEAD_PROMPT)
