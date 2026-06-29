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

from interaction_review.approaches.a4_agent import run as run_a4
from interaction_review.approaches.b0_checklist import run as run_b0
from interaction_review.approaches.b1_single_prompt import run as run_b1
from interaction_review.approaches.b2_few_shot import run as run_b2
from interaction_review.approaches.p3_pipeline import run as run_p3
from interaction_review.schemas import Dossier, Finding, Guideline

Approach = Callable[[Dossier, list[Guideline]], list[Finding]]

REGISTRY: dict[str, Approach] = {
    "b0": run_b0,  # checklist determinista (sin LLM)
    "b1": run_b1,  # prompt unico zero-shot
    "b2": run_b2,  # prompt unico few-shot
    "p3": run_p3,  # pipeline determinista: barrido por bloques (NO agente)
    "a4": run_a4,  # agente: bucle con control de flujo decidido por el modelo
}

__all__ = ["REGISTRY", "Approach", "run_b0", "run_b1", "run_b2", "run_p3", "run_a4"]
