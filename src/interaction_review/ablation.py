"""Ablacion del testimonio del usuario final (ADR-007).

Pregunta que responde: el testimonio del usuario final, ¿aporta al RECALL del
revisor (descubre problemas que la documentacion tecnica no revela) o solo al
grounding/credibilidad de los que ya se detectarian?

Diseno del experimento:
  1. Etiquetar cada GoldenIssue con `revealed_by` (USER_ONLY / TECH_ONLY / BOTH).
  2. Correr el revisor sobre el dossier COMPLETO (con voz).
  3. Correr el revisor sobre el dossier SIN las fuentes END_USER (`without_voice`).
  4. Comparar el recall del subconjunto USER_ONLY entre ambas condiciones
     (`metrics.recall_by_revealed_by`).

Si el testimonio es el diferencial, el recall de USER_ONLY se desploma sin voz.
Si no cambia, el diferencial esta en el grounding, no en el descubrimiento.

Este modulo es OFFLINE y determinista: derivar el dossier de control y contar la
distribucion del golden no llaman al LLM. La corrida de los pasos 2-3 (que si lo
llama) vive en el flujo `comparar`.
"""

from __future__ import annotations

from interaction_review.schemas import Dossier, GoldenIssue, RevealedBy, SourceKind


def without_voice(dossier: Dossier) -> Dossier:
    """Dossier de control 'sin voz': el mismo salvo las fuentes END_USER.

    Es la condicion de ablacion: se retira el testimonio del usuario final y se
    conserva todo lo demas (documentacion y perfil tecnico). Devuelve una copia;
    no muta el original. Lanza si no quedaria ninguna fuente (un dossier hecho solo
    de voz no se puede ablar de forma justa).
    """
    kept = [s for s in dossier.sources if s.kind is not SourceKind.END_USER]
    if not kept:
        raise ValueError(
            "El dossier quedaria sin fuentes al quitar END_USER: no se puede ablar "
            "(no hay documentacion/tecnico frente a la que contrastar la voz)."
        )
    return dossier.model_copy(update={"sources": kept})


def has_voice(dossier: Dossier) -> bool:
    """True si el dossier contiene al menos una fuente END_USER (testimonio)."""
    return any(s.kind is SourceKind.END_USER for s in dossier.sources)


def revealed_by_distribution(golden: list[GoldenIssue]) -> dict[RevealedBy, int]:
    """Cuenta cuantos GoldenIssue hay por cada valor de `revealed_by`.

    Resultado OFFLINE informativo por si solo: si casi ningun issue es USER_ONLY,
    el techo de lo que el testimonio puede aportar al recall es bajo *antes* de
    gastar una sola llamada al LLM.
    """
    counts: dict[RevealedBy, int] = {rb: 0 for rb in RevealedBy}
    for g in golden:
        counts[g.revealed_by] += 1
    return counts
