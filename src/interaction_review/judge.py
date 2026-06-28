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
    # Solo se envian al juez los hallazgos ANCLADOS; los no anclados son fp_generic por
    # el gate estructural (abajo) y no necesitan al LLM (ahorra la llamada para B0).
    grounded = [f for f in findings if f.is_grounded()]
    raw: dict = {}
    if grounded:
        out = llm.call_structured(
            model=llm.judge_model(),
            system=prompts.JUDGE_SYSTEM,
            user=prompts.judge_user(_payload(grounded), golden, dossier),
            tool=prompts.JUDGE_TOOL,
            temperature=0.0,  # juez determinista
        )
        raw = {a.get("finding_id"): a for a in out.get("adjudications", [])} if isinstance(out, dict) else {}

    adjudications: list[Adjudication] = []
    for f in findings:
        # GENERICIDAD ESTRUCTURAL (gate duro, en codigo): un hallazgo sin anclaje
        # (locus+evidencia) es generico SIEMPRE, aunque el juez diga que corresponde a
        # un golden por la guideline citada. Sin esto, B0 (checklist vacio) se "empareja"
        # por guideline y contamina el suelo.
        if not f.is_grounded():
            adjudications.append(
                Adjudication(
                    finding_id=f.id,
                    label=AdjudicationLabel.FP_GENERIC,
                    judge_rationale="(no anclado: sin locus/evidencia)",
                )
            )
            continue
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
        # La ETIQUETA se DERIVA de las sub-respuestas atomicas (no la decide el modelo),
        # para que no pueda contradecirse (decir 'corresponde a GI-3' y etiquetar tp_new).
        cg = str(a.get("corresponde_a_golden", "")).strip()
        matched = cg if cg in golden_ids else None
        if matched is not None:
            label = AdjudicationLabel.TP_MATCH
        elif bool(a.get("es_generico")):
            label = AdjudicationLabel.FP_GENERIC
        elif bool(a.get("es_real")):
            label = AdjudicationLabel.TP_NEW
        else:
            label = AdjudicationLabel.FP_INCORRECT
        adjudications.append(
            Adjudication(
                finding_id=f.id,
                label=label,
                matched_golden_id=matched,
                judge_rationale=str(a.get("judge_rationale", "")),
            )
        )
    return adjudications
