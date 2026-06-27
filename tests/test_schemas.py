"""Tests del contrato de datos."""

import pytest
from pydantic import ValidationError

from interaction_review.schemas import Dossier, Finding, Source, SourceKind


def _src() -> Source:
    return Source(id="s1", kind=SourceKind.END_USER, label="u", content="texto")


def test_finding_grounded_requires_all_three_anchors():
    base = dict(id="f1", title="t")
    assert not Finding(**base).is_grounded()  # sin nada
    assert not Finding(**base, guideline_ids=["HAX-G9"]).is_grounded()  # falta locus+evidencia
    assert not Finding(
        **base, guideline_ids=["HAX-G9"], locus="captura de override"
    ).is_grounded()  # falta evidencia
    assert Finding(
        **base,
        guideline_ids=["HAX-G9"],
        locus="captura de override",
        evidence="'el override no se registra'",
    ).is_grounded()


def test_finding_blank_anchors_do_not_count():
    f = Finding(id="f", title="t", guideline_ids=["HAX-G1"], locus="   ", evidence="\n")
    assert not f.is_grounded()


def test_dossier_requires_at_least_one_source():
    with pytest.raises(ValidationError):
        Dossier(system_name="x", domain="d", sources=[])
    # con una fuente, valido
    Dossier(system_name="x", domain="d", sources=[_src()])
