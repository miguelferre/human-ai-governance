"""Render de informes en texto/markdown (la salida v1 es CLI, nunca interfaz)."""

from __future__ import annotations

from interaction_review.metrics import AggregateMetrics
from interaction_review.schemas import Dossier, Finding


def render_regulatory_crosswalk(findings: list[Finding]) -> str:
    """Seccion 'evidencia de conformidad': que requisitos del AI Act / NIST AI RMF
    tocan los hallazgos, y por que guideline. Orientativo, no dictamen legal (ADR-008).
    """
    from interaction_review.regulatory import crosswalk, framework_names

    cw = crosswalk(findings)
    lines: list[str] = ["## Crosswalk normativo (orientativo)", ""]
    if not cw:
        lines.append("_(Los hallazgos no citan guidelines mapeadas a marco normativo.)_")
        return "\n".join(lines)
    lines.append(
        "Requisitos que tocan los hallazgos de arriba, con la guideline que los ancla. "
        "**No es dictamen legal** (ver ADR-008): aplicabilidad segun rol y si el sistema "
        "es de alto riesgo."
    )
    lines.append("")
    names = framework_names()
    for fw, items in cw.items():
        lines.append(f"### {names.get(fw, fw)}")
        for ref, gids in items:
            lines.append(f"- **{ref}**: {', '.join(gids)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_findings_md(dossier: Dossier, findings: list[Finding], approach: str) -> str:
    """Informe de hallazgos en markdown."""
    lines: list[str] = []
    lines.append(f"# Revision de la capa de interaccion - {dossier.system_name}")
    lines.append("")
    lines.append(f"- **Dominio:** {dossier.domain}")
    lines.append(f"- **Approach:** {approach}")
    lines.append(f"- **Fuentes:** {len(dossier.sources)}")
    lines.append(f"- **Hallazgos:** {len(findings)}")
    grounded = sum(1 for f in findings if f.is_grounded())
    pct = (grounded / len(findings) * 100) if findings else 0.0
    lines.append(f"- **Anclados (guideline+locus+evidencia):** {grounded}/{len(findings)} ({pct:.0f}%)")
    # Si viene deduplicado, el informe consolida varios hallazgos crudos en cada uno.
    raw = sum(f.merged_count for f in findings)
    if raw > len(findings):
        lines.append(f"- **Deduplicado:** {raw} hallazgos crudos consolidados en {len(findings)}.")
    lines.append("")

    for f in findings:
        flag = "OK" if f.is_grounded() else "GENERICO?"
        consolida = f" _(consolida {f.merged_count})_" if f.merged_count > 1 else ""
        lines.append(f"## [{flag}] {f.title}{consolida}")
        lines.append("")
        lines.append(f"- **Guidelines:** {', '.join(f.guideline_ids) or '(ninguna)'}")
        lines.append(f"- **Severidad:** {f.severity.value}")
        lines.append(f"- **Locus:** {f.locus or '(sin locus concreto)'}")
        lines.append(f"- **Evidencia:** {f.evidence or '(sin evidencia)'}")
        if f.anti_pattern:
            lines.append(f"- **Anti-patron:** {f.anti_pattern}")
        if f.rationale:
            lines.append(f"- **Por que importa aqui:** {f.rationale}")
        if f.recommendation:
            lines.append(f"- **Recomendacion:** {f.recommendation}")
        lines.append("")
    return "\n".join(lines)


def render_metrics_md(aggregates: list[AggregateMetrics]) -> str:
    """Tabla comparativa de approaches (media +/- std sobre k corridas)."""
    lines: list[str] = []
    lines.append("# Comparativa de approaches")
    lines.append("")
    lines.append("| Approach | k | Recall | Precision | Genericidad | Grounding | Primary (F-beta*) |")
    lines.append("|---|---|---|---|---|---|---|")

    def cell(s) -> str:  # noqa: ANN001 - Stat
        return f"{s.mean:.2f} +/- {s.std:.2f}"

    for a in aggregates:
        lines.append(
            f"| {a.approach} | {a.k} | {cell(a.recall)} | {cell(a.precision)} | "
            f"{cell(a.genericity_rate)} | {cell(a.grounding_rate)} | {cell(a.primary_score)} |"
        )
    lines.append("")
    lines.append("> Primary = F-beta (beta>1, prioriza recall) sujeto a techo de genericidad (ADR-002).")
    lines.append("> Genericidad: menor es mejor. Grounding: mayor es mejor.")
    return "\n".join(lines)
