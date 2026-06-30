"""Capa SEMANTICA del deduplicado (con LLM): el residual que el lexico no junta.

El dedup determinista (dedup.py) colapsa duplicados textualmente evidentes, pero deja
el residual "mismo problema, redaccion/guideline muy distinta" (calibracion: matches
reales con Jaccard mediana 0.127 -> el texto no basta). Ese juicio es IRREDUCIBLE:
aqui lo hace un LLM, coherente con la tesis del proyecto (lo mecanico al codigo, al
modelo solo lo irreducible, ADR-004).

Flujo: dedup lexico (barato, sin LLM) -> UNA llamada al modelo para agrupar el residual
por problema subyacente -> merge de cada grupo (reutiliza dedup._merge: une guidelines,
severidad maxima, merged_count acumulado). El modelo SOLO agrupa por id; el merge y la
garantia de no perder ningun hallazgo son deterministas, en codigo.

Garantia: cada hallazgo de entrada aparece en EXACTAMENTE un hallazgo de salida (no se
pierde ni se duplica), aunque el modelo alucine ids o repita uno en dos grupos.
"""

from __future__ import annotations

from interaction_review import llm, prompts
from interaction_review.dedup import _merge, deduplicate
from interaction_review.schemas import Finding


def _llm_groups(findings: list[Finding], model: str | None, temperature: float) -> list[list[str]]:
    """Pide al modelo los grupos de ids que son el mismo problema. Devuelve listas de ids."""
    payload = [
        {"id": f.id, "title": f.title, "locus": f.locus, "guideline_ids": f.guideline_ids}
        for f in findings
    ]
    out = llm.call_structured(
        model=model or llm.judge_model(),
        system=prompts.SEMANTIC_DEDUP_SYSTEM,
        user=prompts.semantic_dedup_user(payload),
        tool=prompts.SEMANTIC_DEDUP_TOOL,
        temperature=temperature,
    )
    groups: list[list[str]] = []
    if isinstance(out, dict):
        for g in out.get("groups", []):
            if isinstance(g, dict):
                ids = [i for i in g.get("finding_ids", []) if isinstance(i, str)]
                if len(ids) >= 2:
                    groups.append(ids)
    return groups


def deduplicate_llm(
    findings: list[Finding],
    *,
    pre_dedup: bool = True,
    model: str | None = None,
    temperature: float = 0.0,
) -> list[Finding]:
    """Deduplica con una capa semantica (LLM) sobre el dedup lexico.

    `pre_dedup`: aplica antes el dedup determinista (recomendado: menos items que mandar
    al modelo y se centra en el residual dificil). Idempotente en el limite practico.
    """
    base = deduplicate(findings) if pre_dedup else list(findings)
    if len(base) < 2:
        return base

    by_id = {f.id: f for f in base}
    groups = _llm_groups(base, model, temperature)

    # Construye clusters respetando: cada id en UN solo cluster; orden por 1a aparicion.
    order = {f.id: n for n, f in enumerate(base)}
    assigned: set[str] = set()
    clusters: list[list[Finding]] = []
    for ids in groups:
        members = [by_id[i] for i in dict.fromkeys(ids) if i in by_id and i not in assigned]
        if len(members) >= 2:
            assigned.update(m.id for m in members)
            clusters.append(members)
    # Los no agrupados quedan solos.
    for f in base:
        if f.id not in assigned:
            clusters.append([f])
    # Orden estable: por el indice del miembro mas temprano de cada cluster.
    clusters.sort(key=lambda c: min(order[m.id] for m in c))
    return [_merge(c) for c in clusters]
