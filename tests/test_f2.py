"""Tests for F2 without touching the API: prompts, parsing, judge logic and orchestration.

The real LLM calls are monkeypatched. What is tested is the deterministic logic
around them (grounding, label coherence, aggregation).
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
    # the guideline catalog and the dossier are in the prompt
    assert "HAX-G9" in zero and "Sistema X" in zero


def test_generator_system_prohibe_genericos():
    assert "PROHIBIDO" in prompts.GENERATOR_SYSTEM
    assert prompts.FINDINGS_TOOL["name"] == "report_findings"


# --- finding parsing ---
def test_to_finding_normaliza_y_calcula_anclaje():
    raw = {
        "title": "t",
        "guideline_ids": ["HAX-G9", ""],
        "locus": "el boton de override",
        "evidence": "'solo se pide el motivo al discrepar'",
        "severity": "altisima",  # invalid -> medium
        "rationale": "r",
        "recommendation": "rec",
    }
    f = _to_finding("b1", 3, raw)
    assert f.id == "b1-003"
    assert f.guideline_ids == ["HAX-G9"]  # filters out empties
    assert f.severity.value == "medium"
    assert f.is_grounded() is True


def test_to_finding_sin_anclaje_no_grounded():
    f = _to_finding("b1", 1, {"title": "generico", "guideline_ids": [], "severity": "low"})
    assert not f.is_grounded()


# --- judge candidates (measurement debt: TESTPLAN B2) ---
def test_candidates_incluye_todos_los_golden_probables_primero():
    f = Finding(id="f1", title="t", guideline_ids=["HAX-G9"], locus="x", evidence="y")
    comparte = GoldenIssue(id="G-comparte", description="d", guideline_ids=["HAX-G9"])
    # Golden tagged with ANOTHER guideline (another corpus): before it was EXCLUDED -> false miss.
    distinto = GoldenIssue(id="G-distinto", description="d", guideline_ids=["PAIR-ET-2"])
    cands = judge_mod._candidates(f, [distinto, comparte])
    ids = [g.id for g in cands]
    assert set(ids) == {"G-comparte", "G-distinto"}  # the non-sharing one is NO longer excluded
    assert ids[0] == "G-comparte"  # the one sharing a guideline goes first (hint to the judge)


def test_candidates_recupera_match_con_guideline_distinta(monkeypatch):
    # The finding cites HAX-G9 but the real problem is the golden tagged with PAIR-ET-2.
    # With the old filter it was not a candidate; now it is, and the judge can match it.
    f = Finding(id="f1", title="t", guideline_ids=["HAX-G9"], locus="x", evidence="y")
    golden = [GoldenIssue(id="G-PAIR", description="mismo problema", guideline_ids=["PAIR-ET-2"])]

    def fake_call(**kwargs):
        return {"adjudications": [
            {"finding_id": "f1", "judge_rationale": "es el mismo", "corresponde_a_candidato": "G-PAIR", "es_real": True}
        ]}

    monkeypatch.setattr(llm, "call_structured", fake_call)
    adj = judge_mod.adjudicate([f], golden, _dossier())[0]
    assert adj.label == AdjudicationLabel.TP_MATCH and adj.matched_golden_id == "G-PAIR"


# --- judge logic (LLM monkeypatched) ---
def _grounded(fid: str) -> Finding:
    return Finding(id=fid, title=fid, guideline_ids=["HAX-G1"], locus="x", evidence="y")


def test_adjudicate_rejects_duplicate_ids():
    # raw/candidate maps are keyed by finding id; colliding ids would silently drop findings.
    findings = [_grounded("dup"), _grounded("dup")]
    with pytest.raises(ValueError):
        judge_mod.adjudicate(findings, [GoldenIssue(id="G1", description="d")], _dossier())


def test_adjudicate_deriva_etiqueta_de_candidatos(monkeypatch):
    # x1..x4 grounded; x6 NOT grounded (empty locus/evidence).
    findings = [_grounded(f"x{i}") for i in (1, 2, 3, 4)] + [
        Finding(id="x6", title="x6", guideline_ids=["HAX-G1"])
    ]
    golden = [GoldenIssue(id="G1", description="d")]  # candidate (fallback) for the grounded ones

    def fake_call(**kwargs):
        # The model only confirms a candidate; the label is derived in code.
        return {
            "adjudications": [
                {"finding_id": "x1", "judge_rationale": "ok", "corresponde_a_candidato": "G1", "es_real": True},
                # nonexistent candidate -> not a match; es_real True -> tp_new
                {"finding_id": "x2", "judge_rationale": "x", "corresponde_a_candidato": "NOPE", "es_real": True},
                {"finding_id": "x3", "judge_rationale": "x", "corresponde_a_candidato": "ninguno", "es_real": False},
                # x4 absent on purpose -> fp_incorrect
                # x6: the judge tries to match it, but it is NOT grounded -> the gate forces fp_generic
                {"finding_id": "x6", "judge_rationale": "x", "corresponde_a_candidato": "G1", "es_real": True},
            ]
        }

    monkeypatch.setattr(llm, "call_structured", fake_call)
    by_id = {a.finding_id: a for a in judge_mod.adjudicate(findings, golden, _dossier())}
    assert by_id["x1"].label == AdjudicationLabel.TP_MATCH and by_id["x1"].matched_golden_id == "G1"
    assert by_id["x2"].label == AdjudicationLabel.TP_NEW and by_id["x2"].matched_golden_id is None
    assert by_id["x3"].label == AdjudicationLabel.FP_INCORRECT  # none + not real
    assert by_id["x4"].label == AdjudicationLabel.FP_INCORRECT  # absent -> caution
    # structural gate: without grounding it is fp_generic EVEN IF the judge says it matches G1
    assert by_id["x6"].label == AdjudicationLabel.FP_GENERIC and by_id["x6"].matched_golden_id is None


# --- orchestration (deterministic b0, fake judge, no API) ---
def test_generate_robusto_ante_estructura_mala(monkeypatch):
    # Anthropic tool-use may return items that are not objects -> they must be ignored.
    from interaction_review.approaches import _generator

    bad = {"findings": ["basura-string", {"title": "t", "guideline_ids": ["HAX-G1"], "locus": "x",
                                          "evidence": "y", "severity": "low", "rationale": "r", "recommendation": "z"}]}
    monkeypatch.setattr(_generator.llm, "call_structured", lambda **k: bad)
    out = _generator.generate(_dossier(), list(all_guidelines()), few_shot=False, label="t")
    assert len(out) == 1 and out[0].is_grounded()  # only the object item survives


def test_p3_buckets_cubren_todas_las_guidelines():
    from interaction_review.approaches.p3_pipeline import BUCKETS

    cubiertos = {gid for ids in BUCKETS.values() for gid in ids}
    todas = {g.id for g in all_guidelines()}
    assert cubiertos == todas  # no omissions or invented ids


def test_p3_run_reid_unico(monkeypatch):
    from interaction_review.approaches import p3_pipeline

    def fake_generate(dossier, gl, *, few_shot, label):
        return [Finding(id=f"{label}-001", title=label, guideline_ids=[gl[0].id], locus="x", evidence="y")]

    monkeypatch.setattr(p3_pipeline, "generate", fake_generate)
    out = p3_pipeline.run(_dossier(), list(all_guidelines()))
    ids = [f.id for f in out]
    assert len(ids) == len(set(ids)) == len(p3_pipeline.BUCKETS)  # one finding per block, unique ids
    assert ids[0] == "p3-001"


def test_a4_para_cuando_no_hay_gaps(monkeypatch):
    from interaction_review.approaches import a4_agent

    monkeypatch.setattr(
        a4_agent, "generate",
        lambda d, gl, *, few_shot, label: [_grounded(f"{label}")],
    )
    monkeypatch.setattr(a4_agent, "_assess_gaps", lambda guidelines, findings: {"seguir": False, "guideline_ids": []})
    out = a4_agent.run(_dossier(), list(all_guidelines()))
    assert len(out) == 1 and out[0].id == "a4-001"  # only the initial pass


def test_a4_handles_null_guideline_ids(monkeypatch):
    # The model may return guideline_ids: null (not a list). Must not crash on `for i in None`.
    from interaction_review.approaches import a4_agent

    monkeypatch.setattr(a4_agent, "generate", lambda d, gl, *, few_shot, label: [_grounded(label)])
    monkeypatch.setattr(a4_agent, "_assess_gaps", lambda g, f: {"seguir": True, "guideline_ids": None})
    out = a4_agent.run(_dossier(), list(all_guidelines()))
    assert len(out) == 1 and out[0].id == "a4-001"  # no valid ids -> stops after the initial pass


def test_a4_acota_iteraciones(monkeypatch):
    from interaction_review.approaches import a4_agent

    monkeypatch.setattr(
        a4_agent, "generate",
        lambda d, gl, *, few_shot, label: [_grounded(f"{label}")],
    )
    # the model ALWAYS wants to continue -> the MAX_ITERS cap must bound it (anti-loop)
    monkeypatch.setattr(a4_agent, "_assess_gaps", lambda guidelines, findings: {"seguir": True, "guideline_ids": ["HAX-G1"]})
    out = a4_agent.run(_dossier(), list(all_guidelines()))
    assert len(out) == a4_agent.MAX_ITERS
    assert len({f.id for f in out}) == len(out)  # unique ids


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
    # B0 generates 1 finding per guideline, all generic -> gate fails -> primary 0
    assert agg.genericity_rate.mean == pytest.approx(1.0)
    assert agg.primary_score.mean == 0.0
    assert agg.primary_score.std == 0.0  # deterministic, replicated


def test_checkpoint_not_self_overwritten_without_json_suffix(tmp_path):
    # If save_path does not end in .json, the .gen checkpoint must still be a SEPARATE
    # file (was: str.replace left gen_path == save_path -> final overwrote the checkpoint).
    import json

    def fake_judge(findings, golden, dossier):
        return [Adjudication(finding_id=f.id, label=AdjudicationLabel.FP_GENERIC) for f in findings]

    save = tmp_path / "out.data"  # deliberately NOT .json
    runner.run_experiment(
        dossier=_dossier(),
        golden=[GoldenIssue(id="G1", description="d")],
        guidelines=list(all_guidelines()),
        approaches=["b0"],
        k=1,
        judge=fake_judge,
        save_path=str(save),
    )
    gen = tmp_path / "out.gen.json"
    assert gen.exists() and save.exists()
    # checkpoint = pre-judge snapshot (no adjudications); final file has them
    assert json.loads(gen.read_text(encoding="utf-8"))["runs"]["b0"][0]["adjudications"] == []
    assert json.loads(save.read_text(encoding="utf-8"))["runs"]["b0"][0]["adjudications"]
