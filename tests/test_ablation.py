"""Tests for the testimony ablation (ADR-007): control dossier, golden distribution
and recall broken down by `revealed_by`. Hand-computed values."""

import pytest

from interaction_review.ablation import (
    has_voice,
    revealed_by_distribution,
    without_voice,
)
from interaction_review.metrics import recall_by_revealed_by
from interaction_review.schemas import (
    Adjudication,
    AdjudicationLabel,
    Dossier,
    GoldenIssue,
    RevealedBy,
    Source,
    SourceKind,
)


def _dossier() -> Dossier:
    return Dossier(
        system_name="S",
        domain="d",
        sources=[
            Source(id="doc", kind=SourceKind.DOCUMENT, label="ficha", content="x"),
            Source(id="tec", kind=SourceKind.TECHNICIAN, label="tecnico", content="y"),
            Source(id="u1", kind=SourceKind.END_USER, label="usuario 1", content="z"),
            Source(id="u2", kind=SourceKind.END_USER, label="usuario 2", content="w"),
        ],
    )


# --- without_voice / has_voice --------------------------------------------- #
def test_without_voice_removes_only_end_user():
    d = _dossier()
    control = without_voice(d)
    kinds = [s.kind for s in control.sources]
    assert SourceKind.END_USER not in kinds
    assert {s.id for s in control.sources} == {"doc", "tec"}


def test_without_voice_does_not_mutate_original():
    d = _dossier()
    _ = without_voice(d)
    assert len(d.sources) == 4  # the original untouched
    assert has_voice(d)


def test_without_voice_raises_if_nothing_left():
    only_voice = Dossier(
        system_name="S",
        domain="d",
        sources=[Source(id="u", kind=SourceKind.END_USER, label="u", content="c")],
    )
    with pytest.raises(ValueError):
        without_voice(only_voice)


def test_has_voice():
    assert has_voice(_dossier())
    assert not has_voice(without_voice(_dossier()))


# --- revealed_by_distribution ---------------------------------------------- #
def test_distribution_counts_every_bucket():
    golden = [
        GoldenIssue(id="a", description="", revealed_by=RevealedBy.USER_ONLY),
        GoldenIssue(id="b", description="", revealed_by=RevealedBy.BOTH),
        GoldenIssue(id="c", description="", revealed_by=RevealedBy.BOTH),
        GoldenIssue(id="d", description="", revealed_by=RevealedBy.TECH_ONLY),
        GoldenIssue(id="e", description=""),  # default UNKNOWN
    ]
    dist = revealed_by_distribution(golden)
    assert dist[RevealedBy.USER_ONLY] == 1
    assert dist[RevealedBy.BOTH] == 2
    assert dist[RevealedBy.TECH_ONLY] == 1
    assert dist[RevealedBy.UNKNOWN] == 1


def test_default_revealed_by_is_unknown():
    assert GoldenIssue(id="x", description="").revealed_by is RevealedBy.UNKNOWN


# --- recall_by_revealed_by -------------------------------------------------- #
def test_recall_by_revealed_by_splits_correctly():
    # 2 USER_ONLY (u-hit matched, u-miss not), 1 BOTH matched, 1 TECH_ONLY not.
    golden = [
        GoldenIssue(id="u-hit", description="", revealed_by=RevealedBy.USER_ONLY),
        GoldenIssue(id="u-miss", description="", revealed_by=RevealedBy.USER_ONLY),
        GoldenIssue(id="b-hit", description="", revealed_by=RevealedBy.BOTH),
        GoldenIssue(id="t-miss", description="", revealed_by=RevealedBy.TECH_ONLY),
    ]
    adj = [
        Adjudication(finding_id="f1", label=AdjudicationLabel.TP_MATCH, matched_golden_id="u-hit"),
        Adjudication(finding_id="f2", label=AdjudicationLabel.TP_MATCH, matched_golden_id="b-hit"),
        Adjudication(finding_id="f3", label=AdjudicationLabel.TP_NEW),  # does not count toward recall
    ]
    by = {sr.revealed_by: sr for sr in recall_by_revealed_by(adj, golden)}

    assert by[RevealedBy.USER_ONLY].n_golden == 2
    assert by[RevealedBy.USER_ONLY].n_matched == 1
    assert by[RevealedBy.USER_ONLY].recall == 0.5
    assert by[RevealedBy.BOTH].recall == 1.0
    assert by[RevealedBy.TECH_ONLY].recall == 0.0
    # buckets absent from the golden do not appear:
    assert RevealedBy.UNKNOWN not in by


def test_recall_by_revealed_by_ignores_empty_buckets():
    golden = [GoldenIssue(id="g", description="", revealed_by=RevealedBy.USER_ONLY)]
    out = recall_by_revealed_by([], golden)
    assert len(out) == 1
    assert out[0].revealed_by is RevealedBy.USER_ONLY
    assert out[0].recall == 0.0
