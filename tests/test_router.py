"""Tests del router de producto (decision de escalado; sin API, todo monkeypatcheado)."""

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
    monkeypatch.setattr(router, "run_p3", lambda d, g: (_ for _ in ()).throw(AssertionError("p3 no debe correr")))
    findings, choice = router.route(_dossier(), GUIDES)
    assert findings == b1out
    assert choice.startswith("b1")


def test_coverage_gaps_escalate_to_p3_dedup(monkeypatch):
    b1out = [_g(f"b{i}") for i in range(5)]
    p3out = [_g("p1"), _g("p2"), _g("p3")]
    monkeypatch.setattr(router, "run_b1", lambda d, g: b1out)
    monkeypatch.setattr(router, "_assess_gaps", lambda g, f: {"seguir": True, "guideline_ids": ["HAX-G5"]})
    monkeypatch.setattr(router, "run_p3", lambda d, g: p3out)
    # sentinel: confirmamos que el dedup se aplica a la salida de p3
    monkeypatch.setattr(router, "deduplicate", lambda fs: fs[:1])
    findings, choice = router.route(_dossier(), GUIDES)
    assert "p3+dedup" in choice and "huecos" in choice
    assert findings == p3out[:1]  # dedup aplicado


def test_thin_b1_escalates_even_without_gaps(monkeypatch):
    # b1 vacio (su modo de fallo: inestabilidad / corrida a 0): escalar aunque no haya gaps.
    monkeypatch.setattr(router, "run_b1", lambda d, g: [])
    monkeypatch.setattr(router, "_assess_gaps", lambda g, f: {"seguir": False, "guideline_ids": []})
    monkeypatch.setattr(router, "run_p3", lambda d, g: [_g("p1")])
    findings, choice = router.route(_dossier(), GUIDES)
    assert "escalado" in choice and "escaso" in choice


def test_gaps_with_invalid_guideline_ids_not_treated_as_gap(monkeypatch):
    # Si el modelo pide seguir pero con ids inexistentes, no cuenta como hueco real.
    b1out = [_g(f"b{i}") for i in range(5)]
    monkeypatch.setattr(router, "run_b1", lambda d, g: b1out)
    monkeypatch.setattr(router, "_assess_gaps", lambda g, f: {"seguir": True, "guideline_ids": ["NOPE-99"]})
    monkeypatch.setattr(router, "run_p3", lambda d, g: (_ for _ in ()).throw(AssertionError("no debe escalar")))
    findings, choice = router.route(_dossier(), GUIDES)
    assert findings == b1out and choice.startswith("b1")
