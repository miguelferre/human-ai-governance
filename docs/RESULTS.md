# Experiment results: is an agent needed to review the interaction layer?

Synthesis as of 2026-06-30. Detail of each run in `runs/` (gitignored); plan in
[TESTPLAN.md](TESTPLAN.md); design decisions in [docs/adr/](adr/).

## The question

To review the human-AI interaction layer, is an **agent** needed, or does a **single prompt**
(or even a **deterministic checklist**) suffice? Project rule: complexity is only justified if it
**wins in a measurable way** over the previous rung.

## Method

A ladder of approaches, all with the same contract (dossier to findings anchored to
HAX-18/PAIR):
- **B0** deterministic checklist (no LLM) · **B1** single prompt · **B2** few-shot ·
  **P3** deterministic pipeline (block-by-block sweep, NOT an agent) · **A4** agent (a loop
  where the MODEL decides what to investigate and when to stop).
- Golden set with known problems; **LLM judge** that adjudicates (recall, precision,
  genericity); rule `beats` = margin > noise across k runs.
- Validation against **overfitting** with **held-out** cases documented in the literature
  (Epic Sepsis, HireVue) and **false-positive** control on a well-designed system.

## The results map (recall, k=3)

| Case | Difficulty | Model | B1 | P3 | A4 |
|---|---|---|---|---|---|
| IBD (clinical) | hard (15 issues) | qwen2.5:14b local | 0.38 | **0.80** | 0.67 |
| IBD (clinical) | hard (15) | Claude (Haiku/Sonnet) | 0.44 *±0.32 unstable* | 0.78 | **0.82** |
| HireVue (held-out, NON-clinical) | easy (7) | Claude | 0.90 | **1.00** | 0.90 |
| Epic Sepsis (held-out, different clinical) | easy (7) | Claude | **0.95** | 0.95 | 0.86 |
| COMPAS (held-out, NON-clinical) | medium (9) | Claude | 0.85 | **1.00** | **1.00** |
| MCAS aviation (held-out, NON-clinical) | medium (9) | Claude | 0.96 | 0.93 | 0.96 |
| Moderation (held-out, NON-clinical) | medium (9) | Claude | 0.81 | **1.00** | 0.93 |

B0 = 0.00 across all (floor). All LLM approaches: precision ~0.93-1.0, genericity 0.
The last three (held-out 2026-06-30, new judge) are public cases documented by independent
sources; they reproduce the pattern, reinforcing "it is not overfitting" (now **5 held-out**, 3 domains).

## Conclusion: it is not a single winner, it is a map

1. **The LLM beats the checklist every time.** B0 (generic by construction) never competes.
2. **Easy case + strong model, the single prompt suffices** and is the most concise. On Epic,
   B1 nails 7/7 with ~11 findings; P3 pulls out the same 7 with ~42 (pure redundancy).
3. **Hard case, STRUCTURE is needed.** The single prompt is unstable (in IBD-Claude one of three
   runs went to **0 findings**): it has no safety net.
   - **Weak model, the pipeline (P3)** is the safe choice; the agent's autonomy is noisy there.
   - **Strong model, the agent (A4) matches** the pipeline (0.82 vs 0.78) and is **more concise**
     (~30 vs ~55 findings), but **only with complete input**. That advantage **is not robust**
     (see C3 below): if the input degrades, A4 collapses and P3 holds.

In other words: the complexity that pays off **depends on the difficulty of the case and the
capability of the model**. Neither "the agent is always superfluous" nor "the agent always wins".

## Cross-cutting findings (the most valuable part)

- **The fragile link was the JUDGE (the measurement), not the generator.** It took 4 iterations
  to make it reliable; the solution was always to **move deterministic judgment into the code** and
  leave the model only the irreducible part (reason before labeling, derive the label
  in code, structural genericity gate, candidates preselected by guideline).
  For AI governance this is a lesson in itself: *trust the model to judge, but put deterministic
  guardrails in place*. **B0 is the canary**: if it scores > 0, the measurement is broken.
