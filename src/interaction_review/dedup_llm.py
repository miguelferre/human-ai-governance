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
from interaction_review.dedup import _merge, _representative, deduplicate, text_similarity
from interaction_review.schemas import Finding

# Barandilla anti-sobrefundido (el LLM PROPONE, el codigo COMPRUEBA): dentro de un grupo
# que el modelo dio por "mismo problema", se VETA al miembro cuyo locus+titulo es muy
# dispar del representante (probablemente otro problema del mismo area). Calibrado offline:
# el prompt estricto solo no bajaba la impureza; este gate si. Floor bajo -> solo corta
# los emparejamientos egregios, conserva los reescritos genuinos (mismo locus, otra cita).
SEMANTIC_LOCUS_FLOOR: float = 0.18


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


def _refine_group(members: list[Finding], floor: float) -> list[list[Finding]]:
    """Barandilla: dentro de un grupo del LLM, separa a quien tenga locus muy dispar.

    Devuelve subgrupos: el nucleo (parecido al representante por titulo+locus) y cada
    outlier suelto. Asi un grupo que mezclaba dos problemas vecinos se parte y deja de
    conflar. No pierde hallazgos (los outliers quedan como singletons).
    """
    if len(members) < 2:
        return [members]
    rep = _representative(members)
    sig = f"{rep.title} {rep.locus}"
    core, outliers = [], []
    for m in members:
        if m.id == rep.id or text_similarity(f"{m.title} {m.locus}", sig) >= floor:
            core.append(m)
        else:
            outliers.append([m])
    return [core] + outliers


def deduplicate_llm(
    findings: list[Finding],
    *,
    pre_dedup: bool = True,
    model: str | None = None,
    temperature: float = 0.0,
    locus_floor: float = SEMANTIC_LOCUS_FLOOR,
) -> list[Finding]:
    """Deduplica con una capa semantica (LLM) sobre el dedup lexico.

    `pre_dedup`: aplica antes el dedup determinista (recomendado: menos items que mandar
    al modelo y se centra en el residual dificil). `locus_floor`: barandilla anti-sobrefundido
    (el LLM propone los grupos, el codigo veta miembros con locus dispar; 0 = sin barandilla).
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
    # Barandilla en codigo: parte los grupos que mezclan loci dispares.
    refined: list[list[Finding]] = []
    for c in clusters:
        refined.extend(_refine_group(c, locus_floor) if locus_floor > 0 else [c])
    # Orden estable: por el indice del miembro mas temprano de cada cluster.
    refined.sort(key=lambda c: min(order[m.id] for m in c))
    return [_merge(c) for c in refined]
