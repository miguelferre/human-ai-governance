"""Approaches de revision (la 'escalera de complejidad' del plan).

Todos comparten la misma firma para que la comparacion sea justa:

    run(dossier: Dossier, guidelines: list[Guideline]) -> list[Finding]

Escalera:
  - b0: checklist determinista (sin LLM). El suelo.
  - b1: prompt unico zero-shot.            (F2)
  - b2: prompt unico few-shot.             (F2)
  - p3: pipeline determinista (NO agente). (solo si los datos lo piden)
  - a4: agente.                            (solo si los datos lo piden)
"""

from __future__ import annotations

from typing import Callable

from interaction_review.approaches.b0_checklist import run as run_b0
from interaction_review.schemas import Dossier, Finding, Guideline

Approach = Callable[[Dossier, list[Guideline]], list[Finding]]

REGISTRY: dict[str, Approach] = {
    "b0": run_b0,
}

__all__ = ["REGISTRY", "Approach", "run_b0"]
