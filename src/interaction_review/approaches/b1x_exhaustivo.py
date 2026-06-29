"""B1x - Prompt unico EXHAUSTIVO (ablacion: ¿la ventaja de P3 es estructura o cantidad?).

Igual que B1 (una sola pasada, sin bloques) pero empujando al maximo el numero de
hallazgos. Si B1x se acerca a P3, la ventaja de P3 era generar MAS (cantidad), no su
descomposicion por bloques (estructura). Si B1x sigue por debajo, la estructura aporta.
"""

from __future__ import annotations

from interaction_review.approaches._generator import generate
from interaction_review.schemas import Dossier, Finding, Guideline

_PUSH = (
    "IMPORTANTE: se EXHAUSTIVO al maximo en esta UNICA respuesta. Recorre TODAS las areas "
    "de interaccion y reporta el MAYOR numero posible de problemas reales y anclados (apunta a "
    "20 o mas si existen), sin repetir y sin inventar genericos. No te limites a unos pocos."
)


def run(dossier: Dossier, guidelines: list[Guideline]) -> list[Finding]:
    return generate(dossier, guidelines, few_shot=False, label="b1x", extra=_PUSH)
