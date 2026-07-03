# Test plan, validity and overfitting of the results

Motivated by a question from Miguel: does P3 (the pipeline) look so good because of **overfitting**?
This document records the battery of tests to distinguish real signal from artifact, and
to assess whether this works as a **product** (not just as the winner of a single-case benchmark).

## Identified overfitting risks

- **R-A. P3 blocks hand-designed** knowing the guidelines/case -> an advantage that does not generalize.
- **R-B. Quantity, not quality:** P3 emits ~25 findings vs ~6 from B1 -> more shots to match.
- **R-C. n=1 case:** everything (dossier, golden, blocks, prompts, judge) was tuned around the clinical case.
- **R-D. Somewhat lenient judge / grader artifacts** (see finding in B2 below).
- **R-E. Golden and dossier co-evolved** with the evaluating team.

## Base result to validate (v2, k=1)

B1 (single prompt) 0.38  <  A4 (agent) 0.67  <  P3 (fixed pipeline) 0.80  (all precision ~1.00).
Provisional reading: the pipeline wins; the agent is NOT justified. Still to be validated against the risks.

## Test battery

### A. Does it generalize? (the most important)
- **A1, held-out external cases.** Search the literature/web for real cases with interaction problems
  DOCUMENTED by independent sources (objective golden, not our interpretation);
  build dossier + golden and run B1/P3/A4. This is THE overfitting test. _Status: ✅ DONE, **5
  held-out from independent sources**._
  - Epic Sepsis (a different clinical one) + HireVue (HR), 2026-06-29.
  - **COMPAS** (justice), **MCAS-aviation** (737 MAX cockpit) and **content moderation** (2026-06-30),
    built from cited independent sources (blind neutralized dossier + golden of 9 issues each
    in `data/external/{compas,mcas-aviacion,moderacion}/`). k=3 results: P3 0.93-1.00, A4 0.93-1.00,
    B1 0.81-0.96, precision 0.93-1.0; B0=0. **Overfitting RULED OUT**: the pattern reproduces in all.
    (They are medium difficulty -> B1 already performs high; they are not "hard" cases like IBD.)
- **A2, alternative blocks.** Re-run P3 with a neutral grouping (4 HAX phases + PAIR
  chapters, no hand-design). If P3 holds, the advantage is the *decomposition*, not my blocks. _Status: ✅ DONE
  (2026-06-29, IBD v2, k=3, cloud)._
  - **Result:** P3-neutral (`p3n`, 10 buckets DERIVED from the `group` field: 4 HAX phases + 6 PAIR
    chapters, no hand-design) recall **0.89 ±0.03** vs P3-hand-designed (`p3`) **0.82 ±0.08**. Precision 0.99 and
    genericity 0.00 in both.
  - **Reading:** R-A **RULED OUT**. The neutral partition matches/exceeds my blocks -> the advantage is
    *decomposing*, not the manual design. `p3n` is also more stable (±0.03). Cost: `p3n` generates ~2×
    findings (102 vs 56/run) for the same recall -> more verbose, but does NOT fabricate (precision intact).
    Product implication: grouping by the official taxonomy (free, robust) ≥ hand-designed blocks.

### B. Are the numbers real?
- **B1, structure or quantity?** A "B1-exhaustive" (single prompt asking for MANY findings, one
  pass). If it matches P3, the advantage was quantity; if not, the structure contributes. _Status: pending._
- **B2, human adjudication of P3.** _Status: DONE (2026-06-29)._
  - **Result:** the 12 distinct matches are legitimate -> **0.80 real, not inflated**.
  - **Important finding:** P3 is **undervalued**. Of the 3 "missed", GI-13 (onboarding) and
    GI-06 (automation bias) **were in fact found**, but the grader did not match them because the
    finding cited a guideline different from the golden's (no overlap -> not a candidate). **Real P3
    ≈ 14/15.**
  - **Derived bug (affects everyone equally):** the grader's guideline filter produces
    FALSE MISSES when the generator cites the "wrong" guideline. Possible mitigation: widen
    candidates by group/chapter or by semantic similarity, not only by exact id. It raises the recall
    of all approaches; the relative comparison holds.
  - **FIXED (2026-06-30):** `judge._candidates` now offers ALL the golden (those that share
    guideline/group first); the "shortlist" was a crutch of the 14B, not needed with a strong cloud judge.
    Surprise on measuring (re-judged control p3, k=3): the average does NOT rise (0.82->0.82), but the **variance
    drops by half (±0.08->±0.03)** with precision intact. The "≈14/15" was a lucky run, not
    the average. It is a reproducibility win, not a recall one. Detail in [RESULTS.md](RESULTS.md).

### C. Is it a good product (not just winning the benchmark)?
- **C0, deduplication (the product step).** The live anti-pattern: P3 emits the same problem
  several times (often citing different guidelines). _Status: ✅ DONE (2026-06-30, deterministic,
  offline)._ `src/interaction_review/dedup.py` + `scripts/dedup_report.py`; exposed as
  `review --dedup`. Validated over already-judged runs: **coverage lost 0 in 6 scenarios**
  (recall intact), 13-26% reduction in p3 with impurity ~0, generalizes to the held-out cases, and does not harm
  what is already concise (b1/a4).
  - **Semantic layer with LLM, ✅ DONE (2026-06-30, `dedup_llm.py`, `review --dedup-llm`).** For the
    residual ("same problem via a different guideline"). It collapses strongly (p3: 56->17, 42->15, 41->14, ~one
    finding per problem) and maintains coverage, BUT **over-merges** (impurity 6/5/9 in k=3). Two levers tested:
    strict prompt (barely moved it) and **guardrail in code** (`locus_floor`: the LLM proposes, the
    code vetoes disparate loci) -> impurity ~½ (a2 4/Epic 0/HireVue 5) but it eats into conciseness (~28-31 ≈
    deterministic). **Fundamental trade-off** -> deterministic = default; LLM = aggressive mode with a review.
  - **Difficulty routing (`auto`, `router.py`), ✅ EXPLORED (2026-06-30).** b1 + gap-check -> escalates to
    p3+dedup. The gap-check over-escalates (3/4) and may leave a miss on the b1 branch (HireVue) -> difficulty is not
    inferred cleanly a priori; **p3+dedup is the robust default**. Detail in [RESULTS.md](RESULTS.md).
