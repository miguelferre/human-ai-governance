# ADR-006: The judge offers all golden (retire the weak-model crutch)

- **Status:** Accepted
- **Date:** 2026-06-30

## Context

The LLM-judge pre-filtered the golden candidates down to those sharing the **exact**
guideline with the finding (see ADR-004: reduce the local 14B judge's task from "scan
all 15" to "confirm one of these 1-3"). That filter caused **false failures**: a
finding that cited the "wrong" guideline (another phase, or another corpus) did not
have the correct golden among its candidates and could not be matched (a measurement
debt uncovered by human adjudication, TESTPLAN B2). The "shortlist" was a crutch for
the weak local model; after the switch to cloud (ADR-004 addendum) the judge is Sonnet,
**strong**, and can scan all 15.

## Decision

`judge._candidates` offers **all** the golden as candidates, with those sharing
guideline/group (HAX phase / PAIR chapter) **first** as a hint (marked `[*]` in the
prompt) and the rest ordered by text similarity. The strong judge decides over the
complete set.

Calibration ruled out the alternative of expanding candidates **only by text
similarity**: it is a weak signal (real matches have Jaccard median 0.127 between
finding and golden).

## Consequences

- **The means do NOT change** (control re-judgment: EII-Claude b1 0.44 / p3 0.78 / a4 0.82
  identical to the old judge; a2 p3 0.82->0.82), but the **variance drops ~1/2**
  (±0.08->±0.03), precision intact. It is a win of **reproducibility** and methodology
  (recall no longer depends on which guideline was cited), not of recall.
- **Revisit the "real P3 ≈14/15"**: it was a lucky run (run0 0.93->0.80 with the new judge),
  not the mean at k=3. P3 is robustly ~0.82 on hard EII.
- The historical table in docs/RESULTS.md is from the old judge; re-judging it entirely
  would only narrow the bars (not done: no value, identical conclusions). The main file
  was re-judged.
- Cost: the judge's prompt grows (15 candidates per finding instead of 1-3); acceptable in
  the cloud.
