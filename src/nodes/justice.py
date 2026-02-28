import os
import re
from collections import defaultdict
from typing import Dict, List

from src.state import AgentState, AuditReport, CriterionResult


DIMENSION_FILE_MAP = {
    "git_forensic_analysis": ["README.md"],
    "state_management_rigor": ["src/state.py"],
    "graph_orchestration": ["src/graph.py", "src/nodes/detectives.py"],
    "safe_tool_engineering": ["src/tools/repo_tools.py", "src/tools/vision_tools.py"],
    "structured_output_enforcement": ["src/nodes/judges.py"],
    "theoretical_depth": ["reports/interim_report_improved.md"],
    "report_accuracy": ["src/nodes/detectives.py", "reports/interim_report_improved.md"],
}


def _extract_file_refs(text: str) -> List[str]:
    patterns = [
        r"(?:src|tests?|reports|audit|peer_repo_eyor)[/\\][\w/\\.\-]+\.(?:py|js|ts|json|yaml|yml|toml|md)",
        r"[\w\-]+\.(?:py|js|ts|json|yaml|yml|toml|md)",
    ]
    refs = set()
    for pat in patterns:
        for match in re.findall(pat, text, re.IGNORECASE):
            refs.add(match.replace("\\", "/"))
    return sorted(refs)


def _evidence_found_ratio(evidence_items: list) -> float:
    if not evidence_items:
        return 0.0
    found = sum(1 for e in evidence_items if e.found)
    return found / len(evidence_items)


def _judge_by_name(opinions: list, name: str):
    return next((o for o in opinions if o.judge == name), None)


def _apply_security_override(prosecutor, dim_id: str, dim_evidence: list) -> bool:
    if not prosecutor:
        return False
    arg = prosecutor.argument.lower()
    security_terms = ["security", "os.system", "injection", "sanitiz", "unsafe"]
    evid_security_fail = any(
        ("safe_tool_engineering" in dim_id or "security" in dim_id)
        and not ev.found
        for ev in dim_evidence
    )
    return (prosecutor.score <= 2 and any(t in arg for t in security_terms)) or evid_security_fail


def _apply_fact_supremacy(defense, dim_evidence: list) -> bool:
    if not defense:
        return False
    if defense.score < 4:
        return False
    # Defense claims should not stand if evidence is weak or absent
    return _evidence_found_ratio(dim_evidence) < 0.5


def _weighted_architecture_score(scores: list, tech_lead_score: int) -> int:
    avg_score = sum(scores) / len(scores)
    weighted = (avg_score + tech_lead_score * 2) / 3
    return round(weighted)


def _synthesize_criterion_remediation(dim_id: str, dim_name: str, dim_opinions: list, dim_evidence: list) -> str:
    files = list(DIMENSION_FILE_MAP.get(dim_id, []))

    issue_lines = []
    for op in dim_opinions:
        if op.score < 4:
            issue_lines.append(f"[{op.judge} {op.score}/5] {op.argument[:180]}")

    extracted = []
    for op in dim_opinions:
        extracted.extend(_extract_file_refs(op.argument))
    for ev in dim_evidence:
        if ev.location:
            extracted.extend(_extract_file_refs(ev.location))
        if ev.content:
            extracted.extend(_extract_file_refs(ev.content))

    files.extend(extracted)
    files = sorted(set(files))

    if not files:
        files = ["src/graph.py"]

    actions = {
        "git_forensic_analysis": [
            "Adopt atomic commits that map to feature increments and include rationale in commit messages.",
            "Add a short contribution guide documenting expected commit granularity.",
        ],
        "state_management_rigor": [
            "Ensure every parallel-merged state field uses an explicit Annotated reducer.",
            "Add validation tests for state schema drift and reducer behavior.",
        ],
        "graph_orchestration": [
            "Add explicit tests asserting fan-out/fan-in topology and failure-routing behavior.",
            "Verify aggregator nodes remain mandatory synchronization points before synthesis.",
        ],
        "safe_tool_engineering": [
            "Harden clone and subprocess error paths with explicit stderr propagation.",
            "Add URL validation and documented constraints before repo cloning.",
        ],
        "structured_output_enforcement": [
            "Add stricter retry policy for malformed structured outputs and assert cited evidence presence.",
            "Add tests that verify persona score bands and citation discipline.",
        ],
        "theoretical_depth": [
            "Tie each claimed architecture concept to exact implementation files and concrete behavior.",
            "Add one implementation-linked example per major concept in the report.",
        ],
    }

    selected_actions = actions.get(
        dim_id,
        [
            f"Refine {dim_name} with explicit implementation evidence and tests.",
            "Add file-level validation checks to prevent regression.",
        ],
    )

    lines = [
        f"Affected files: {', '.join(f'`{f}`' for f in files)}",
        "Issues:",
    ]
    if issue_lines:
        lines.extend([f"- {line}" for line in issue_lines])
    else:
        lines.append("- No severe issues detected, but reliability improvements are still recommended.")

    lines.append("Actions:")
    lines.extend([f"- {a}" for a in selected_actions])

    return "\n".join(lines)


