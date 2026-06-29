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


def _candidates(f: Finding, golden: list[GoldenIssue]) -> list[GoldenIssue]:
    """Candidatos del golden para un hallazgo: los que COMPARTEN guideline con el.

    Es un pre-filtro DETERMINISTA: reduce la tarea del juez de "escanea los 15" a
    "confirma si es uno de estos 1-3". Si no comparte guideline con ninguno (raro),
    se devuelven todos como salvaguarda para no negar un match por discrepancia de cita.
    """
    fg = set(f.guideline_ids)
    cands = [g for g in golden if fg & set(g.guideline_ids)]
    return cands if cands else list(golden)


def _payload(grounded: list[Finding], golden: list[GoldenIssue]) -> list[dict]:
    out = []
    for f in grounded:
        cands = _candidates(f, golden)
        out.append(
            {
                "id": f.id,
                "title": f.title,
                "locus": f.locus,
                "evidence": f.evidence,
                "candidates": [{"id": g.id, "description": g.description} for g in cands],
            }
        )
    return out


def adjudicate(
    findings: list[Finding], golden: list[GoldenIssue], dossier: Dossier
) -> list[Adjudication]:
    """Devuelve una adjudicacion por hallazgo (en el mismo orden de `findings`)."""
    if not findings:
        return []
    grounded = [f for f in findings if f.is_grounded()]
    # Candidatos por hallazgo (para validar que el juez elige uno de SU lista).
    cand_ids_by_finding = {f.id: {g.id for g in _candidates(f, golden)} for f in grounded}

    # Juzgar en LOTES pequenos: una sola llamada con 20+ hallazgos satura el limite de
    # tiempo del 14B (paso en P3). Lotes de BATCH mantienen cada llamada corta y fiable.
    raw: dict = {}
    BATCH = 6
    for i in range(0, len(grounded), BATCH):
        chunk = grounded[i : i + BATCH]
        out = llm.call_structured(
            model=llm.judge_model(),
            system=prompts.JUDGE_SYSTEM,
            user=prompts.judge_user(_payload(chunk, golden), dossier),
            tool=prompts.JUDGE_TOOL,
            temperature=0.0,  # juez determinista
        )
        if isinstance(out, dict):
            for a in out.get("adjudications", []):
                if a.get("finding_id"):
                    raw[a["finding_id"]] = a

    adjudications: list[Adjudication] = []
    for f in findings:
        # GENERICIDAD ESTRUCTURAL (gate duro, en codigo): sin anclaje => fp_generic SIEMPRE,
        # antes de mirar al juez. Sin esto, B0 (checklist vacio) contamina el suelo.
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
            adjudications.append(
                Adjudication(
                    finding_id=f.id,
                    label=AdjudicationLabel.FP_INCORRECT,
                    judge_rationale="(sin clasificacion del juez)",
                )
            )
            continue
        # La ETIQUETA se DERIVA: candidato valido -> tp_match; si "ninguno" -> tp_new/fp_incorrect.
        cc = str(a.get("corresponde_a_candidato", "")).strip()
        matched = cc if cc in cand_ids_by_finding.get(f.id, set()) else None
        if matched is not None:
            label = AdjudicationLabel.TP_MATCH
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