- **It was not overfitting.** **Five** held-out across **three domains** (Epic Sepsis and HireVue;
  COMPAS, MCAS-aviation and content moderation, these three built from independent cited sources)
  reproduce the patterns. The high recall of the clinical case was not a trick of the case: P3/A4 recover
  0.93-1.00 of problems documented by third parties, precision 0.93-1.0.
- **There is no false alarm (C1).** On a well-designed system, B1/P3/A4 return **0
  findings**: they do not invent problems. P3's verbosity is **redundancy**, not
  fabrication, and is fixed with a deduplication step.
- **Human adjudication is indispensable:** it uncovered two measurement biases (judge under
  load; golden-dossier mismatch) that would have falsified the conclusions.

## Robustness validation (A2 · C3 · C2, k=3, cloud, hard IBD v2 case)

Three more tests to distinguish signal from artifact and close the agent question:

- **A2, is the pipeline's advantage MY blocks (overfitting) or decomposition?** P3 was re-run with a
  **neutral** partition (the authors' taxonomy: 4 HAX phases + 6 PAIR chapters, derived from the data,
  with no hand design). **0.89 ≥ 0.82** for hand-built P3, so **it is not block overfitting**: the advantage is
  *decomposition*, and the neutral partition turns out to be more stable too (±0.03).
- **C3, is incomplete input the agent's niche?** A4 vs P3 with the dossier trimmed (no user's voice
  or logs). **Counterintuitive** result: A4 **0.62** vs P3 **0.78**; against complete input
  (A4 0.82, P3 0.78), **P3 does not fall and A4 collapses −0.20**. The hypothesized niche **does not
  exist**: poor input is exactly where the fixed exhaustive sweep gains the most. A4, by deciding when to stop, cuts
  short (~30 findings vs 53) and leaves recoverable issues behind.
- **C2, does it depend on the exact wording?** P3 over the paraphrased dossier (telegraphic model-card to prose,
  same facts): **0.78 ≈ 0.82** original, precision 1.00. **Robust to wording**: it understands, it does not fish
  for format. (B1 remains noisy, 0.47 ±0.33: its fragility is structural, not about wording.)

**What changes in the conclusion:** the cell *"strong model, the agent is justified"* is **weakened**. The
agent only matches in the best case (easy/complete) and is more concise, but **it has no robust niche**:
it loses to the pipeline as soon as the input degrades. The complexity that pays off **robustly** is the
**fixed decomposition of the pipeline (P3)**, not the agent's autonomy.

## Deduplication: the product step (deterministic, offline, k=3)

The live anti-pattern of P3/p3n: it emits the SAME problem several times, almost always
citing a DIFFERENT guideline each time (in one run, "onboarding without retraining" appeared
**7 times** via HAX-G1, HAX-G12, PAIR-UN-2, PAIR-MM-1, PAIR-EF-2, PAIR-DE-1...). A
human auditor does not want to read it seven times.

`src/interaction_review/dedup.py` collapses near-duplicate findings into one that **merges the
guidelines of all of them** (one finding per problem, annotated with all the guidelines it breaks). It is
DETERMINISTIC, lives in code, has no LLM, and **does not look at the golden** (in production it does not exist):
it groups by lexical similarity of the problem (Jaccard of title+locus, plus title ratio with an
anti-template guard). Consistent with ADR-004: the mechanical part goes to the code.

Validated OFFLINE over already-judged runs (`scripts/dedup_report.py`), using the
adjudications (which the dedup never sees) as an independent yardstick: does it lose coverage? Does it
merge distinct real problems (impurity)?

