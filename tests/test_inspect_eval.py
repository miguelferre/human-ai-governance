"""Offline smoke of the Inspect AI bridge (evals/inspect/hax_pair_review.py).

Skipped if inspect-ai is not installed (the `evals` extra). The eval module is loaded by PATH, not
imported as a package, so a package literally named `inspect` never shadows the stdlib. The b0 path
is fully deterministic and calls no model (`--model none`); the grounded path is exercised with the
LLM monkeypatched, like the rest of the suite.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest

pytest.importorskip("inspect_ai")
from inspect_ai import eval as ia_eval  # noqa: E402

from interaction_review import llm  # noqa: E402

_MODULE_PATH = Path(__file__).resolve().parents[1] / "evals" / "inspect" / "hax_pair_review.py"


def _load_eval_module():
    spec = importlib.util.spec_from_file_location("hax_pair_review_eval", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_MOD = _load_eval_module()
_METRIC_KEYS = {"recall", "precision", "genericity_rate", "grounding_rate", "primary_score"}


def test_dataset_shapes():
    ds = _MOD.load_external_cases()
    assert len(ds) >= 16
    ids = [s.id for s in ds]
    assert len(ids) == len(set(ids)), "sample ids must be unique"
    assert "google-flood-hub" in ids
    for s in ds:
        assert "dossier" in s.metadata and "golden" in s.metadata


@pytest.fixture(scope="module")
def b0_log(tmp_path_factory):
    log_dir = tmp_path_factory.mktemp("eval_b0")
    return ia_eval(
        _MOD.hax_pair_review(approach="b0"),
        model="none",
        display="none",
        log_dir=str(log_dir),
    )[0]


def test_eval_runs_and_reports_all_metrics(b0_log):
    assert b0_log.status == "success"
    names = {s.name for s in b0_log.results.scores}
    assert _METRIC_KEYS <= names
    recall = next(s for s in b0_log.results.scores if s.name == "recall")
    assert {"nan_mean", "nan_stderr"} <= set(recall.metrics)


def test_control_case_excluded_from_recall(b0_log):
    # `sistema-bueno` has an empty golden -> recall undefined (NaN, serialized to None in the log).
    ctrl = next(s for s in b0_log.samples if s.id == "sistema-bueno").scores["review_scorer"]
    assert ctrl.metadata["run_metrics"]["n_golden"] == 0
    r = ctrl.value["recall"]
    assert r is None or (isinstance(r, float) and math.isnan(r))
    # ...and that undefined value does not poison the aggregate.
    recall = next(s for s in b0_log.results.scores if s.name == "recall")
    assert not math.isnan(recall.metrics["nan_mean"].value)


def test_score_metadata_records_resolved_models(b0_log):
    s0 = b0_log.samples[0].scores["review_scorer"]
    # The models are recorded resolved (not "none"): anti-mislabel about who generated/judged.
    assert s0.metadata["gen_model"] and s0.metadata["judge_model"]
    assert "adjudications" in s0.metadata and "recall_by_revealed_by" in s0.metadata


def test_grounded_path_exercises_generator_and_judge(monkeypatch, tmp_path):
    # The generator produces one grounded finding; the judge is invoked (returns nothing confirmed,
    # so the finding is labeled fp_incorrect). Proves the LLM path is wired through Inspect.
    def fake(**kwargs):
        name = kwargs.get("tool", {}).get("name")
        if name == "report_findings":
            return {
                "findings": [
                    {
                        "title": "Score shown without an uncertainty band",
                        "guideline_ids": ["HAX-G2"],
                        "locus": "main screen",
                        "evidence": "a bare number",
                        "severity": "high",
                        "rationale": "r",
                        "recommendation": "z",
                    }
                ]
            }
        if name == "report_adjudications":
            return {"adjudications": []}
        return {}

    monkeypatch.setattr(llm, "call_structured", fake)
    log = ia_eval(
        _MOD.hax_pair_review(approach="b1"),
        model="none",
        limit=1,
        display="none",
        log_dir=str(tmp_path),
    )[0]
    assert log.status == "success"
    meta = log.samples[0].scores["review_scorer"].metadata
    assert meta["run_metrics"]["n_findings"] >= 1
    assert meta["adjudications"], "the judge should have produced adjudication records"
