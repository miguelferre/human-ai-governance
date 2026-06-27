"""B0 - Checklist determinista (sin LLM). El suelo de la escalera de baselines.

Por construccion, B0 ignora el contenido del dossier y emite una pregunta fija
por guideline. Es GENERICO a proposito: no ancla los hallazgos en un locus ni en
evidencia del sistema concreto. Sirve para fijar el listón mas bajo: si un
approach con LLM (B1) no supera claramente a esto, el LLM no esta aportando nada.
"""

from __future__ import annotations

from interaction_review.schemas import Dossier, Finding, Guideline


def run(dossier: Dossier, guidelines: list[Guideline]) -> list[Finding]:
    findings: list[Finding] = []
    for i, g in enumerate(guidelines, start=1):
        findings.append(
            Finding(
                id=f"b0-{i:03d}",
                title=f"Revisar guideline: {g.title}",
                guideline_ids=[g.id],
                # locus y evidence vacios A PROPOSITO: B0 no mira el sistema.
                locus="",
                evidence="",
                anti_pattern=g.anti_patterns[0] if g.anti_patterns else None,
                rationale=f"Comprobacion generica del cumplimiento de {g.id}.",
                recommendation=f"Verificar manualmente si el sistema cumple: {g.description}",
            )
        )
    return findings
