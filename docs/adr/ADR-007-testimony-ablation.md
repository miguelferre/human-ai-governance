# ADR-007: Ablation of the user's testimony (`revealed_by` field)

- **Status:** Accepted
- **Date:** 2026-07-01

## Context

The reviewer's commercial differentiator (see docs/PRODUCT.md and the go-to-market) is
incorporating the **end user's testimony**, not just auditing the design in the
abstract. But it is a promise **not yet demonstrated**: control C3 (docs/RESULTS.md)
showed that, in **global** recall, the dossier with voice and without voice perform
almost the same (P3 0.78 = 0.78). That does not refute the promise (the value of the
testimony could lie in a small subset of problems that *only* the voice reveals, or in
the grounding/credibility of the findings), but it does require measuring it in a
targeted way instead of asserting it.

The measurement problem: global recall mixes issues that any source reveals with those
that depend on the testimony. To isolate the contribution of the voice, one needs to
know, **for each GoldenIssue, from what type of source it is detectable**.

## Decision

1. **`revealed_by` field in `GoldenIssue`** (enum `RevealedBy`), hand-labeled over the real
   content of the dossier's sources:
   - `USER_ONLY`: only identifiable from an end user's testimony (`END_USER`). Without that
     voice, the problem is invisible in the dossier.
   - `TECH_ONLY`: only from documentation or technical profile (`DOCUMENT` / `TECHNICIAN`).
   - `BOTH`: the documentation describes it **and** the user experiences/confirms it.
   - `UNKNOWN`: unlabeled (default), does not take part in the ablation. It keeps the previous
     golden (EII, held-out without voice) compatible without touching them.

   **Labeling criterion:** for each issue, in which sources is there evidence that supports it?
   Only in `END_USER` -> `USER_ONLY`; only in `DOCUMENT`/`TECHNICIAN` -> `TECH_ONLY`; in both
   -> `BOTH`. It is decided by reading the sources, not by the cited guideline.

2. **"Without voice" control condition** (`ablation.without_voice`): the same dossier with the
   `END_USER` sources removed. Deterministic, offline, does not mutate the original.

3. **Metric** (`metrics.recall_by_revealed_by`): recall broken down by `revealed_by` subset.
   The comparison that matters is the recall of `USER_ONLY` **with voice vs without voice**.

## How the result is read (pre-registered, before the run)

- **The promise holds** if the recall of `USER_ONLY` is high with voice and **collapses**
  without voice (the reviewer stops seeing those problems when you take the testimony away).
- **The promise weakens to "grounding, not discovery"** if the recall of `USER_ONLY` does not
  drop appreciably without voice (the reviewer infers them the same from the documentation; the
  testimony adds evidence and credibility, not new findings). This would be consistent with C3.
- **Prior ceiling, free:** `ablation.revealed_by_distribution` counts the golden's `USER_ONLY`
  **without spending API**. If they are very few, the maximum possible contribution to recall is
  already low before running anything, an honest result in itself.

## Consequences

- Labeling is **human judgment** and goes in the answer key (outside the blind dossier; the
  reviewer does not see it). A labeling biased toward `USER_ONLY` would inflate the testimony's
  contribution -> the evidence per issue is documented and remains reviewable.
- The field is additive and defaults to `UNKNOWN`: it does not change any existing metric or
  break previous golden. The ablation is a separate analysis, not a change to the main experiment.
- The final run (recall with voice vs without voice) needs the LLM (`compare` flow over the
  full dossier and over `without_voice`); the scaffolding (field, control, metric, offline
  count) does not.
