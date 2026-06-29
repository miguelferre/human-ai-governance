"""Generacion de hallazgos via LLM, compartida por B1 (zero-shot) y B2 (few-shot)."""

from __future__ import annotations

import os

from interaction_review import llm, prompts
from interaction_review.schemas import Dossier, Finding, Guideline, Severity


def gen_temperature() -> float:
    # Temperatura > 0 a proposito: queremos variabilidad entre las k corridas
    # para poder medir la estabilidad (ADR-002).
    return float(os.environ.get("GEN_TEMPERATURE", "1.0"))


def _to_finding(label: str, idx: int, raw: dict) -> Finding:
    sev = raw.get("severity", "medium")
    try:
        severity = Severity(sev)
    except ValueError:
        severity = Severity.MEDIUM
    return Finding(
        id=f"{label}-{idx:03d}",
        title=str(raw.get("title", "")).strip() or "(sin titulo)",
        guideline_ids=[str(g) for g in raw.get("guideline_ids", []) if str(g).strip()],
        locus=str(raw.get("locus", "")).strip(),
        evidence=str(raw.get("evidence", "")).strip(),
        anti_pattern=(raw.get("anti_pattern") or None),
        severity=severity,
        rationale=str(raw.get("rationale", "")).strip(),
        recommendation=str(raw.get("recommendation", "")).strip(),
    )


def generate(
    dossier: Dossier, guidelines: list[Guideline], *, few_shot: bool, label: str, extra: str = ""
) -> list[Finding]:
    """Una llamada al LLM -> lista de Finding. `label` prefija los ids (b1/b2).

    `extra`: instruccion adicional opcional en el prompt (p.ej. empujar exhaustividad en B1x).
    """
    user = prompts.generator_user(dossier, guidelines, few_shot=few_shot, extra=extra)
    out = llm.call_structured(
        model=llm.gen_model(),
        system=prompts.GENERATOR_SYSTEM,
        user=user,
        tool=prompts.FINDINGS_TOOL,
        temperature=gen_temperature(),
    )
    raw_findings = out.get("findings", []) if isinstance(out, dict) else []
    # Robustez: el tool-use de Anthropic no garantiza la estructura como el `format` local.
    # Si 'findings' viene como dict, tomar sus valores; descartar items que no sean objeto.
    if isinstance(raw_findings, dict):
        raw_findings = list(raw_findings.values())
    items = [rf for rf in raw_findings if isinstance(rf, dict)]
    return [_to_finding(label, i, rf) for i, rf in enumerate(items, start=1)]
