"""B2 - Prompt unico con un ejemplo trabajado (few-shot) para suprimir genericidad.

Sigue siendo UNA sola llamada al LLM; la unica diferencia con B1 es el ejemplo
bueno/malo en el prompt.
"""

from __future__ import annotations

from interaction_review.approaches._generator import generate
from interaction_review.schemas import Dossier, Finding, Guideline


def run(dossier: Dossier, guidelines: list[Guideline]) -> list[Finding]:
    return generate(dossier, guidelines, few_shot=True, label="b2")
