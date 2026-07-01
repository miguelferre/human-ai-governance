"""Tests del mapeo normativo (ADR-008): integridad del mapa, union de refs y crosswalk."""

from interaction_review.regulatory import (
    FRAMEWORKS,
    crosswalk,
    framework_names,
    refs_for,
    unknown_map_ids,
    unmapped_guidelines,
)
from interaction_review.report import render_regulatory_crosswalk
from interaction_review.schemas import Finding


def _f(fid: str, gids: list[str]) -> Finding:
    return Finding(id=fid, title=fid, guideline_ids=gids, locus="x", evidence="y")


# --- Integridad del mapa ---------------------------------------------------- #
def test_every_guideline_is_mapped():
    """Ninguna guideline real se queda sin marco normativo."""
    assert unmapped_guidelines() == []


def test_no_phantom_ids_in_map():
    """El mapa no cita ids de guideline que no existen (erratas)."""
    assert unknown_map_ids() == []


def test_framework_names_present():
    names = framework_names()
    assert set(names) == set(FRAMEWORKS)
    assert "AI Act" in names["eu_ai_act"]
    assert "NIST" in names["nist_ai_rmf"]


# --- refs_for --------------------------------------------------------------- #
def test_automation_bias_maps_to_art_14_4_b():
    """Detalle vendible: la guideline de automation bias toca el Art. 14(4)(b) explicito."""
    refs = refs_for(["PAIR-ET-3"])
    assert "Art. 14(4)(b)" in refs["eu_ai_act"]


def test_refs_for_is_union_without_duplicates():
    refs = refs_for(["HAX-G2", "PAIR-ET-2"])  # ambas tocan precision/incertidumbre
    aa = refs["eu_ai_act"]
    assert aa == sorted(set(aa), key=aa.index) or len(aa) == len(set(aa))  # sin duplicados
    assert "Art. 15(1)" in aa  # comun a ambas


def test_refs_for_ignores_unknown_ids():
    assert refs_for(["NO-EXISTE"]) == {}


# --- crosswalk -------------------------------------------------------------- #
def test_crosswalk_groups_guidelines_under_each_ref():
    findings = [_f("f1", ["PAIR-ET-3"]), _f("f2", ["HAX-G2"])]
    cw = crosswalk(findings)
    aa = dict(cw["eu_ai_act"])
    assert "PAIR-ET-3" in aa["Art. 14(4)(b)"]
    assert "HAX-G2" in aa["Art. 15(1)"]


def test_crosswalk_ref_ordering_numeric():
    """Art. 9 va antes que Art. 13 (orden numerico, no alfabetico)."""
    findings = [_f("f", ["HAX-G2", "PAIR-EF-1"])]  # G2->Art.15, EF-1->Art.9 y 15
    refs = [ref for ref, _ in crosswalk(findings)["eu_ai_act"]]
    assert refs.index("Art. 9(2)") < refs.index("Art. 15(1)")


def test_crosswalk_empty_when_no_mapped_guidelines():
    assert crosswalk([_f("f", ["NO-EXISTE"])]) == {}
    assert crosswalk([_f("f", [])]) == {}


# --- render ----------------------------------------------------------------- #
def test_render_crosswalk_has_sections():
    md = render_regulatory_crosswalk([_f("f", ["PAIR-ET-3", "HAX-G6"])])
    assert "Crosswalk normativo" in md
    assert "AI Act" in md
    assert "NIST" in md
    assert "no es dictamen legal" in md.lower()


def test_render_crosswalk_graceful_when_empty():
    md = render_regulatory_crosswalk([_f("f", [])])
    assert "no citan guidelines mapeadas" in md.lower()
