from src.state import AgentState, AuditReport, CriterionResult, JudicialOpinion
import statistics

def chief_justice_node(state: AgentState) -> dict:
    """The Supreme Court: Synthesizes opinions into a final verdict using deterministic rules."""
    opinions = state["opinions"]
    dimensions = state["rubric_dimensions"]
    evidences = state["evidences"]
    
    criterion_results = []
    overall_scores = []
    
    for dim in dimensions:
        dim_id = dim["id"]
        dim_name = dim["name"]
        
        # Filter opinions for this criterion
        dim_opinions = [o for o in opinions if o.criterion_id == dim_id]
        if not dim_opinions:
            continue
            
        prosecutor = next((o for o in dim_opinions if o.judge == "Prosecutor"), None)
        defense = next((o for o in dim_opinions if o.judge == "Defense"), None)
        tech_lead = next((o for o in dim_opinions if o.judge == "TechLead"), None)
        
        # Rule-based synthesis
        final_score = 0
        dissent_summary = None
        
        # Calculate base score (weighted average)
        scores = [o.score for o in dim_opinions]
        avg_score = sum(scores) / len(scores)
        
        # Deterministic Rules
        # 1. Rule of Security (Security Flaws cap score at 3)
        if prosecutor and "security" in prosecutor.argument.lower() and prosecutor.score <= 2:
            final_score = min(3, int(avg_score))
            dissent_summary = "Security Rule: Prosecutor identified a critical security risk which capped the score."
        
        # 2. Rule of Functionality (Tech Lead carries highest weight)
        elif tech_lead:
            # Shift average towards Tech Lead
            final_score = round((avg_score + tech_lead.score) / 2)
        else:
            final_score = round(avg_score)
            
        # 3. Dissent Requirement (Variance > 2)
        if max(scores) - min(scores) > 2:
            dissent_summary = (dissent_summary or "") + f" High variance detected: Prosecutor ({prosecutor.score if prosecutor else 'N/A'}) vs Defense ({defense.score if defense else 'N/A'}). Synthesis favored {tech_lead.judge if tech_lead else 'Average'}."

        # Remediation (Synthesis of judge suggestions)
        remediation = ". ".join([o.argument for o in dim_opinions if o.score < 4])
        if not remediation:
            remediation = "No immediate remediation required."

        criterion_results.append(CriterionResult(
            dimension_id=dim_id,
            dimension_name=dim_name,
            final_score=final_score,
            judge_opinions=dim_opinions,
            dissent_summary=dissent_summary,
            remediation=remediation
        ))
        overall_scores.append(final_score)
        
    overall_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0
    
    report = AuditReport(
        repo_url=state["repo_url"],
        executive_summary=f"Audit completed with an overall score of {overall_score:.2f}/5.00.",
        overall_score=overall_score,
        criteria=criterion_results,
        remediation計劃=f"Focused remediation is required for {len([c for c in criterion_results if c.final_score < 4])} dimensions."
    )
    
    # Serialize to Markdown (Requirement)
    md_content = f"# Audit Report: {state['repo_url']}\n\n"
    md_content += f"## Executive Summary\n{report.executive_summary}\n\n"
    md_content += f"- **Overall Score:** {report.overall_score:.2f}/5\n\n"
    md_content += "## Criterion Breakdown\n"
    
    for crit in report.criteria:
        md_content += f"### {crit.dimension_name} (Score: {crit.final_score})\n"
        if crit.dissent_summary:
            md_content += f"> [!NOTE]\n> **Dissent/Synthesis:** {crit.dissent_summary}\n\n"
        
        for op in crit.judge_opinions:
            md_content += f"**{op.judge}:** (Score: {op.score}) {op.argument}\n\n"
            
        md_content += f"**Remediation:** {crit.remediation}\n\n"
        md_content += "---\n\n"
    
    md_content += f"## Final Remediation Plan\n{report.remediation_plan}\n"
    
    # Save the report
    with open("audit/report.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    return {"final_report": report}