def _build_final_remediation_plan(criterion_results: list) -> str:
    weak = [c for c in criterion_results if c.final_score < 4]
    if not weak:
        return (
            "All dimensions scored 4+ out of 5. Continue with regression testing for "
            "judicial divergence and synthesis quality."
        )

    by_file: Dict[str, List[str]] = defaultdict(list)
    for c in weak:
        refs = _extract_file_refs(c.remediation)
        if not refs:
            refs = DIMENSION_FILE_MAP.get(c.dimension_id, ["src/graph.py"])
        for ref in refs:
            by_file[ref].append(f"{c.dimension_name} (score {c.final_score}/5)")

    lines = ["Priority remediation by file:"]
    for file_path in sorted(by_file):
        impacts = ", ".join(sorted(set(by_file[file_path])))
        lines.append(f"- `{file_path}`: {impacts}")

    lines.append("Execution order:")
    lines.append("1. Fix security/tooling and structured output reliability first.")
    lines.append("2. Improve synthesis dissent quality and criterion-level actionability.")
    lines.append("3. Tighten documentation-to-code cross-reference coverage.")

    return "\n".join(lines)


def chief_justice_node(state: AgentState) -> dict:
    """Synthesize judicial opinions into a deterministic final report."""
    opinions = state["opinions"]
    dimensions = state["rubric_dimensions"]
    evidences = state.get("evidences", {})

    criterion_results = []
    overall_scores = []

    for dim in dimensions:
        dim_id = dim["id"]
        dim_name = dim["name"]
        dim_opinions = [o for o in opinions if o.criterion_id == dim_id]
        if not dim_opinions:
            continue

        dim_evidence = evidences.get(dim_id, [])
        prosecutor = _judge_by_name(dim_opinions, "Prosecutor")
        defense = _judge_by_name(dim_opinions, "Defense")
        tech_lead = _judge_by_name(dim_opinions, "TechLead")

        scores = [o.score for o in dim_opinions]
        avg_score = sum(scores) / len(scores)
        final_score = round(avg_score)
        dissent_parts = []
        applied_rules = []

        # Rule 1: Security Override
        if _apply_security_override(prosecutor, dim_id, dim_evidence):
            final_score = min(final_score, 3)
            applied_rules.append("security_override")
            dissent_parts.append(
                "Security override applied: prosecutor/evidence indicates security risk; score capped at 3."
            )

        # Rule 2: Fact Supremacy
        if _apply_fact_supremacy(defense, dim_evidence):
            final_score = min(final_score, 3)
            applied_rules.append("fact_supremacy")
            dissent_parts.append(
                "Fact supremacy applied: defense optimism overruled due to weak supporting evidence."
            )

        # Rule 3: Functionality Weight (architecture dimensions)
        if tech_lead and ("graph_orchestration" in dim_id or "architecture" in dim_id.lower()):
            final_score = _weighted_architecture_score(scores, tech_lead.score)
            applied_rules.append("functionality_weight")
            dissent_parts.append(
                "Functionality weight applied: tech lead opinion weighted higher for architecture viability."
            )

        # Rule 4: Dissent requirement on high variance
        variance = max(scores) - min(scores)
        if variance > 2:
            dissent_parts.append(
                "Dissent required: score variance exceeds 2 points "
                f"(Prosecutor={prosecutor.score if prosecutor else 'N/A'}, "
                f"Defense={defense.score if defense else 'N/A'}, "
                f"TechLead={tech_lead.score if tech_lead else 'N/A'})."
            )
            # deterministic re-centering toward median for stability
            final_score = round(sorted(scores)[len(scores) // 2])
            applied_rules.append("dissent_recenter")

        final_score = max(1, min(5, final_score))

        remediation = _synthesize_criterion_remediation(
            dim_id=dim_id,
            dim_name=dim_name,
            dim_opinions=dim_opinions,
            dim_evidence=dim_evidence,
        )

        dissent_summary = None
        if dissent_parts:
            dissent_summary = " ".join(dissent_parts) + f" Rules applied: {', '.join(applied_rules)}."

        criterion_results.append(
            CriterionResult(
                dimension_id=dim_id,
                dimension_name=dim_name,
                final_score=final_score,
                judge_opinions=dim_opinions,
                dissent_summary=dissent_summary,
                remediation=remediation,
            )
        )
        overall_scores.append(final_score)

    overall_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0.0
    remediation_plan = _build_final_remediation_plan(criterion_results)

    report = AuditReport(
        repo_url=state["repo_url"],
        executive_summary=(
            f"Audit of `{state['repo_url']}` completed. "
            f"Overall Score: **{overall_score:.2f}/5.00**. "
            f"{len([c for c in criterion_results if c.final_score < 4])} dimension(s) require remediation."
        ),
        overall_score=overall_score,
        criteria=criterion_results,
        remediation_plan=remediation_plan,
    )

    # Serialize to markdown
    md_lines = [
        f"# Audit Report: {state['repo_url']}",
        "",
        "## Executive Summary",
        report.executive_summary,
        "",
        f"- Overall Score: {report.overall_score:.2f} / 5.00",
        f"- Dimensions Evaluated: {len(criterion_results)}",
        f"- Dimensions Requiring Remediation: {len([c for c in criterion_results if c.final_score < 4])}",
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
            md_lines.append(f"Synthesis/Dissent: {crit.dissent_summary}")
            md_lines.append("")

        for op in crit.judge_opinions:
            md_lines.append(f"{op.judge} (Score: {op.score}/5): {op.argument}")
            if op.cited_evidence:
                md_lines.append(f"- Evidence cited: {', '.join(op.cited_evidence)}")
            md_lines.append("")

        md_lines.append(f"Remediation:\n{crit.remediation}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    md_lines.append("## Final Remediation Plan")
    md_lines.append("")
    md_lines.append(report.remediation_plan)
    md_lines.append("")

    md_content = "\n".join(md_lines)

    output_dir = os.getenv("AUDIT_OUTPUT_DIR", "audit/report_onself_generated")
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[ChiefJustice] Audit report written to {report_path}")
    return {"final_report": report}
