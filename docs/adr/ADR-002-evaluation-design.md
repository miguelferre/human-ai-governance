# ADR-002: Evaluation design and primary metric (pre-registered)

- **Status:** Accepted
- **Date:** 2026-06-27

## Context

"Working" has to be measurable, not an intuition. There is a real clinical case
with interaction problems already identified by the user: it is a **golden set**
with known answers. The question is whether the system rediscovers them on its own,
without seeing them, and without spitting out generic output.

## Decision

### Golden set and blind execution
- The answer key (a frozen list of `GoldenIssue`) lives under `data/golden/`
  (gitignored). The system does **not** see it. It receives only the `Dossier`.

### Adjudication
- An **LLM-judge** (different model/prompt from the generator) labels each finding:
  `TP_MATCH` / `TP_NEW` / `FP_GENERIC` / `FP_INCORRECT`.
- The **human reviews and corrects** (`human_confirmed`). The final gold is human.

### Metrics (implemented in `metrics.py`)
- recall, precision, genericity_rate, grounding_rate, tp_new.
- Each approach is run **k >= 3** times; mean +/- standard deviation is reported.

### Primary metric (PRE-REGISTERED, before seeing results)
- `primary_score` = **F-beta with beta = 2.0** (prioritizes recall: in an audit,
  failing to detect a real problem is worse than a FP that is cheap to discard),
  **subject to** `genericity_rate <= 0.25`. If it does not pass that ceiling,
  `primary_score = 0`.
- These values are fixed in code (`metrics.BETA`, `metrics.GENERICITY_THRESHOLD`)
  so they are not rationalized after the fact. Changing them requires a new ADR.

### Decision rule between rungs
- `metrics.beats(candidate, baseline)`: the candidate wins if the mean of its
  primary_score exceeds the baseline's by more than the sum of their standard
  deviations (margin > noise).

## Consequences and assumed limits

- **n = 1 golden case** -> **formative** evaluation, not a benchmark. The second case
  (climate) is a **partial held-out test**: it is not used to tune prompts.
- **Overfitting**: all tuning is done looking only at the clinical case; assumed risk.
- A generic finding counts as a **failure**, by metric design.
