"""Tests de F2 sin tocar la API: prompts, parseo, logica del juez y orquestacion.

Las llamadas reales al LLM se monkeypatchean. Lo que se testea es la logica
determinista alrededor (anclaje, coherencia de etiquetas, agregacion).
"""

import pytest

from interaction_review import judge as judge_mod
from interaction_review import llm, prompts, runner
from interaction_review.approaches._generator import _to_finding
from interaction_review.guidelines import all_guidelines
from interaction_review.schemas import (
    Adjudication,
    AdjudicationLabel,
    Dossier,
    Finding,
    GoldenIssue,
    Source,
    SourceKind,
)


def _dossier() -> Dossier:
    return Dossier(
        system_name="Sistema X",
        domain="dominio Y",
        summary="resumen Z",
        sources=[Source(id="tech-1", kind=SourceKind.TECHNICIAN, label="Tecnico", content="hecho concreto")],
    )


# --- prompts ---
def test_format_dossier_incluye_fuentes_y_metadatos():
    txt = prompts.format_dossier(_dossier())
    assert "Sistema X" in txt and "dominio Y" in txt and "hecho concreto" in txt


def test_generator_user_fewshot_toggle_y_anclaje():
    g = list(all_guidelines())
    zero = prompts.generator_user(_dossier(), g, few_shot=False)
    few = prompts.generator_user(_dossier(), g, few_shot=True)
    assert "BIEN (anclado)" not in zero
    assert "BIEN (anclado)" in few
    # el catalogo de guidelines y el dossier estan en el prompt
    assert "HAX-G9" in zero and "Sistema X" in zero


def test_generator_system_prohibe_genericos():
    assert "PROHIBIDO" in prompts.GENERATOR_SYSTEM
    assert prompts.FINDINGS_TOOL["name"] == "report_findings"


# --- parseo de hallazgos ---
def test_to_finding_normaliza_y_calcula_anclaje():
    raw = {
        "title": "t",
        "guideline_ids": ["HAX-G9", ""],
        "locus": "el boton de override",
        "evidence": "'solo se pide el motivo al discrepar'",
        "severity": "altisima",  # invalida -> medium
        "rationale": "r",
        "recommendation": "rec",
    }
    f = _to_finding("b1", 3, raw)
    assert f.id == "b1-003"
    assert f.guideline_ids == ["HAX-G9"]  # filtra vacios
    assert f.severity.value == "medium"
    assert f.is_grounded() is True


def test_to_finding_sin_anclaje_no_grounded():
    f = _to_finding("b1", 1, {"title": "generico", "guideline_ids": [], "severity": "low"})
    assert not f.is_grounded()


# --- logica del juez (LLM monkeypatcheado) ---
def test_adjudicate_deriva_etiqueta_de_subrespuestas(monkeypatch):
    findings = [Finding(id=f"x{i}", title=f"x{i}") for i in (1, 2, 3, 4, 5)]
    golden = [GoldenIssue(id="G1", description="d")]

    def fake_call(**kwargs):
        # El modelo NO da etiqueta: da sub-respuestas y la derivamos en codigo.
        return {
            "adjudications": [
                {"finding_id": "x1", "judge_rationale": "ok", "corresponde_a_golden": "G1", "es_generico": False, "es_real": True},
                # id de golden inexistente -> no es match; real -> tp_new
                {"finding_id": "x2", "judge_rationale": "x", "corresponde_a_golden": "NOPE", "es_generico": False, "es_real": True},
                {"finding_id": "x3", "judge_rationale": "x", "corresponde_a_golden": "ninguno", "es_generico": True, "es_real": False},
                # x4 ausente a proposito -> fp_incorrect
                {"finding_id": "x5", "judge_rationale": "x", "corresponde_a_golden": "ninguno", "es_generico": False, "es_real": False},
            ]
        }

    monkeypatch.setattr(llm, "call_structured", fake_call)
    by_id = {a.finding_id: a for a in judge_mod.adjudicate(findings, golden, _dossier())}
    assert by_id["x1"].label == AdjudicationLabel.TP_MATCH and by_id["x1"].matched_golden_id == "G1"
    assert by_id["x2"].label == AdjudicationLabel.TP_NEW and by_id["x2"].matched_golden_id is None
    assert by_id["x3"].label == AdjudicationLabel.FP_GENERIC
    assert by_id["x4"].label == AdjudicationLabel.FP_INCORRECT  # ausente -> prudencia
    assert by_id["x5"].label == AdjudicationLabel.FP_INCORRECT  # ni golden, ni generico, ni real


# --- orquestacion (b0 determinista, juez falso, sin API) ---
def test_run_experiment_b0_es_el_suelo(monkeypatch):
    def fake_judge(findings, golden, dossier):
        return [Adjudication(finding_id=f.id, label=AdjudicationLabel.FP_GENERIC) for f in findings]

    golden = [GoldenIssue(id="G1", description="d")]
    res = runner.run_experiment(
        dossier=_dossier(),
        golden=golden,
        guidelines=list(all_guidelines()),
        approaches=["b0"],
        k=3,
        judge=fake_judge,
    )
    agg = res["_aggregate_objs"]["b0"]
    assert agg.k == 3
    # B0 genera 1 hallazgo por guideline, todos genericos -> gate falla -> primary 0
    assert agg.genericity_rate.mean == pytest.approx(1.0)
    assert agg.primary_score.mean == 0.0
    assert agg.primary_score.std == 0.0  # determinista replicado
