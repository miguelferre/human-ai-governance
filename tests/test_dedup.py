"""Tests for finding deduplication (product step).

Dedup is DETERMINISTIC and does not see the golden: it is tested with synthetic findings
whose expected behavior is reasoned by hand. The quantitative validation (reduction,
purity, coverage) over real runs lives in scripts/dedup_report.py, not here.
"""

from interaction_review.dedup import (
    DEFAULT_THRESHOLD,
    deduplicate,
    similarity,
)
from interaction_review.schemas import Finding, Severity


def _f(fid: str, title: str, locus: str, guidelines: list[str], **kw) -> Finding:
    return Finding(
        id=fid,
        title=title,
        locus=locus,
        evidence=kw.get("evidence", "evidencia"),
        guideline_ids=guidelines,
        severity=kw.get("severity", Severity.MEDIUM),
        rationale=kw.get("rationale", ""),
        recommendation=kw.get("recommendation", ""),
    )


# The typical duplicate: SAME problem, DIFFERENT guideline (what we saw in P3/p3n).
_ONB_A = _f("a", "Onboarding inicial sin reciclaje periodico", "Formacion a los medicos del piloto", ["HAX-G1"])
_ONB_B = _f("b", "Onboarding inicial sin reciclaje formal", "Formacion a los medicos del piloto", ["PAIR-MM-1"])
# Clearly different problem.
_OVERRIDE = _f("c", "Override asimetrico mal capturado", "Boton de rechazo del score", ["HAX-G9"])


def test_default_threshold_is_documented_value():
    # If it changes, it requires recalibration (scripts/dedup_report.py) and a note in RESULTADOS.md.
    assert DEFAULT_THRESHOLD == 0.60


def test_similarity_high_for_same_problem_different_guideline():
    assert similarity(_ONB_A, _ONB_B) >= DEFAULT_THRESHOLD


def test_similarity_low_for_distinct_problems():
    assert similarity(_ONB_A, _OVERRIDE) < DEFAULT_THRESHOLD


def test_similarity_guard_rejects_templated_titles_with_disjoint_vocab():
    # Same phrase pattern ("Falta de comunicacion de X ..."), DIFFERENT problems:
    # without real vocabulary overlap, the title ratio must NOT merge them (the guard).
    a = _f("x", "Falta de comunicacion del rendimiento por subgrupo", "Presentacion del score al medico", ["HAX-G2"])
    b = _f("y", "Falta de comunicacion de recalibraciones tras cambios", "Ciclo mensual de Change Request", ["HAX-G14"])
    assert similarity(a, b) < DEFAULT_THRESHOLD


def test_merges_same_problem_and_unions_guidelines():
    out = deduplicate([_ONB_A, _ONB_B])
    assert len(out) == 1
    merged = out[0]
    assert merged.merged_count == 2
    # Union of guidelines in order of appearance (the product value: one finding
    # per problem, annotated with ALL the guidelines it violates).
    assert merged.guideline_ids == ["HAX-G1", "PAIR-MM-1"]


def test_keeps_distinct_problems_separate():
    out = deduplicate([_ONB_A, _OVERRIDE])
    assert len(out) == 2


def test_representative_prefers_grounded_then_severe_then_rich():
    weak = _f("w", "Onboarding sin reciclaje", "Formacion medicos", ["HAX-G1"], severity=Severity.LOW)
    strong = _f(
        "s", "Onboarding sin reciclaje periodico", "Formacion a los medicos",
        ["PAIR-MM-1"], severity=Severity.HIGH, rationale="razon larga y concreta", recommendation="accion",
    )
    out = deduplicate([weak, strong])
    assert len(out) == 1
    # The representative (surviving text) is the most severe/rich one, and severity rises.
    assert out[0].title == strong.title
    assert out[0].severity == Severity.HIGH
    assert set(out[0].guideline_ids) == {"HAX-G1", "PAIR-MM-1"}


def test_single_finding_marked_merged_count_one():
    out = deduplicate([_OVERRIDE])
    assert len(out) == 1
    assert out[0].merged_count == 1


def test_empty_input():
    assert deduplicate([]) == []


def test_all_distinct_preserved():
    findings = [
        _f("1", "Onboarding sin reciclaje", "Formacion", ["HAX-G1"]),
        _f("2", "Override asimetrico mal capturado", "Boton rechazo", ["HAX-G9"]),
        _f("3", "Fatiga de alerta por avisos repetidos", "Popup de score en cada caso", ["HAX-G3"]),
    ]
    assert len(deduplicate(findings)) == 3


def test_idempotent():
    # Idempotent for WELL-SEPARATED clusters (the common case). Not a general guarantee:
    # a rebuilt representative can drift toward a neighbor (see deduplicate's docstring).
    once = deduplicate([_ONB_A, _ONB_B, _OVERRIDE])
    twice = deduplicate(once)
    assert len(once) == len(twice) == 2
    assert [f.title for f in once] == [f.title for f in twice]
    assert [f.merged_count for f in twice] == [f.merged_count for f in once]


def test_merged_count_default_is_one_on_fresh_finding():
    assert Finding(id="z", title="t").merged_count == 1
