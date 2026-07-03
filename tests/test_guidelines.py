"""Tests for loading and validating the guideline corpora."""

from interaction_review.guidelines import all_guidelines, guidelines_by_id, load_corpus
from interaction_review.schemas import GuidelineCorpus


def test_hax_has_exactly_18():
    hax = load_corpus(GuidelineCorpus.HAX)
    assert len(hax) == 18
    assert {g.id for g in hax} == {f"HAX-G{i}" for i in range(1, 19)}


def test_pair_loads_and_is_nonempty():
    pair = load_corpus(GuidelineCorpus.PAIR)
    assert len(pair) > 0
    assert all(g.corpus is GuidelineCorpus.PAIR for g in pair)


def test_all_ids_unique_across_corpora():
    gls = all_guidelines()
    ids = [g.id for g in gls]
    assert len(ids) == len(set(ids))


def test_every_guideline_has_examples_and_group():
    for g in all_guidelines():
        assert g.title.strip()
        assert g.description.strip()
        assert g.good_example.strip()
        assert g.bad_example.strip()
        assert g.group.strip()


def test_index_roundtrip_and_key_ids_present():
    idx = guidelines_by_id()
    # G9 (correction/override) and FC-2 (control/override) are central to the clinical case.
    assert idx["HAX-G9"].corpus is GuidelineCorpus.HAX
    assert idx["PAIR-FC-2"].corpus is GuidelineCorpus.PAIR
