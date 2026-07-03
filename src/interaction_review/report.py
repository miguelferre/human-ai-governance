"""Rendering of reports in text/markdown (the v1 output is CLI, never a UI)."""

from __future__ import annotations

from interaction_review.metrics import AggregateMetrics
from interaction_review.schemas import Dossier, Finding


def render_regulatory_crosswalk(findings: list[Finding]) -> str:
    """'Evidence of conformity' section: which AI Act / NIST AI RMF requirements
    the findings touch, and through which guideline. Indicative, not a legal opinion (ADR-008).
    """
    from interaction_review.regulatory import crosswalk, framework_names, guideline_notes

    cw = crosswalk(findings)
    lines: list[str] = ["## Regulatory crosswalk (indicative)", ""]
    if not cw:
        lines.append("_(The findings do not cite guidelines mapped to a regulatory framework.)_")
        return "\n".join(lines)
    lines.append(
        "Requirements touched by the findings above, with the guideline that anchors them. "
        "**Not a legal opinion** (see ADR-008): applicability depends on the role and whether the "
        "system is high-risk."
    )
    lines.append("")
    names = framework_names()
    for fw, items in cw.items():
        lines.append(f"### {names.get(fw, fw)}")
        for ref, gids in items:
            lines.append(f"- **{ref}**: {', '.join(gids)}")
        lines.append("")
    notes = guideline_notes({gid for f in findings for gid in f.guideline_ids})
    if notes:
        lines.append("### Why these map")
        for gid, nota in notes:
            lines.append(f"- **{gid}**: {nota}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


_META_FIELDS = (("date", "Generated"), ("tool_version", "Tool version"), ("model", "Generator model"))


def render_findings_md(
    dossier: Dossier, findings: list[Finding], approach: str, *, meta: dict | None = None
) -> str:
    """Findings report in markdown. `meta` (optional) adds provenance lines (date/model/version)."""
    lines: list[str] = []
    lines.append(f"# Interaction layer review - {dossier.system_name}")
    lines.append("")
    lines.append(f"- **Domain:** {dossier.domain}")
    lines.append(f"- **Approach:** {approach}")
    lines.append(f"- **Sources:** {len(dossier.sources)}")
    lines.append(f"- **Findings:** {len(findings)}")
    grounded = sum(1 for f in findings if f.is_grounded())
    pct = (grounded / len(findings) * 100) if findings else 0.0
    lines.append(f"- **Anchored (guideline+locus+evidence):** {grounded}/{len(findings)} ({pct:.0f}%)")
    # If deduplicated, the report consolidates several raw findings into each one.
    raw = sum(f.merged_count for f in findings)
    if raw > len(findings):
        lines.append(f"- **Deduplicated:** {raw} raw findings consolidated into {len(findings)}.")
    if meta:
        for key, label in _META_FIELDS:
            if meta.get(key):
                lines.append(f"- **{label}:** {meta[key]}")
    lines.append("")

    for f in findings:
        flag = "OK" if f.is_grounded() else "GENERIC?"
        merged = f" _(consolidates {f.merged_count})_" if f.merged_count > 1 else ""
        lines.append(f"## [{flag}] {f.title}{merged}")
        lines.append("")
        lines.append(f"- **Guidelines:** {', '.join(f.guideline_ids) or '(none)'}")
        lines.append(f"- **Severity:** {f.severity.value}")
        lines.append(f"- **Locus:** {f.locus or '(no concrete locus)'}")
        lines.append(f"- **Evidence:** {f.evidence or '(no evidence)'}")
        if f.anti_pattern:
            lines.append(f"- **Anti-pattern:** {f.anti_pattern}")
        if f.rationale:
            lines.append(f"- **Why it matters here:** {f.rationale}")
        if f.recommendation:
            lines.append(f"- **Recommendation:** {f.recommendation}")
        lines.append("")
    return "\n".join(lines)


def render_metrics_md(aggregates: list[AggregateMetrics]) -> str:
    """Comparative table of approaches (mean +/- std over k runs)."""
    lines: list[str] = []
    lines.append("# Approach comparison")
    lines.append("")
    lines.append("| Approach | k | Recall | Precision | Genericity | Grounding | Primary (F-beta*) |")
    lines.append("|---|---|---|---|---|---|---|")

    def cell(s) -> str:  # noqa: ANN001 - Stat
        return f"{s.mean:.2f} +/- {s.std:.2f}"

    for a in aggregates:
        lines.append(
            f"| {a.approach} | {a.k} | {cell(a.recall)} | {cell(a.precision)} | "
            f"{cell(a.genericity_rate)} | {cell(a.grounding_rate)} | {cell(a.primary_score)} |"
        )
    lines.append("")
    lines.append("> Primary = F-beta (beta>1, prioritizes recall) subject to a genericity ceiling (ADR-002).")
    lines.append("> Genericity: lower is better. Grounding: higher is better.")
    return "\n".join(lines)
