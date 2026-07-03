"""Tests for the B0 approach (deterministic checklist, the floor)."""

from interaction_review.approaches import run_b0
from interaction_review.guidelines import all_guidelines
from interaction_review.schemas import Dossier, Source, SourceKind


def _dossier() -> Dossier:
    return Dossier(
        system_name="x",
        domain="d",
        sources=[Source(id="s", kind=SourceKind.DOCUMENT, label="l", content="c")],
    )


def test_b0_emits_one_finding_per_guideline():
    gls = list(all_guidelines())
    findings = run_b0(_dossier(), gls)
    assert len(findings) == len(gls)
    assert [f.guideline_ids[0] for f in findings] == [g.id for g in gls]


def test_b0_findings_are_generic_by_construction():
    # B0 does NOT look at the system: no finding is grounded (no locus or evidence).
    findings = run_b0(_dossier(), list(all_guidelines()))
    assert all(not f.is_grounded() for f in findings)
