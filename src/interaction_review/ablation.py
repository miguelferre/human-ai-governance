"""Ablation of the end user's testimony (ADR-007).

Question it answers: does the end user's testimony contribute to the reviewer's
RECALL (discovering problems that the technical documentation does not reveal) or only to the
grounding/credibility of those that would already be detected?

Experiment design:
  1. Label each GoldenIssue with `revealed_by` (USER_ONLY / TECH_ONLY / BOTH).
  2. Run the reviewer over the COMPLETE dossier (with voice).
  3. Run the reviewer over the dossier WITHOUT the END_USER sources (`without_voice`).
  4. Compare the recall of the USER_ONLY subset between both conditions
     (`metrics.recall_by_revealed_by`).

If the testimony is the differentiator, USER_ONLY recall collapses without voice.
If it does not change, the differentiator is in grounding, not in discovery.

This module is OFFLINE and deterministic: deriving the control dossier and counting the
golden distribution do not call the LLM. The run of steps 2-3 (which does call it)
lives in the `compare` flow.
"""

from __future__ import annotations

from interaction_review.schemas import Dossier, GoldenIssue, RevealedBy, SourceKind


def without_voice(dossier: Dossier) -> Dossier:
    """Control dossier 'without voice': the same one except the END_USER sources.

    It is the ablation condition: the end user's testimony is removed and
    everything else is kept (documentation and technical profile). Returns a copy;
    it does not mutate the original. Raises if no source would remain (a dossier made only
    of voice cannot be ablated fairly).
    """
    kept = [s for s in dossier.sources if s.kind is not SourceKind.END_USER]
    if not kept:
        raise ValueError(
            "El dossier quedaria sin fuentes al quitar END_USER: no se puede ablar "
            "(no hay documentacion/tecnico frente a la que contrastar la voz)."
        )
    return dossier.model_copy(update={"sources": kept})


def has_voice(dossier: Dossier) -> bool:
    """True if the dossier contains at least one END_USER source (testimony)."""
    return any(s.kind is SourceKind.END_USER for s in dossier.sources)


def revealed_by_distribution(golden: list[GoldenIssue]) -> dict[RevealedBy, int]:
    """Counts how many GoldenIssue there are for each `revealed_by` value.

    An OFFLINE result informative on its own: if almost no issue is USER_ONLY,
    the ceiling of what the testimony can contribute to recall is low *before*
    spending a single LLM call.
    """
    counts: dict[RevealedBy, int] = {rb: 0 for rb in RevealedBy}
    for g in golden:
        counts[g.revealed_by] += 1
    return counts