| Case | approach | n before->after | reduction | coverage | impure (k=3) |
|---|---|---|---|---|---|
| IBD (hard) | p3 | 56 -> 44 | 21% | 12.3 intact | 0 |
| IBD (hard) | p3n | 102 -> 77 | 24% | 13.3 intact | 5 |
| IBD C2 (paraphrased) | p3 | 58 -> 42 | 26% | 11.7 intact | 4 |
| IBD C3 (incomplete) | p3 | 53 -> 39 | 25% | 11.7 intact | 0 |
| Epic (held-out) | p3 | 42 -> 36 | 14% | 6.7 intact | 0 |
| HireVue (held-out) | p3 | 41 -> 35 | 13% | 7.0 intact | 2 |

**What the numbers say (T=0.60, calibrated by the `--sweep`):**
- **It is SAFE: coverage lost = 0 in all 6 scenarios** (recall always intact; the dedup
  does not drop findings, it merges). Precision intact. And **it does not damage what is already concise**: b1 and a4 barely
  change (0-7%), there is nothing to collapse.
- **It generalizes:** same gain on both held-out, not tuned to IBD.
- **The deterministic win is MODEST:** ~13-26% fewer findings in p3 with impurity ~0. It removes the
  textually evident duplicates; it lowers the console but does not empty it.
- **p3n is harder to clean** (5 impure, 4.2x duplication per golden), another point in favor of
  **p3 as the product** over p3n.
- **The residual is irreducible judgment:** "the same problem slipped in under a different guideline"
  with very different vocabulary is not distinguishable at the lexical level from two neighboring problems without
  risking conflation (that is why T stays on the safe side). That last layer calls for a
  **semantic (LLM)** step, exactly the thesis of the project: the mechanical part to the code, and to the model only
  the irreducible part.

### Semantic layer with LLM (front 1b, `dedup_llm.py`): the trade-off

Over the residual, a call to the model groups by underlying problem (the merge and the guarantee of
not losing findings remain deterministic, in code). Validated over already-judged p3 runs:

| Case | n raw -> lexical -> LLM | coverage | impure (clusters that mix golden, k=3) |
|---|---|---|---|
| IBD (a2) | 56 -> 44 -> **17** | 12.3 intact | 6 |
| Epic (held-out) | 42 -> 36 -> **15** | 6.7 intact | 5 |
| HireVue (held-out) | 41 -> 35 -> **14** | 7.0 intact | 9 |

**Honest trade-off, not a clean win:** the LLM **truly collapses** (~one finding per problem, which
the deterministic step does not achieve) and **keeps coverage** (recall intact), but **over-merges** (impurity 6/5/9,
up to ~2/3 of clusters in HireVue mix distinct problems).

**Two levers were tried (2026-06-30):** (1) a strict prompt "by default DO NOT group, when in doubt separate"
barely moved impurity (a2 6→6, Epic 5→4). (2) A **guardrail in code** (`SEMANTIC_LOCUS_FLOOR`: the LLM
proposes groups, the code VETOES the member with a locus that differs from the representative), which **lowers impurity ~by half
(a2 4, Epic 0, HireVue 5)** but **eats into conciseness**: with the guardrail the LLM ends up at ~28-31, barely
better than the deterministic step (~36-44).

**Conclusion (honest) of front 1b:** the semantic layer is a **fundamental trade-off**, not a clean
improvement: aggressive it conflates, and with a guardrail it barely beats the deterministic step. That is why the **deterministic dedup
is the recommended default** (safe, impurity ~0) and `--dedup-llm` (with a default guardrail of 0.18) is an
**optional aggressive mode with review**. What would really close the residual without conflating would call for the
good yardstick: the **new judge** re-judging these runs (the measured impurity is an upper bound, part of it is noise from the
old judge that splits a single problem into two goldens).

## Routing by difficulty (front b, `router.py`, `review --approach auto`)

The map says: easy→b1 (concise), hard→p3 (structure). Since difficulty is not known a priori, the
router runs b1 and **escalates to p3+dedup** if the gap-check (reused from A4) detects uncovered areas, or if b1
comes back thin (the latter covers its instability: the run to 0). Check of the decision over already
generated b1 (real gap-check):

