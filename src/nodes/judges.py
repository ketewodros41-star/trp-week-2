import os
import time
import logging
from typing import List, Tuple

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from src.state import AgentState, JudicialOpinion, Evidence

logger = logging.getLogger(__name__)

# Ensure env vars are loaded before checking keys
load_dotenv()



def _build_llm():
    """Prefer Gemini when configured; fallback to OpenAI."""
    if os.getenv("GOOGLE_API_KEY"):
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    return ChatOpenAI(model="gpt-4o", temperature=0)


llm = _build_llm()

MAX_RETRIES = 3

PROSECUTOR_PROMPT = """You are the PROSECUTOR in a Digital Courtroom.
Persona: Hardline Security Auditor / Cynical Code Critic.
Philosophy: "Evidence over intent. All code is guilty of technical debt until proven innocent."
Scoring policy:
- Default range is 1-3.
- Score 4 is allowed ONLY if evidence is comprehensive and identifies zero significant risks.
- NEVER use score 5. Perfection is a myth of lazy developers.
Requirements:
- Hunt for "Vibe-coding": generic logic, missing error paths, unsupported documentation claims, and signs of laziness.
- Perform adversarial scrutiny for security flaws, unsafe defaults, and exploitable gaps.
- Be adversarial, cynical, and clinical. Avoid any praise.
- Every claim MUST cite an Evidence ID like [E1].
Return JudicialOpinion only.
"""

DEFENSE_PROMPT = """You are the DEFENSE ATTORNEY in a Digital Courtroom.
Persona: Senior Solutions Architect / Pragmatic Visionary.
Philosophy: "Innovation requires trade-offs. Implementation speed and architectural intent are primary values."
Scoring policy:
- Default range is 3-5.
- Score below 3 ONLY if evidence is overwhelmingly non-existent.
Requirements:
- Explicitly recognize effort, intent, and creative workarounds when supported by evidence.
- Highlight "Architectural Intent": justify missing details as "deferred implementation" or "prototyping agility".
- Argue that functional utility outweighs minor structural nitpicks.
- Be collaborative and supportive. Every claim MUST cite an Evidence ID like [E1].
Return JudicialOpinion only.
"""

TECH_LEAD_PROMPT = """You are the TECH LEAD in a Digital Courtroom.
Persona: Production Reliability Engineer / Maintenance Realist.
Philosophy: "Can we maintain this at 3 AM? Operational toil and remediation feasibility are all that matter."
Scoring policy:
- typical range is 2-4. 
- Use 5 only for exceptional, self-documenting, and fully-tested production-grade code.
Requirements:
- Focus on architectural soundness, maintainability, and practical production viability.
- Focus on "Operational Risk": complexity debt, lack of logging, and "clever" code that will break.
- Be pragmatic and clinical. Avoid the Prosecutor's cynicism and the Defense's idealism.
- Every claim MUST cite an Evidence ID like [E1].
Return JudicialOpinion only.
"""

# Persona-specific fallback messages
FALLBACK_MESSAGES = {
    "Prosecutor": "The prosecution's analysis tool failed. In the absence of proof, I assume maximum structural risk and lazy engineering. Evaluation blocked by technical error.",
    "Defense": "The defense's analysis was interrupted. We maintain that the architectural intent remains sound despite this telemetry failure.",
    "TechLead": "Internal monitoring failed for this dimension. Operationally, this is a 'unknown-unknown' risk. Defaulting to safe baseline.",
}



def _evidence_stats(relevant_evidence: List[Evidence]) -> Tuple[float, float]:
    if not relevant_evidence:
        return 0.0, 0.0
    found_ratio = sum(1 for e in relevant_evidence if e.found) / len(relevant_evidence)
    avg_conf = sum(e.confidence for e in relevant_evidence) / len(relevant_evidence)
    return found_ratio, avg_conf



def _format_evidence_with_ids(relevant_evidence: List[Evidence]) -> Tuple[str, List[str]]:
    if not relevant_evidence:
        return "No evidence collected for this dimension.", []

    lines: List[str] = []
    ids: List[str] = []
    for i, e in enumerate(relevant_evidence):
        eid = f"E{i + 1}"
        ids.append(eid)
        lines.append(
            f"[{eid}] found={e.found} confidence={e.confidence:.2f} "
            f"goal={e.goal} location={e.location} rationale={e.rationale} content={e.content}"
        )
    return "\n".join(lines), ids



def _ensure_citations(opinion: JudicialOpinion, evidence_ids: List[str]) -> JudicialOpinion:
    if evidence_ids and not opinion.cited_evidence:
        opinion.cited_evidence = evidence_ids[:2]
    return opinion



