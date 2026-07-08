"""Integrity of the held-out corpus under data/external/.

Every case is a pair (dossier.json, answer_key.json). This guards the whole corpus against
hand-editing typos: schemas validate, ids are unique, guideline_ids are real (no phantom ids),
and revealed_by is a known value. It is also the contract the Inspect dataset builder relies on.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from interaction_review.guidelines import all_guidelines
from interaction_review.schemas import Dossier, GoldenIssue

_EXTERNAL = Path(__file__).resolve().parents[1] / "data" / "external"
_VALID_GUIDELINE_IDS = {g.id for g in all_guidelines()}


def _cases() -> list[Path]:
    return sorted(
        d
        for d in _EXTERNAL.iterdir()
        if d.is_dir() and (d / "dossier.json").is_file() and (d / "answer_key.json").is_file()
    )


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_there_are_external_cases():
    cases = _cases()
    # 15 pre-existing held-out pairs + the Google Flood Hub climate case = 16.
    assert len(cases) >= 16, f"expected the held-out corpus (>=16 cases), found {len(cases)}"
    assert any(c.name == "google-flood-hub" for c in cases)


@pytest.mark.parametrize("case", _cases(), ids=lambda p: p.name)
def test_case_dossier_and_answer_key_are_valid(case: Path):
    # Dossier validates and has at least one source.
    dossier = Dossier.model_validate(_load(case / "dossier.json"))
    assert dossier.sources

    # Answer key: a non-empty-schema list of GoldenIssue (empty list allowed only for controls).
    raw = _load(case / "answer_key.json")
    assert isinstance(raw, list), f"{case.name}: answer_key.json must be a JSON array"
    golden = [GoldenIssue.model_validate(g) for g in raw]

    ids = [g.id for g in golden]
    assert len(ids) == len(set(ids)), f"{case.name}: duplicate GoldenIssue ids"

    # No phantom guideline ids: every cited guideline exists in the corpus.
    for g in golden:
        unknown = set(g.guideline_ids) - _VALID_GUIDELINE_IDS
        assert not unknown, f"{case.name}/{g.id}: unknown guideline ids {sorted(unknown)}"
