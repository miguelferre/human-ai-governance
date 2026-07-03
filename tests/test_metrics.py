"""Tests for metrics with hand-computed values (synthetic toy golden)."""

import pytest

from interaction_review.metrics import (
    BETA,
    GENERICITY_THRESHOLD,
    AggregateMetrics,
    RunMetrics,
    Stat,
    aggregate,
    beats,
    compute_run_metrics,
    f_beta,
)
from interaction_review.schemas import (
    Adjudication,
    AdjudicationLabel,
    Finding,
    GoldenIssue,
)


def _grounded(fid: str) -> Finding:
    return Finding(id=fid, title=fid, guideline_ids=["HAX-G1"], locus="x", evidence="y")


def _bare(fid: str) -> Finding:
    return Finding(id=fid, title=fid)


def _golden() -> list[GoldenIssue]:
    return [GoldenIssue(id=f"G{i}", description=f"issue {i}") for i in (1, 2, 3)]


def _scenario():
    # f1,f2 -> TP_MATCH (G1,G2); f3 -> TP_NEW; f4 -> FP_GENERIC; f5 -> FP_INCORRECT
    findings = [_grounded("f1"), _grounded("f2"), _grounded("f3"), _bare("f4"), _bare("f5")]
    adj = [
        Adjudication(finding_id="f1", label=AdjudicationLabel.TP_MATCH, matched_golden_id="G1"),
        Adjudication(finding_id="f2", label=AdjudicationLabel.TP_MATCH, matched_golden_id="G2"),
        Adjudication(finding_id="f3", label=AdjudicationLabel.TP_NEW),
        Adjudication(finding_id="f4", label=AdjudicationLabel.FP_GENERIC),
        Adjudication(finding_id="f5", label=AdjudicationLabel.FP_INCORRECT),
    ]
    return findings, adj, _golden()


def test_pre_registered_params_are_fixed():
    # If this changes, it requires a new ADR (ADR-002).
    assert BETA == 2.0
    assert GENERICITY_THRESHOLD == 0.25


def test_run_metrics_hand_computed():
    findings, adj, golden = _scenario()
    m = compute_run_metrics("test", findings, adj, golden)
    assert m.recall == pytest.approx(2 / 3)
    assert m.precision == pytest.approx(3 / 5)
    assert m.genericity_rate == pytest.approx(1 / 5)
    assert m.grounding_rate == pytest.approx(3 / 5)
    assert m.tp_new == 1
    assert m.fbeta == pytest.approx(f_beta(3 / 5, 2 / 3))
    assert m.meets_genericity_gate is True
    assert m.primary_score == pytest.approx(m.fbeta)


def test_genericity_gate_zeroes_primary_score():
    # 2 of 3 findings generic -> genericity 0.667 > 0.25 -> primary = 0
    findings = [_bare("f1"), _bare("f2"), _grounded("f3")]
    adj = [
        Adjudication(finding_id="f1", label=AdjudicationLabel.FP_GENERIC),
        Adjudication(finding_id="f2", label=AdjudicationLabel.FP_GENERIC),
        Adjudication(finding_id="f3", label=AdjudicationLabel.TP_MATCH, matched_golden_id="G1"),
    ]
    m = compute_run_metrics("test", findings, adj, _golden())
    assert m.genericity_rate > GENERICITY_THRESHOLD
    assert m.meets_genericity_gate is False
    assert m.primary_score == 0.0


def test_empty_findings_do_not_crash():
    m = compute_run_metrics("empty", [], [], _golden())
    assert m.n_findings == 0
    assert m.precision == 0.0
    assert m.grounding_rate == 0.0
    assert m.primary_score == 0.0


def test_mismatched_adjudications_raise():
    # Adjudications from ANOTHER run against these findings must NOT silently produce
    # precision > 1 (was: 5 adjudications / 1 finding -> precision 5.0).
    findings = [_grounded("f1")]
    alien = [
        Adjudication(finding_id=f"z{i}", label=AdjudicationLabel.TP_NEW) for i in range(5)
    ]
    with pytest.raises(ValueError):
        compute_run_metrics("p3", findings, alien, _golden())


def test_duplicate_adjudication_raises():
    findings = [_grounded("f1")]
    dup = [
        Adjudication(finding_id="f1", label=AdjudicationLabel.TP_NEW),
        Adjudication(finding_id="f1", label=AdjudicationLabel.TP_MATCH, matched_golden_id="G1"),
    ]
    with pytest.raises(ValueError):
        compute_run_metrics("p3", findings, dup, _golden())


def test_f_beta_zero_when_no_signal():
    assert f_beta(0.0, 0.0) == 0.0


def test_aggregate_mean_and_std():
    findings, adj, golden = _scenario()
    runs = [compute_run_metrics("test", findings, adj, golden) for _ in range(3)]
    agg = aggregate(runs)
    assert agg.k == 3
    assert agg.recall.mean == pytest.approx(2 / 3)
    assert agg.recall.std == pytest.approx(0.0)  # deterministic here


def test_aggregate_rejects_mixed_approaches():
    findings, adj, golden = _scenario()
    a = compute_run_metrics("a", findings, adj, golden)
    b = compute_run_metrics("b", findings, adj, golden)
    with pytest.raises(ValueError):
        aggregate([a, b])


def _agg(name: str, scores: list[float]) -> AggregateMetrics:
    runs = [
        RunMetrics(
            approach=name, n_findings=0, n_golden=3, recall=0, precision=0,
            genericity_rate=0, grounding_rate=0, tp_new=0, fbeta=0,
            meets_genericity_gate=True, primary_score=s,
        )
        for s in scores
    ]
    return aggregate(runs)


def test_beats_requires_margin_above_noise():
    # margin 0.2 >> noise (0.05 + 0) -> wins
    assert beats(_agg("cand", [0.75, 0.85]), _agg("base", [0.6, 0.6])) is True
    # margin 0.02 < combined noise 0.10 -> does NOT win
    assert beats(_agg("cand", [0.57, 0.67]), _agg("base", [0.55, 0.65])) is False
