"""Tests for CLI robustness: input validation and dedup plumbing (no API).

Exercise the deterministic guards added in the audit: unknown corpus, evaluate
without inputs, compare with a non-comparable approach or k<1, and that --dedup is
honored on both the normal and the 'auto' path.
"""

import argparse

import pytest

from interaction_review.cli import _maybe_dedup, _select_guidelines, main
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
    args = argparse.Namespace(dedup=True, dedup_llm=False)
    out = _maybe_dedup([_f("a"), _f("b")], args)  # two near-identical -> merged into one
    assert len(out) == 1


def test_maybe_dedup_noop_when_not_requested():
    args = argparse.Namespace(dedup=False, dedup_llm=False)
    findings = [_f("a"), _f("b")]
    assert _maybe_dedup(findings, args) == findings  # untouched
