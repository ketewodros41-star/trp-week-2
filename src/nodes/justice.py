import os
from src.state import AgentState, AuditReport, CriterionResult, JudicialOpinion


def chief_justice_node(state: AgentState) -> dict:
    """The Supreme Court: Synthesizes opinions into a final verdict using deterministic rules."""
    opinions = state["opinions"]
    dimensions = state["rubric_dimensions"]

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

        scores = [o.score for o in dim_opinions]
        avg_score = sum(scores) / len(scores)
        final_score = 0
        dissent_summary = None

        # ---------------------------------------------------------------
        # DETERMINISTIC SYNTHESIS RULES
        # ---------------------------------------------------------------

        # Rule 1: Rule of Security
        # If the Prosecutor identifies a security vulnerability (score <= 2 AND "security"
        # keyword in argument), the score is capped at 3 regardless of Defense points.
        security_flagged = (
            prosecutor is not None
            and prosecutor.score <= 2
            and any(kw in prosecutor.argument.lower() for kw in ["security", "os.system", "injection", "sanitiz"])
        )
        if security_flagged:
            final_score = min(3, round(avg_score))
            dissent_summary = (
                f"SECURITY OVERRIDE: Prosecutor flagged a critical security risk "
                f"('{prosecutor.argument[:120]}...'). Score capped at 3 regardless of Defense arguments."
            )

        # Rule 2: Rule of Evidence / Fact Supremacy
        # If Defense claims high theoretical depth but repo evidence shows artifact is missing,
        # Defense is overruled.
        elif (
            defense is not None
            and defense.score >= 4
            and "metacognition" in defense.argument.lower()
        ):
            # Check if repo investigator found the referenced artifacts
            evidences = state.get("evidences", {})
            theoretical_evidence = evidences.get("theoretical_depth", [])
            if theoretical_evidence and not any(e.found for e in theoretical_evidence):
                final_score = min(defense.score, 3)
                dissent_summary = (
                    "FACT SUPREMACY: Defense claimed deep metacognition, but Detective evidence "
                    "shows the PDF report was not found or contained no supporting content. "
                    "Defense overruled for hallucination."
                )
            else:
                # Rule 3: Rule of Functionality — Tech Lead carries highest weight for architecture
                if tech_lead and "graph_orchestration" in dim_id:
                    final_score = round((avg_score + tech_lead.score * 2) / 3)
                else:
                    final_score = round((avg_score + (tech_lead.score if tech_lead else avg_score)) / 2)

        # Rule 3: Rule of Functionality — Tech Lead is tie-breaker
        elif tech_lead:
            if "graph_orchestration" in dim_id or "architecture" in dim_id.lower():
                # Highest weight given to Tech Lead for architecture dimensions
                final_score = round((avg_score + tech_lead.score * 2) / 3)
            else:
                final_score = round((avg_score + tech_lead.score) / 2)
        else:
            final_score = round(avg_score)

        # Clamp to valid range
        final_score = max(1, min(5, final_score))

        # Rule 4: Dissent Requirement — variance > 2 must include explicit dissent
        score_variance = max(scores) - min(scores)
        if score_variance > 2:
            conflict_line = (
                f"HIGH VARIANCE ({score_variance} pts): "
                f"Prosecutor={prosecutor.score if prosecutor else 'N/A'}, "
                f"Defense={defense.score if defense else 'N/A'}, "
                f"TechLead={tech_lead.score if tech_lead else 'N/A'}. "
                f"Synthesis favored {'TechLead' if tech_lead else 'Average'}."
            )
            dissent_summary = (dissent_summary + " | " + conflict_line) if dissent_summary else conflict_line

        # Build remediation from judges who scored < 4
        remediation_parts = [o.argument for o in dim_opinions if o.score < 4]
        remediation = " | ".join(remediation_parts) if remediation_parts else "No immediate remediation required."

        criterion_results.append(CriterionResult(
            dimension_id=dim_id,
            dimension_name=dim_name,
            final_score=final_score,
            judge_opinions=dim_opinions,
            dissent_summary=dissent_summary,
            remediation=remediation,
        ))
        overall_scores.append(final_score)

    overall_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0.0

    weak_dimensions = len([c for c in criterion_results if c.final_score < 4])
    remediation_plan = (
        f"Focused remediation required for {weak_dimensions} dimension(s). "
        "See Criterion Breakdown below for file-level instructions per dimension."
    )

    report = AuditReport(
        repo_url=state["repo_url"],
        executive_summary=(
            f"Audit of `{state['repo_url']}` completed. "
            f"Overall Score: **{overall_score:.2f}/5.00**. "
            f"{weak_dimensions} dimension(s) require remediation."
        ),
        overall_score=overall_score,
        criteria=criterion_results,
        remediation_plan=remediation_plan,
    )

    # ---------------------------------------------------------------
    # SERIALIZE TO MARKDOWN (Required deliverable)
    # ---------------------------------------------------------------
    md_lines = [
        f"# Audit Report: {state['repo_url']}",
        "",
        "## Executive Summary",
        report.executive_summary,
        "",
        f"- **Overall Score:** {report.overall_score:.2f} / 5.00",
        f"- **Dimensions Evaluated:** {len(criterion_results)}",
        f"- **Dimensions Requiring Remediation:** {weak_dimensions}",
        "",
        "---",
        "",
        "## Criterion Breakdown",
        "",
    ]

    for crit in report.criteria:
        md_lines.append(f"### {crit.dimension_name} (Score: {crit.final_score}/5)")
        md_lines.append("")

        if crit.dissent_summary:
            md_lines.append(f"> [!NOTE]")
            md_lines.append(f"> **Synthesis/Dissent:** {crit.dissent_summary}")
            md_lines.append("")

        for op in crit.judge_opinions:
            md_lines.append(f"**{op.judge}** (Score: {op.score}/5): {op.argument}")
            if op.cited_evidence:
                md_lines.append(f"  - *Evidence cited:* {', '.join(op.cited_evidence)}")
            md_lines.append("")

        md_lines.append(f"**Remediation:** {crit.remediation}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    md_lines.append("## Final Remediation Plan")
    md_lines.append("")
    md_lines.append(report.remediation_plan)
    md_lines.append("")

    md_content = "\n".join(md_lines)

    # Ensure output directory exists from env or default
    output_dir = os.getenv("AUDIT_OUTPUT_DIR", "audit/report_onself_generated")
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[ChiefJustice] Audit report written to {report_path}")
    return {"final_report": report}
