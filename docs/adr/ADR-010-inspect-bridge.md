# ADR-010: Inspect AI eval as a bridge (not a reimplementation)

- **Status:** Accepted
- **Date:** 2026-07-08

## Context

The evaluation (LLM judge over golden sets, with pre-registered F2 metrics) is home-grown and lives in
`compare`/`evaluate`. That is fine internally, but it is illegible to the AI-evaluation / assurance
market, which reads **Inspect AI** (the UK AI Security Institute's framework): `.eval` logs, `inspect
view`, the solver/scorer vocabulary. Porting the eval makes the same rigor readable to anyone in that
circuit, and is a credential for evaluation / oversight work. The goal was interoperability **without
reimplementing** (or diluting) the validated method.

## Decision

A bridge in `evals/inspect/hax_pair_review.py`, outside the package:

- **Dataset** = the held-out corpus (`data/external/<case>/{dossier,answer_key}.json`), one `Sample`
  per case, dossier + golden carried in `Sample.metadata`.
- **Solver** = the project's own pipeline: `REGISTRY[approach](dossier, guidelines)` + `deduplicate`.
  It **never calls Inspect's `generate`**; it sets `state.output.completion` to the real Markdown
  report so `inspect view` shows the findings. The task runs with `--model none`.
- **Scorer** = the project's own judge (`judge.adjudicate`, ADR-006 protocol intact) + metrics
  (`metrics.compute_run_metrics`). It emits recall / precision / genericity / grounding / primary as a
  dict-valued `Score`, and stashes the adjudications and resolved model names in `Score.metadata`. It
  does **not** use `model_graded_qa`.
- **k** maps to Inspect's `--epochs`.

Key choices:

- **Location outside the package, no `__init__.py`.** A package importable as `inspect` would shadow
  the stdlib module; the eval lives as a standalone file, loaded by path in tests and by filename on
  the `inspect eval` CLI. `inspect-ai` is an **optional extra** (`[evals]`), not a core dep: the
  product does not need it.
- **NaN-aware aggregation.** The control case `sistema-bueno` has an empty golden, so `compute_run_metrics`
  returns recall `0.0` there; folded into a plain mean it would depress the aggregate. The scorer emits
  recall/primary as **NaN** when there is no golden (and precision/genericity/grounding as NaN when
  there are no findings), and custom `nan_mean`/`nan_stderr` metrics drop the NaNs. Without this the
  eval would publish a **falsely low** recall.
- **Anti-mislabel about the model.** The `.eval` log's model is `none` (explicit, not a fake model);
  `-T gen_model=... -T judge_model=...` set the project's own models and are recorded as task args; the
  scorer also writes the **resolved** `gen_model()`/`judge_model()` into each score's metadata. Always
  run with `--model none` (an `INSPECT_EVAL_MODEL` in the environment would otherwise leak in).

## Consequences

- The harness is readable to the Inspect/AISI circuit without touching the validated engine: generation,
  dedup, the judge and the pre-registered F2-with-genericity-gate are unchanged. The README documents,
  honestly, what the framework gives versus what stays hand-built.
- **The Inspect aggregate is a window, not a re-measurement.** Inspect reduces per case and aggregates
  mean +/- stderr across cases; the canonical product number (recall 0.91 +/- 0.055 over the 9 testimony
  cases, `docs/RESULTS-testimony.md`) is pre-registered and **does not change**. This is stated in the
  README, in `evals/inspect/README.md`, and here to avoid a "two competing numbers" reading.
- **CI** installs the `evals` extra and runs an offline smoke (b0 with `--model none`, plus a
  monkeypatched grounded path); real runs stay manual. Pinned `inspect-ai>=0.3.241,<0.4` (0.3.x moves fast).
- **Risk:** Inspect API churn across 0.3.x; mitigated by the version bound and the CI smoke that breaks
  visibly. **Follow-up:** none required; the bridge is thin by design.
