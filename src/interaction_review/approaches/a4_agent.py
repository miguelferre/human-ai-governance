"""A4 - Agente: bucle con control de flujo decidido por el MODELO (no por codigo).

Diferencia clave con P3 (pipeline fijo): P3 barre SIEMPRE los mismos bloques. A4 hace
una pasada inicial amplia y luego, en cada iteracion, el MODELO decide -mirando lo que
lleva- que areas faltan y si merece otra pasada o parar. Esa autonomia (que investigar
y cuando terminar, segun el estado) es lo que lo hace agente.

Barandilla anti-loop: MAX_ITERS acota el numero de iteraciones (no hay bucle abierto).
"""

from __future__ import annotations

from interaction_review import llm, prompts
from interaction_review.approaches._generator import gen_temperature, generate
from interaction_review.schemas import Dossier, Finding, Guideline

MAX_ITERS = 4  # tope duro de iteraciones (1 amplia + hasta 3 dirigidas)


def _assess_gaps(guidelines: list[Guideline], findings: list[Finding]) -> dict:
    """Decision AUTONOMA del modelo: ¿seguir? ¿que guidelines investigar ahora?"""
    payload = [{"title": f.title, "guideline_ids": f.guideline_ids} for f in findings]
    out = llm.call_structured(
        model=llm.gen_model(),
        system=prompts.AGENT_GAPS_SYSTEM,
        user=prompts.agent_gaps_user(guidelines, payload),
        tool=prompts.AGENT_GAPS_TOOL,
        temperature=gen_temperature(),
    )
    return out if isinstance(out, dict) else {"seguir": False, "guideline_ids": []}


def run(dossier: Dossier, guidelines: list[Guideline]) -> list[Finding]:
    by_id = {g.id: g for g in guidelines}
    findings: list[Finding] = generate(dossier, guidelines, few_shot=False, label="a4-it0")

    for it in range(1, MAX_ITERS):
        decision = _assess_gaps(guidelines, findings)
        if not decision.get("seguir"):
            break
        ids = [i for i in decision.get("guideline_ids", []) if i in by_id]
        if not ids:
            break
        target = [by_id[i] for i in ids]
        findings.extend(generate(dossier, target, few_shot=False, label=f"a4-it{it}"))

    return [f.model_copy(update={"id": f"a4-{n:03d}"}) for n, f in enumerate(findings, start=1)]
