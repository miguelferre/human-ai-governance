"""LLM-juez: adjudica los hallazgos contra el golden set (ADR-002).

Usa un modelo y un prompt DISTINTOS del generador para no auto-evaluarse. Su
salida es un pre-etiquetado que despues revisa el humano (`human_confirmed`).
"""

from __future__ import annotations

from interaction_review import llm, prompts
from interaction_review.schemas import (
    Adjudication,
    AdjudicationLabel,
    Dossier,
    Finding,
    GoldenIssue,
)


def _payload(findings: list[Finding]) -> list[dict]:
    return [
        {
            "id": f.id,
            "title": f.title,
            "guideline_ids": f.guideline_ids,
            "locus": f.locus,
            "evidence": f.evidence,
        }
        for f in findings
    ]


def adjudicate(
    findings: list[Finding], golden: list[GoldenIssue], dossier: Dossier
) -> list[Adjudication]:
    """Devuelve una adjudicacion por hallazgo (en el mismo orden de `findings`)."""
    if not findings:
        return []
    golden_ids = {g.id for g in golden}
    out = llm.call_structured(
        model=llm.judge_model(),
        system=prompts.JUDGE_SYSTEM,
        user=prompts.judge_user(_payload(findings), golden, dossier),
        tool=prompts.JUDGE_TOOL,
        temperature=0.0,  # juez determinista
    )
    raw = {a.get("finding_id"): a for a in out.get("adjudications", [])} if isinstance(out, dict) else {}

    adjudications: list[Adjudication] = []
    for f in findings:
        a = raw.get(f.id)
        if a is None:
            # El juez no clasifico este hallazgo: por prudencia, incorrecto.
            adjudications.append(
                Adjudication(
                    finding_id=f.id,
                    label=AdjudicationLabel.FP_INCORRECT,
                    judge_rationale="(sin clasificacion del juez)",
                )
            )
            continue
        try:
            label = AdjudicationLabel(a.get("label"))
        except ValueError:
            label = AdjudicationLabel.FP_INCORRECT
        matched = a.get("matched_golden_id")
        # Coherencia: tp_match exige un id de golden valido; si no, es descubrimiento.
        if label == AdjudicationLabel.TP_MATCH and matched not in golden_ids:
            label = AdjudicationLabel.TP_NEW
            matched = None
        if label != AdjudicationLabel.TP_MATCH:
            matched = None
        adjudications.append(
            Adjudication(
                finding_id=f.id,
                label=label,
                matched_golden_id=matched,
                judge_rationale=str(a.get("judge_rationale", "")),
            )
        )
    return adjudications
