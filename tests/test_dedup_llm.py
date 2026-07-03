"""Tests for the semantic dedup layer (orchestration; LLM monkeypatched, no API).

The deterministic logic around the model is tested: that the merge respects the guarantee
of not losing or duplicating findings even if the model hallucinates ids or repeats one across two groups.
"""

import pytest

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
    # 'ZZZ' does not exist -> the group is left with 1 real member -> not merged.
    monkeypatch.setattr(llm, "call_structured", _fake([["a", "ZZZ"]]))
    out = dedup_llm.deduplicate_llm(findings, pre_dedup=False, locus_floor=0)
    assert len(out) == 3 and all(f.merged_count == 1 for f in out)


def test_id_in_two_groups_first_wins_no_duplication(monkeypatch):
    findings = [_f("a", "HAX-G1"), _f("b", "PAIR-MM-1"), _f("c", "HAX-G9")]
    monkeypatch.setattr(llm, "call_structured", _fake([["a", "b"], ["b", "c"]]))
    out = dedup_llm.deduplicate_llm(findings, pre_dedup=False, locus_floor=0)
    # b is already in the first group -> the second group is left with 1 (c) -> c alone.
    ids_seen = sorted(i for f in out for i in [f.id])
    assert len(out) == 2
    # No input finding is lost or duplicated (all represented exactly once).
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


def test_duplicate_ids_rejected():
    # The "no finding lost" guarantee relies on unique ids; collisions must be refused.
    findings = [_f("a", "HAX-G1"), _f("a", "HAX-G2")]  # same id
    with pytest.raises(ValueError):
        dedup_llm.deduplicate_llm(findings, pre_dedup=False, locus_floor=0)


def test_empty_groups_keeps_all_singletons(monkeypatch):
    findings = [_f("a", "HAX-G1"), _f("b", "HAX-G2")]
    monkeypatch.setattr(llm, "call_structured", _fake([]))
    out = dedup_llm.deduplicate_llm(findings, pre_dedup=False, locus_floor=0)
    assert len(out) == 2 and all(f.merged_count == 1 for f in out)


# --- anti-over-merge guardrail (the LLM proposes, the code vetoes) ---
def _real(fid: str, title: str, locus: str, gid: str) -> Finding:
    return Finding(id=fid, title=title, locus=locus, guideline_ids=[gid], evidence="e")


def test_guardrail_splits_dissimilar_locus(monkeypatch):
    # The LLM groups two DIFFERENT problems (disparate loci); the guardrail separates them.
    a = _real("a", "onboarding sin reciclaje periodico", "formacion inicial a los medicos", "HAX-G1")
    b = _real("b", "override asimetrico mal capturado", "boton de rechazo del score clinico", "HAX-G9")
    monkeypatch.setattr(llm, "call_structured", _fake([["a", "b"]]))
    out = dedup_llm.deduplicate_llm([a, b], pre_dedup=False, locus_floor=0.18)
    assert len(out) == 2 and all(f.merged_count == 1 for f in out)


def test_guardrail_keeps_same_locus(monkeypatch):
    # Same problem, same locus, different guideline: the guardrail KEEPS it merged.
    a = _real("a", "onboarding inicial sin reciclaje", "formacion a los medicos del piloto", "HAX-G1")
    b = _real("b", "onboarding sin refresco periodico", "formacion a los medicos del piloto", "PAIR-MM-1")
    monkeypatch.setattr(llm, "call_structured", _fake([["a", "b"]]))
    out = dedup_llm.deduplicate_llm([a, b], pre_dedup=False, locus_floor=0.18)
    assert len(out) == 1 and out[0].merged_count == 2
    assert set(out[0].guideline_ids) == {"HAX-G1", "PAIR-MM-1"}
