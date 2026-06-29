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
def _grounded(fid: str) -> Finding:
    return Finding(id=fid, title=fid, guideline_ids=["HAX-G1"], locus="x", evidence="y")


def test_adjudicate_deriva_etiqueta_de_candidatos(monkeypatch):
    # x1..x4 anclados; x6 SIN anclaje (locus/evidencia vacios).
    findings = [_grounded(f"x{i}") for i in (1, 2, 3, 4)] + [
        Finding(id="x6", title="x6", guideline_ids=["HAX-G1"])
    ]
    golden = [GoldenIssue(id="G1", description="d")]  # candidato (fallback) para los anclados

    def fake_call(**kwargs):
        # El modelo solo confirma candidato; la etiqueta se deriva en codigo.
        return {
            "adjudications": [
                {"finding_id": "x1", "judge_rationale": "ok", "corresponde_a_candidato": "G1", "es_real": True},
                # candidato inexistente -> no es match; es_real True -> tp_new
                {"finding_id": "x2", "judge_rationale": "x", "corresponde_a_candidato": "NOPE", "es_real": True},
                {"finding_id": "x3", "judge_rationale": "x", "corresponde_a_candidato": "ninguno", "es_real": False},
                # x4 ausente a proposito -> fp_incorrect
                # x6: el juez intenta emparejarlo, pero NO esta anclado -> el gate fuerza fp_generic
                {"finding_id": "x6", "judge_rationale": "x", "corresponde_a_candidato": "G1", "es_real": True},
            ]
        }

    monkeypatch.setattr(llm, "call_structured", fake_call)
    by_id = {a.finding_id: a for a in judge_mod.adjudicate(findings, golden, _dossier())}
    assert by_id["x1"].label == AdjudicationLabel.TP_MATCH and by_id["x1"].matched_golden_id == "G1"
    assert by_id["x2"].label == AdjudicationLabel.TP_NEW and by_id["x2"].matched_golden_id is None
    assert by_id["x3"].label == AdjudicationLabel.FP_INCORRECT  # ninguno + no real
    assert by_id["x4"].label == AdjudicationLabel.FP_INCORRECT  # ausente -> prudencia
    # gate estructural: sin anclaje es fp_generic AUNQUE el juez diga que corresponde a G1
    assert by_id["x6"].label == AdjudicationLabel.FP_GENERIC and by_id["x6"].matched_golden_id is None


# --- orquestacion (b0 determinista, juez falso, sin API) ---
def test_generate_robusto_ante_estructura_mala(monkeypatch):
    # El tool-use de Anthropic puede devolver items que no son objeto -> deben ignorarse.
    from interaction_review.approaches import _generator

    bad = {"findings": ["basura-string", {"title": "t", "guideline_ids": ["HAX-G1"], "locus": "x",
                                          "evidence": "y", "severity": "low", "rationale": "r", "recommendation": "z"}]}
    monkeypatch.setattr(_generator.llm, "call_structured", lambda **k: bad)
    out = _generator.generate(_dossier(), list(all_guidelines()), few_shot=False, label="t")
    assert len(out) == 1 and out[0].is_grounded()  # solo el item-objeto sobrevive


def test_p3_buckets_cubren_todas_las_guidelines():
    from interaction_review.approaches.p3_pipeline import BUCKETS

    cubiertos = {gid for ids in BUCKETS.values() for gid in ids}
    todas = {g.id for g in all_guidelines()}
    assert cubiertos == todas  # sin omisiones ni ids inventados


def test_p3_run_reid_unico(monkeypatch):
    from interaction_review.approaches import p3_pipeline

    def fake_generate(dossier, gl, *, few_shot, label):
        return [Finding(id=f"{label}-001", title=label, guideline_ids=[gl[0].id], locus="x", evidence="y")]

    monkeypatch.setattr(p3_pipeline, "generate", fake_generate)
    out = p3_pipeline.run(_dossier(), list(all_guidelines()))
    ids = [f.id for f in out]
    assert len(ids) == len(set(ids)) == len(p3_pipeline.BUCKETS)  # un hallazgo por bloque, ids unicos
    assert ids[0] == "p3-001"


def test_a4_para_cuando_no_hay_gaps(monkeypatch):
    from interaction_review.approaches import a4_agent

    monkeypatch.setattr(
        a4_agent, "generate",
        lambda d, gl, *, few_shot, label: [_grounded(f"{label}")],
    )
    monkeypatch.setattr(a4_agent, "_assess_gaps", lambda guidelines, findings: {"seguir": False, "guideline_ids": []})
    out = a4_agent.run(_dossier(), list(all_guidelines()))
    assert len(out) == 1 and out[0].id == "a4-001"  # solo la pasada inicial


def test_a4_acota_iteraciones(monkeypatch):
    from interaction_review.approaches import a4_agent

    monkeypatch.setattr(
        a4_agent, "generate",
        lambda d, gl, *, few_shot, label: [_grounded(f"{label}")],
    )
    # el modelo SIEMPRE quiere seguir -> el tope MAX_ITERS debe acotar (anti-loop)
    monkeypatch.setattr(a4_agent, "_assess_gaps", lambda guidelines, findings: {"seguir": True, "guideline_ids": ["HAX-G1"]})
    out = a4_agent.run(_dossier(), list(all_guidelines()))
    assert len(out) == a4_agent.MAX_ITERS
    assert len({f.id for f in out}) == len(out)  # ids unicos


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
