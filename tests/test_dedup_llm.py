"""Tests de la capa semantica del dedup (orquestacion; LLM monkeypatcheado, sin API).

Se testea la logica determinista alrededor del modelo: que el merge respete la garantia
de no perder ni duplicar hallazgos aunque el modelo alucine ids o repita uno en dos grupos.
"""

from interaction_review import dedup_llm
from interaction_review import llm
from interaction_review.schemas import Finding, Severity


def _f(fid: str, gid: str, sev: Severity = Severity.MEDIUM) -> Finding:
    return Finding(id=fid, title=fid, guideline_ids=[gid], locus=fid, evidence="e", severity=sev)


def _fake(groups):
    return lambda **kw: {"groups": [{"finding_ids": g, "reason": "x"} for g in groups]}


def test_merges_groups_and_unions_guidelines(monkeypatch):
    findings = [_f("a", "HAX-G1"), _f("b", "PAIR-MM-1"), _f("c", "HAX-G9")]
    monkeypatch.setattr(llm, "call_structured", _fake([["a", "b"]]))
    out = dedup_llm.deduplicate_llm(findings, pre_dedup=False, locus_floor=0)
    assert len(out) == 2
    merged = next(f for f in out if f.merged_count == 2)
    assert set(merged.guideline_ids) == {"HAX-G1", "PAIR-MM-1"}
    assert {f.id for f in out if f.merged_count == 1} == {"c"}


def test_hallucinated_id_is_ignored(monkeypatch):
    findings = [_f("a", "HAX-G1"), _f("b", "HAX-G2"), _f("c", "HAX-G9")]
    # 'ZZZ' no existe -> el grupo queda con 1 miembro real -> no se funde.
    monkeypatch.setattr(llm, "call_structured", _fake([["a", "ZZZ"]]))
    out = dedup_llm.deduplicate_llm(findings, pre_dedup=False, locus_floor=0)
    assert len(out) == 3 and all(f.merged_count == 1 for f in out)


def test_id_in_two_groups_first_wins_no_duplication(monkeypatch):
    findings = [_f("a", "HAX-G1"), _f("b", "PAIR-MM-1"), _f("c", "HAX-G9")]
    monkeypatch.setattr(llm, "call_structured", _fake([["a", "b"], ["b", "c"]]))
    out = dedup_llm.deduplicate_llm(findings, pre_dedup=False, locus_floor=0)
    # b ya esta en el primer grupo -> el segundo grupo queda con 1 (c) -> c solo.
    ids_seen = sorted(i for f in out for i in [f.id])
    assert len(out) == 2
    # Ningun hallazgo de entrada se pierde ni se duplica (todos representados una vez).
    total = sum(f.merged_count for f in out)
    assert total == 3


def test_no_finding_lost(monkeypatch):
    findings = [_f(c, "HAX-G1") for c in ("a", "b", "c", "d")]
    monkeypatch.setattr(llm, "call_structured", _fake([["a", "b", "c", "d"]]))
    out = dedup_llm.deduplicate_llm(findings, pre_dedup=False, locus_floor=0)
    assert len(out) == 1 and out[0].merged_count == 4


def test_short_input_returned_as_is(monkeypatch):
    monkeypatch.setattr(llm, "call_structured", _fake([]))
    assert dedup_llm.deduplicate_llm([], pre_dedup=False, locus_floor=0) == []
    one = [_f("a", "HAX-G1")]
    assert dedup_llm.deduplicate_llm(one, pre_dedup=False, locus_floor=0) == one


def test_empty_groups_keeps_all_singletons(monkeypatch):
    findings = [_f("a", "HAX-G1"), _f("b", "HAX-G2")]
    monkeypatch.setattr(llm, "call_structured", _fake([]))
    out = dedup_llm.deduplicate_llm(findings, pre_dedup=False, locus_floor=0)
    assert len(out) == 2 and all(f.merged_count == 1 for f in out)


# --- barandilla anti-sobrefundido (el LLM propone, el codigo veta) ---
def _real(fid: str, title: str, locus: str, gid: str) -> Finding:
    return Finding(id=fid, title=title, locus=locus, guideline_ids=[gid], evidence="e")


def test_guardrail_splits_dissimilar_locus(monkeypatch):
    # El LLM agrupa dos problemas DISTINTOS (loci dispares); la barandilla los separa.
    a = _real("a", "onboarding sin reciclaje periodico", "formacion inicial a los medicos", "HAX-G1")
    b = _real("b", "override asimetrico mal capturado", "boton de rechazo del score clinico", "HAX-G9")
    monkeypatch.setattr(llm, "call_structured", _fake([["a", "b"]]))
    out = dedup_llm.deduplicate_llm([a, b], pre_dedup=False, locus_floor=0.18)
    assert len(out) == 2 and all(f.merged_count == 1 for f in out)


def test_guardrail_keeps_same_locus(monkeypatch):
    # Mismo problema, mismo locus, guideline distinta: la barandilla lo MANTIENE fundido.
    a = _real("a", "onboarding inicial sin reciclaje", "formacion a los medicos del piloto", "HAX-G1")
    b = _real("b", "onboarding sin refresco periodico", "formacion a los medicos del piloto", "PAIR-MM-1")
    monkeypatch.setattr(llm, "call_structured", _fake([["a", "b"]]))
    out = dedup_llm.deduplicate_llm([a, b], pre_dedup=False, locus_floor=0.18)
    assert len(out) == 1 and out[0].merged_count == 2
    assert set(out[0].guideline_ids) == {"HAX-G1", "PAIR-MM-1"}