- **C1, false positives in a "good" system.** Give P3 the dossier of a well-designed system
  (few problems). Does it stay quiet or invent to fill blocks? An auditor that always finds 25
  faults is useless. _Status: pending (requires a synthetic dossier of a "good" system)._
- **C2, robustness to input format.** Vary the dossier (less detail, different phrasing) and see
  whether the findings hold. _Status: ✅ DONE (2026-06-29, IBD v2 paraphrased by LLM, same
  information, narrative prose instead of the telegraphic model-card style, k=3, cloud)._
  - **Result:** P3 recall **0.78 ±0.03** (paraphrased) vs **0.82 ±0.08** (original, A2); precision
    1.00 and grounding 1.00. B1 **0.47 ±0.33** (as noisy as without paraphrasing: 0.44 historical).
  - **Reading:** P3 is **robust to phrasing**: reformulating the input does not change its recall or its precision
    -> it understands the meaning, it does not "fish" for format/keywords. B1's fragility is intrinsic
    (lack of structure), not a matter of phrasing. It reinforces P3 as a product candidate.
- **C3, the agent's niche.** A4 vs P3 with **incomplete input** (info scattered/absent): the only
  regime where autonomy should win. _Status: ✅ DONE (2026-06-29, IBD v2 with a trimmed dossier,
  no user voice or production logs, k=3, cloud)._
  - **Result:** over incomplete input, **A4 recall 0.62 ±0.08** vs **P3 0.78 ±0.13**. Against the
    baseline of COMPLETE input (A4 0.82, P3 0.78): **P3 does NOT drop (robust); A4 collapses −0.20**.
  - **Reading (counterintuitive):** the hypothesized agent niche does NOT appear. Incomplete input is
    exactly where P3's **fixed exhaustive sweep gains most**: it guarantees coverage when the signal is
    scarce and scattered. A4, deciding autonomously when to stop, **cuts short** (≈30 findings vs 53 from
    P3) and leaves recoverable issues behind. A4 keeps very high precision (0.99) but at the cost of recall.
  - **Caveat -> RESOLVED (2026-06-30):** a **fresh** A4-complete control over IBD v2, k=3: **0.80 ±0.09**
    (precision 1.00) ≈ 0.82 previous. The C3 delta (A4 complete ~0.80-0.82 vs incomplete 0.62) is
    **locked in**: the drop of A4 with incomplete input is real, not a run artifact.

### Confirmation with variance
- **k=3** of the key approaches (P3 and A4 at least) once the previous tests are closed, to
  apply the `beats` rule formally. _Status: pending (high cost on a slow local machine)._

## Status as of 2026-06-29 (executed on Claude CLOUD; synthesis in RESULTS.md)

- **B2** human adjudication of P3: ✅ DONE (0.80 real, undervalued; grader bug documented).
- **A1** generalization: ✅ DONE with **5 held-out from independent sources** (HireVue, Epic, COMPAS, MCAS-aviation, moderation on 2026-06-30) -> **it was NOT overfitting** (patterns reproduced in all: P3/A4 0.93-1.00).
- **B1** structure vs quantity: ✅ answered by the map, the structure contributes **reliability** in hard cases (B1 unstable, one run at 0), not just quantity; in easy cases B1≈P3. (The `b1x` approach was implemented; its local run was aborted for slowness.)
- **C1** false positives in a good system: ✅ DONE. B1/P3/A4 return **0 findings**; they do not invent. P3's verbosity is redundancy, not fabrication.
- **A2** alternative blocks: ✅ DONE (R-A ruled out: neutral `p3n` 0.89 ≥ hand-designed `p3` 0.82; see above).
- **C3** the agent's niche: ✅ DONE. The niche does NOT appear; with incomplete input P3 (exhaustive) 0.78 > A4 0.62.
- **C2** input robustness: ✅ DONE. P3 robust to phrasing (paraphrased 0.78 ≈ original 0.82, precision 1.00).

**A/C battery completed (2026-06-29).** A2 (block overfitting) ruled out · C3 (the agent's niche)
does not appear, the agent loses where it should win · C2 (robustness to phrasing) confirmed for P3. Synthesis in
[RESULTS.md](RESULTS.md).
- **k=3 confirmation**: ✅ done in cloud (all runs in the table are k=3).

**Conclusion validated in [RESULTS.md](RESULTS.md): a conditional map** (the complexity that pays off depends on difficulty×model), not a single winner.

## Method notes
- Slow local machine (~10 min/call when the workstation is used) -> background runs with a watchdog
  and generation checkpoint. Suspend pauses runs (disable or watch out).
- All raw output is saved in `runs/` (gitignored). Case material in `data/golden/` (private).
