"""B2 - Single prompt with one worked example (few-shot) to suppress genericity.

It is still ONE single LLM call; the only difference from B1 is the good/bad
example in the prompt.
"""

from __future__ import annotations

from interaction_review.approaches._generator import generate
from interaction_review.schemas import Dossier, Finding, Guideline


def run(dossier: Dossier, guidelines: list[Guideline]) -> list[Finding]:
    return generate(dossier, guidelines, few_shot=True, label="b2")
