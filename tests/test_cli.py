"""Tests for CLI robustness: input validation and dedup plumbing (no API).

Exercise the deterministic guards added in the audit: unknown corpus, evaluate
without inputs, compare with a non-comparable approach or k<1, and that --dedup is
honored on both the normal and the 'auto' path.
"""

import json

import pytest

from interaction_review.cli import _maybe_dedup, _select_guidelines, build_parser, main
from interaction_review.schemas import Finding

DEMO = "data/examples/dossier_demo.json"
GOLDEN = "data/external/epic-sepsis/answer_key.json"


# --- corpus validation ------------------------------------------------------ #
def test_select_guidelines_unknown_corpus_exits():
    with pytest.raises(SystemExit):
        _select_guidelines("foo")


def test_select_guidelines_valid_subset():
    hax = _select_guidelines("hax")
    assert hax and all(g.corpus.value == "HAX" for g in hax)


# --- evaluate needs at least one input -------------------------------------- #
def test_evaluate_without_findings_or_dossier_returns_2(capsys):
    rc = main(["evaluate", "--golden", GOLDEN])
    assert rc == 2
    assert "findings" in capsys.readouterr().err.lower()


# --- compare rejects the review-only router and k<1 cleanly ----------------- #
def test_compare_auto_is_rejected_cleanly(capsys):
    rc = main(["compare", "--dossier", DEMO, "--golden", GOLDEN, "--approaches", "auto"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "auto" in err and "router" in err  # no traceback, explains why


def test_compare_k_zero_rejected(capsys):
    rc = main(["compare", "--dossier", DEMO, "--golden", GOLDEN, "--approaches", "b0", "--k", "0"])
    assert rc == 2
    assert "k" in capsys.readouterr().err.lower()


# --- --dedup honored on both paths ------------------------------------------ #
def _f(fid: str) -> Finding:
    return Finding(
        id=fid, title="onboarding sin reciclaje periodico",
        locus="formacion a los medicos del piloto", guideline_ids=["HAX-G1"], evidence="e",
    )


def test_maybe_dedup_applies_when_requested():
    out = _maybe_dedup([_f("a"), _f("b")], dedup=True, dedup_llm=False)  # near-identical -> one
    assert len(out) == 1


def test_maybe_dedup_noop_when_not_requested():
    findings = [_f("a"), _f("b")]
    assert _maybe_dedup(findings, dedup=False, dedup_llm=False) == findings  # untouched


# --- product default: p3 with dedup on ------------------------------------- #
def test_review_default_approach_is_p3_with_dedup():
    args = build_parser().parse_args(["review", "--dossier", DEMO])
    assert args.approach == "p3"       # the product, not the b0 checklist floor
    assert args.no_dedup is False      # dedup on by default for p3


# --- review report carries provenance (offline, b0) ------------------------- #
def test_review_report_has_provenance(tmp_path, capsys):
    out = tmp_path / "r.md"
    rc = main(["review", "--dossier", DEMO, "--approach", "b0", "--out", str(out)])
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "Generated:" in text and "Tool version:" in text
    assert "deterministic" in text  # b0 uses no model


# --- evaluate --run closes the compare -> evaluate loop --------------------- #
def _run_json(tmp_path, *, adjudications):
    data = {
        "config": {"approaches": ["p3"], "k": 1},
        "runs": {
            "p3": [{
                "findings": [{
                    "id": "p3-001", "title": "t", "guideline_ids": ["HAX-G1"],
                    "locus": "x", "evidence": "y", "severity": "medium",
                }],
                "adjudications": adjudications,
                "metrics": {},
            }],
        },
    }
    p = tmp_path / "run.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def test_evaluate_from_run(tmp_path, capsys):
    run = _run_json(tmp_path, adjudications=[
        {"finding_id": "p3-001", "label": "tp_match", "matched_golden_id": "E-01"},
    ])
    rc = main(["evaluate", "--run", run, "--approach", "p3", "--golden", GOLDEN])
    assert rc == 0
    assert "p3" in capsys.readouterr().out  # metrics table emitted


def test_evaluate_from_run_unknown_approach(tmp_path, capsys):
    run = _run_json(tmp_path, adjudications=[{"finding_id": "p3-001", "label": "tp_new"}])
    rc = main(["evaluate", "--run", run, "--approach", "b1", "--golden", GOLDEN])
    assert rc == 2
    assert "no runs for approach" in capsys.readouterr().err


def test_evaluate_from_run_idx_out_of_range(tmp_path, capsys):
    run = _run_json(tmp_path, adjudications=[{"finding_id": "p3-001", "label": "tp_new"}])
    rc = main(["evaluate", "--run", run, "--approach", "p3", "--idx", "9", "--golden", GOLDEN])
    assert rc == 2
    assert "out of range" in capsys.readouterr().err
