"""P3-neutral (prueba A2) - Pipeline determinista con particion NEUTRAL de guidelines.

Control de overfitting (R-A del TESTPLAN): P3 'normal' agrupa las guidelines en 5
bloques SEMANTICOS hechos a mano conociendo el caso (p3_pipeline.BUCKETS). Si esa
agrupacion afinada fuera la fuente de la ventaja -y no la descomposicion en si-, P3
no generalizaria: seria overfitting al caso.

P3-neutral usa la particion de los PROPIOS AUTORES, ya presente en los datos: el
campo `group` de cada guideline (las 4 fases de HAX-18: Inicialmente / Durante /
Cuando se equivoca / Con el tiempo; y los 6 capitulos de PAIR). No hay diseno a
mano: los bloques se DERIVAN de los datos. Si P3-neutral ~= P3 en recall, la ventaja
es DESCOMPONER, no mis bloques -> la mejora generaliza.

Mismo flujo FIJO que P3 (una pasada focalizada por bloque -> merge); lo unico que
cambia es como se agrupan las guidelines. Sigue siendo un pipeline, NO un agente.
"""

from __future__ import annotations

from interaction_review.approaches._generator import generate
from interaction_review.schemas import Dossier, Finding, Guideline


def buckets_by_group(guidelines: list[Guideline]) -> dict[str, list[Guideline]]:
    """Agrupa por (corpus, group) preservando el orden de aparicion.

    Neutral por construccion: la clave es la taxonomia oficial del corpus, no una
    agrupacion nuestra. Con corpus hax+pair salen 4 (fases HAX) + 6 (capitulos PAIR).
    """
    buckets: dict[str, list[Guideline]] = {}
    for g in guidelines:
        key = f"{g.corpus.value}:{g.group}"
        buckets.setdefault(key, []).append(g)
    return buckets


def _slug(key: str) -> str:
    out = key.lower()
    for ch in (" ", ":", "+", "/"):
        out = out.replace(ch, "-")
    return "-".join(p for p in out.split("-") if p)


def run(dossier: Dossier, guidelines: list[Guideline]) -> list[Finding]:
    collected: list[Finding] = []
    for key, gl in buckets_by_group(guidelines).items():
        if not gl:
            continue
        collected.extend(generate(dossier, gl, few_shot=False, label=f"p3n-{_slug(key)}"))
    # Re-id unico y estable (los labels por bloque colisionarian en el indice).
    return [f.model_copy(update={"id": f"p3n-{n:03d}"}) for n, f in enumerate(collected, start=1)]