| Case | b1→p3 known | router decision | correct? |
|---|---|---|---|
| IBD (hard) | 0.44→0.78 | escalates to p3+dedup | ✓ b1 insufficient |
| COMPAS (medium) | 0.85→1.00 | escalates | ✓ p3 improves |
| Epic (easy) | 0.95→0.95 | escalates | ~ unnecessary (p3 does not improve but does not lose; +verbosity) |
| HireVue (easy) | 0.90→1.00 | stays on b1 | ✗ leaves 0.10 (p3 would give 1.00) |

**Honest:** the gap-check is **eager**, escalating 3/4 (in practice ≈ "p3+dedup unless b1 already covers
everything") and, when it stays on b1, it can leave an issue unseen (HireVue: the gap-check did not detect the hole).
**Difficulty is NOT inferred cleanly from a single b1 pass.** Conclusion: the **robust
recommendation is p3+dedup by default** (it never loses much: 0.78-1.00 in all cases); lean-safe `auto` is useful
(and shields b1's instability) but its b1 branch risks a miss, so it is a conciseness optimization,
not a reliable discriminator. Another honest result: the router's complexity does not pay for itself.

## Honest limitations

- Golden sets are small and built by the evaluator (IBD case) or from public sources
  (held-out); the number of cases is already reasonable (6 cases, 5 held-out, 3 domains) but still not a benchmark.
- The "zero" of B1 in IBD-Claude could be a one-off API hiccup, but it illustrates the
  single prompt's lack of a safety net.
- The 3 new held-out (COMPAS/MCAS/moderation) are of **medium** difficulty and well documented,
  so B1 already performs high (0.81-0.96): they confirm generalization but are not "hard" cases like IBD.
- A4-vs-P3 still needs confirmation with more **hard** cases and intermediate models.

## Next steps

- **Product, deduplication:** DONE in its **two layers** (safe deterministic + semantic LLM). Front 1b
  turned out to be a **fundamental trade-off** (see above): deterministic default, `--dedup-llm` as an aggressive mode.
- **Routing by difficulty (`auto`):** EXPLORED (see above). Honest result: difficulty is not
  inferred cleanly a priori (the gap-check over-escalates); **p3+dedup is the robust default**. `auto` remains a
  lean-safe option.
- **What would really close the dedup residual:** re-judge these runs with the **new judge** to measure
  the real impurity (the current one is an upper bound, contaminated by the old judge), but this is polish, it does not change the
  recommendation (deterministic by default). The experiment and the minimal product are **closed**.
- **Measurement debt, fixed (2026-06-30).** The judge's candidate filter only offered
  goldens with the EXACT shared guideline (a crutch of the local 14B judge, ADR-004): a finding that cited
  another guideline had no way to reach the correct golden as a candidate, hence a false miss. Now the cloud judge (strong)
  sees **all** goldens, with those sharing guideline/group first as a hint (`judge._candidates`).
  Control re-judging (p3, a2, k=3): **mean recall stable 0.82→0.82, variance halved
  (±0.08→±0.03), precision intact (0.99)**. Honest reading: the fix improves **reproducibility**
  and removes the dependency on which guideline was cited, but **does NOT raise the mean**, the "real P3 ≈14/15" was
  a lucky run (run0 drops 0.93→0.80 with the new judge; runs 1-2 rise), not the truth at k=3.
  Also re-judged the main file **complete IBD-Claude (b1/p3/a4): means IDENTICAL to the old judge
  (0.44 / 0.78 / 0.82)**, so the fix does not touch the headline. Trimmed here: re-judging the other 5 files
  of the table would add nothing (stable means, only variance changes). **Conclusions unchanged.**
- **Fresh A4-complete control, DONE (2026-06-30).** A4 over complete IBD v2, fresh k=3: **0.80 ±0.09**
  (precision 1.00), against the previous 0.82, so the C3 delta (A4 complete 0.80-0.82 vs A4 incomplete 0.62) is
  **shielded**: A4's drop with incomplete input is real, not an artifact of one run.
