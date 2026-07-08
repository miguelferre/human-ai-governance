# Inspect AI eval

An [Inspect AI](https://inspect.aisi.org.uk/) port of the HAX/PAIR interaction-layer reviewer. It is a
**bridge**, not a reimplementation: Inspect runs the orchestration and logging; the method (generation,
dedup, the LLM judge, the pre-registered F2 metric) is the project's own. See
[ADR-010](../../docs/adr/ADR-010-inspect-bridge.md).

## Install

```bash
uv sync --extra dev --extra evals
```

## Run

Always pass `--model none`: the solver runs the project's own pipeline and never uses an Inspect model
(an `INSPECT_EVAL_MODEL` in the environment would otherwise leak in). The generator/judge are the
project's own models; pin them with `-T`.

```bash
# Free, deterministic smoke (b0 checklist, no model calls at all):
uv run inspect eval evals/inspect/hax_pair_review.py --model none -T approach=b0 --limit 1

# Real run on a couple of cases (needs ANTHROPIC_API_KEY, or LLM_BACKEND=ollama):
uv run inspect eval evals/inspect/hax_pair_review.py --model none --limit 2 \
  -T gen_model=claude-haiku-4-5-20251001 -T judge_model=<snapshot-date>

# Full corpus, k=3 (epochs == k). ~450-500 model calls; start with --limit:
uv run inspect eval evals/inspect/hax_pair_review.py --model none --epochs 3 \
  -T gen_model=claude-haiku-4-5-20251001 -T judge_model=<snapshot-date>

# Inspect the run: transcript = the real findings report; score metadata = adjudications + models.
uv run inspect view
```

## Task args (`-T`)

| Arg | Default | Meaning |
|---|---|---|
| `approach` | `p3` | Any key in `approaches.REGISTRY` (`b0`, `b1`, `p3`, ...) |
| `dedup` | `true` | Apply the deterministic dedup after generation |
| `gen_model` | (env) | Pin the generator; recorded in the log and in each score's metadata |
| `judge_model` | (env) | Pin the judge; **use a dated snapshot** (the default is a floating alias) |

## What it produces

Per case, a `Score` with `recall`, `precision`, `genericity_rate`, `grounding_rate`, `primary_score`
(F2 subject to the genericity gate), aggregated across cases with `nan_mean` / `nan_stderr`. The control
case `sistema-bueno` (empty golden) emits recall/primary as NaN and is excluded from those aggregates,
so it does not falsely depress recall. Each score's metadata carries the full adjudications,
`recall_by_revealed_by`, and the resolved generator/judge models.

## Important: this is a window, not a re-measurement

The aggregate Inspect reports is **not** the pre-registered product number. The canonical figure
(recall 0.91 +/- 0.055 over the 9 testimony cases) lives in
[docs/RESULTS-testimony.md](../../docs/RESULTS-testimony.md) and does not change. Inspect reduces and
aggregates differently (mean +/- stderr across all cases); treat it as an interoperable view onto the
harness, useful for `inspect view` and for anyone who reads `.eval` logs.
