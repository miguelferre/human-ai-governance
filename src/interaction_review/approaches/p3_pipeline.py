"""P3 - Pipeline determinista (NO agente): barrido por bloques de aspectos.

Hipotesis (de los datos de B1): una sola pasada cubre ~38% por corrida pero la union
de varias llega a ~73%; o sea, una pasada unica se deja aspectos. P3 hace una pasada
FOCALIZADA por cada bloque de guidelines y junta los hallazgos, para subir el recall
por corrida sin perder anclaje.

Flujo FIJO (sin decisiones autonomas del modelo): N pasadas (una por bloque) -> merge.
Eso lo distingue de un agente (A4): aqui el control de flujo lo decide el codigo.
"""

from __future__ import annotations

from interaction_review.approaches._generator import generate
from interaction_review.schemas import Dossier, Finding, Guideline

# Bloques de aspectos de interaccion -> ids de guideline. Cubren TODO HAX-18 + PAIR.
BUCKETS: dict[str, list[str]] = {
    "presentacion_y_confianza": ["HAX-G2", "HAX-G4", "HAX-G11", "PAIR-ET-1", "PAIR-ET-2", "PAIR-ET-3"],
    "correccion_y_feedback": ["HAX-G9", "HAX-G15", "HAX-G16", "PAIR-FC-1", "PAIR-FC-2"],
    "invocacion_alertas_tiempo": ["HAX-G3", "HAX-G5", "HAX-G7", "HAX-G8"],
    "onboarding_modelo_mental": ["HAX-G1", "PAIR-MM-1", "PAIR-MM-2", "PAIR-UN-1", "PAIR-UN-2"],
    "robustez_evolucion_supervision": [
        "HAX-G6", "HAX-G10", "HAX-G12", "HAX-G13", "HAX-G14", "HAX-G17", "HAX-G18",
        "PAIR-EF-1", "PAIR-EF-2", "PAIR-DE-1",
    ],
}


def run(dossier: Dossier, guidelines: list[Guideline]) -> list[Finding]:
    by_id = {g.id: g for g in guidelines}
    collected: list[Finding] = []
    for bucket, ids in BUCKETS.items():
        gl = [by_id[i] for i in ids if i in by_id]
        if not gl:
            continue
        collected.extend(generate(dossier, gl, few_shot=False, label=f"p3-{bucket}"))
    # Re-id unico y estable (los labels por bloque colisionarian en el indice).
    return [f.model_copy(update={"id": f"p3-{n:03d}"}) for n, f in enumerate(collected, start=1)]