def _enforce_persona_score(
    judge_name: str,
    raw_score: int,
    found_ratio: float,
    avg_conf: float,
) -> int:
    score = raw_score

    if judge_name == "Prosecutor":
        if found_ratio < 0.5 or avg_conf < 0.65:
            score = min(score, 2)
        else:
            score = min(score, 3)

    elif judge_name == "Defense":
        if found_ratio >= 0.7 and avg_conf >= 0.7:
            score = max(score, 4)
        elif found_ratio >= 0.4:
            score = max(score, 3)
        else:
            score = min(score, 3)

    elif judge_name == "TechLead":
        if found_ratio < 0.4:
            score = min(score, 3)
        else:
            score = min(max(score, 2), 4)

    return max(1, min(5, score))



def get_judge_node(judge_name: str, system_prompt: str):
    def judge_node(state: AgentState) -> dict:
        evidences = state.get("evidences", {})
        dimensions = state["rubric_dimensions"]
        opinions: List[JudicialOpinion] = []

        # Fresh structured LLM for this node invocation
        structured_llm = llm.with_structured_output(JudicialOpinion)

        for dim in dimensions:
            dim_id = dim["id"]
            relevant_evidence = evidences.get(dim_id, [])
            evidence_str, evidence_ids = _format_evidence_with_ids(relevant_evidence)
            found_ratio, avg_conf = _evidence_stats(relevant_evidence)

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                (
                    "human",
                    "Rubric Dimension: {dimension}\n"
                    "Evidence Summary: found_ratio={found_ratio:.2f}, avg_confidence={avg_conf:.2f}\n\n"
                    "Evidence:\n{evidence}",
                ),
            ])

            opinion = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    chain = prompt | structured_llm
                    opinion = chain.invoke(
                        {
                            "dimension": str(dim),
                            "found_ratio": found_ratio,
                            "avg_conf": avg_conf,
                            "evidence": evidence_str,
                        }
                    )
                    break
                except Exception as e:
                    print(f"DEBUG LLM ERROR [{judge_name}]: {e}")
                    logger.warning(
                        "Judge '%s' retry %s/%s failed for '%s': %s",
                        judge_name,
                        attempt,
                        MAX_RETRIES,
                        dim_id,
                        e,
                    )
                    if attempt < MAX_RETRIES:
                        time.sleep(1.0 * attempt)

            if opinion is None:
                fallback_arg = FALLBACK_MESSAGES.get(
                    judge_name, f"Judicial analysis failed for '{dim_id}'."
                )
                opinions.append(
                    JudicialOpinion(
                        judge=judge_name,
                        criterion_id=dim_id,
                        score=1,
                        argument=fallback_arg,
                        cited_evidence=evidence_ids[:2],
                    )
                )
                continue

            opinion.judge = judge_name
            opinion.criterion_id = dim_id
            opinion.score = _enforce_persona_score(judge_name, opinion.score, found_ratio, avg_conf)
            opinion = _ensure_citations(opinion, evidence_ids)

            if judge_name == "Prosecutor" and found_ratio < 0.5:
                opinion.argument = (
                    opinion.argument
                    + " Evidence coverage is low; stricter scoring applied by prosecutor calibration."
                )
            if judge_name == "Defense" and found_ratio >= 0.7:
                opinion.argument = (
                    opinion.argument
                    + " Strong evidence coverage supports a higher defense baseline."
                )

            opinions.append(opinion)
            time.sleep(0.8)

        return {"opinions": opinions}

    return judge_node


prosecutor_node = get_judge_node("Prosecutor", PROSECUTOR_PROMPT)
defense_node = get_judge_node("Defense", DEFENSE_PROMPT)
tech_lead_node = get_judge_node("TechLead", TECH_LEAD_PROMPT)



def judicial_aggregator_node(state: AgentState) -> dict:
    """
    Dedicated synchronization node for the judicial layer.
    Ensures all judges have contributed before passing to Chief Justice.
    """
    opinions = state.get("opinions", [])
    dimensions = state["rubric_dimensions"]
    judge_names = ["Prosecutor", "Defense", "TechLead"]

    logger.info(
        "[JudicialAggregator] Synchronizing %s opinions for %s dimensions.",
        len(opinions),
        len(dimensions),
    )

    for dim in dimensions:
        dim_id = dim["id"]
        for jname in judge_names:
            found = any(o.judge == jname and o.criterion_id == dim_id for o in opinions)
            if not found:
                logger.warning("[JudicialAggregator] Missing opinion from %s for %s", jname, dim_id)

    return {"opinions": opinions}
