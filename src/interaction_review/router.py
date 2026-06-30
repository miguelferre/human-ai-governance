"""Enrutado por dificultad: el mapa de resultados, automatizado.

Conclusion del experimento (RESULTADOS.md): con un modelo fuerte, en casos FACILES el
prompt unico (b1) basta y es el mas conciso; en casos DIFICILES hace falta ESTRUCTURA
(b1 es inestable, una corrida se fue a 0) y el pipeline (p3) es lo robusto. La dificultad
NO se conoce a priori, asi que el router la INFIERE:

1. Corre b1 (barato, conciso).
2. Pregunta al modelo si quedan AREAS sin cubrir (reusa el gap-check de A4).
3. Si hay huecos -o b1 vino escaso (su modo de fallo: inestabilidad)-> ESCALA a p3 + dedup.
   Si no, se queda con b1.

Asi se obtiene lo mejor de cada celda del mapa: conciso cuando se puede, exhaustivo cuando
hace falta; y el escalado por "b1 escaso" cubre justo la inestabilidad de b1 (la corrida a 0).
NO es un rung de la escalera (no se compara en `comparar`): es la capa de PRODUCTO.
"""

from __future__ import annotations

from interaction_review.approaches._generator import generate  # noqa: F401  (asegura backend cargado)
from interaction_review.approaches.a4_agent import _assess_gaps
from interaction_review.approaches.b1_single_prompt import run as run_b1
from interaction_review.approaches.p3_pipeline import run as run_p3
from interaction_review.dedup import deduplicate
from interaction_review.schemas import Dossier, Finding, Guideline

# Si b1 trae menos hallazgos anclados que esto, lo tratamos como "escaso" y escalamos
# aunque el gap-check no lo pida: blinda contra la inestabilidad de b1 (corrida a 0).
MIN_B1_GROUNDED: int = 3


def route(dossier: Dossier, guidelines: list[Guideline]) -> tuple[list[Finding], str]:
    """Elige b1 (facil) o p3+dedup (dificil) segun la cobertura. Devuelve (findings, eleccion)."""
    by_id = {g.id: g for g in guidelines}
    b1 = run_b1(dossier, guidelines)
    grounded = [f for f in b1 if f.is_grounded()]

    decision = _assess_gaps(guidelines, b1)
    real_gaps = bool(decision.get("seguir")) and any(
        i in by_id for i in decision.get("guideline_ids", [])
    )
    thin = len(grounded) < MIN_B1_GROUNDED

    if real_gaps or thin:
        motivo = "b1 escaso" if thin and not real_gaps else "huecos de cobertura"
        return deduplicate(run_p3(dossier, guidelines)), f"p3+dedup (escalado: {motivo})"
    return b1, "b1 (caso facil: cobertura suficiente)"
