"""B1 - Prompt unico zero-shot. El baseline con LLM a batir."""

from __future__ import annotations

from interaction_review.approaches._generator import generate
from interaction_review.schemas import Dossier, Finding, Guideline


def run(dossier: Dossier, guidelines: list[Guideline]) -> list[Finding]:
    return generate(dossier, guidelines, few_shot=False, label="b1")
