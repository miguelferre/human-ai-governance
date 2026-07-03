"""Tests for the product router (escalation decision; no API, everything monkeypatched)."""

from interaction_review import router
from interaction_review.guidelines import all_guidelines
from interaction_review.schemas import Dossier, Finding, Source, SourceKind


def _dossier() -> Dossier:
    return Dossier(
        system_name="X", domain="Y", summary="Z",
        sources=[Source(id="t1", kind=SourceKind.TECHNICIAN, label="T", content="c")],
    )


def _g(fid: str, gid: str = "HAX-G1") -> Finding:
    return Finding(id=fid, title=fid, guideline_ids=[gid], locus="locus", evidence="ev")


GUIDES = list(all_guidelines())


def test_easy_case_stays_b1(monkeypatch):
    b1out = [_g(f"b{i}") for i in range(5)]
    monkeypatch.setattr(router, "run_b1", lambda d, g: b1out)
    monkeypatch.setattr(router, "_assess_gaps", lambda g, f: {"seguir": False, "guideline_ids": []})
    monkeypatch.setattr(router, "run_p3", lambda d, g: (_ for _ in ()).throw(AssertionError("p3 must not run")))
    findings, choice = router.route(_dossier(), GUIDES)
    assert findings == b1out
    assert choice.startswith("b1")


def test_coverage_gaps_escalate_to_p3_dedup(monkeypatch):
    b1out = [_g(f"b{i}") for i in range(5)]
    p3out = [_g("p1"), _g("p2"), _g("p3")]
    monkeypatch.setattr(router, "run_b1", lambda d, g: b1out)
    monkeypatch.setattr(router, "_assess_gaps", lambda g, f: {"seguir": True, "guideline_ids": ["HAX-G5"]})
    monkeypatch.setattr(router, "run_p3", lambda d, g: p3out)
    # sentinel: we confirm that dedup is applied to the p3 output
    monkeypatch.setattr(router, "deduplicate", lambda fs: fs[:1])
    findings, choice = router.route(_dossier(), GUIDES)
    assert "p3+dedup" in choice and "gaps" in choice
    assert findings == p3out[:1]  # dedup applied


def test_thin_b1_escalates_even_without_gaps(monkeypatch):
    # b1 empty (its failure mode: instability / run drops to 0): escalate even without gaps.
    monkeypatch.setattr(router, "run_b1", lambda d, g: [])
    monkeypatch.setattr(router, "_assess_gaps", lambda g, f: {"seguir": False, "guideline_ids": []})
    monkeypatch.setattr(router, "run_p3", lambda d, g: [_g("p1")])
    findings, choice = router.route(_dossier(), GUIDES)
    assert "escalated" in choice and "sparse" in choice


def test_gaps_with_invalid_guideline_ids_not_treated_as_gap(monkeypatch):
    # If the model asks to continue but with nonexistent ids, it does not count as a real gap.
    b1out = [_g(f"b{i}") for i in range(5)]
    monkeypatch.setattr(router, "run_b1", lambda d, g: b1out)
    monkeypatch.setattr(router, "_assess_gaps", lambda g, f: {"seguir": True, "guideline_ids": ["NOPE-99"]})
    monkeypatch.setattr(router, "run_p3", lambda d, g: (_ for _ in ()).throw(AssertionError("must not escalate")))
    findings, choice = router.route(_dossier(), GUIDES)
    assert findings == b1out and choice.startswith("b1")
