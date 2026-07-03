# Results: held-out cases with real user testimony

Additional validation (2026-06-30) over **7 real cases with documented user testimony**,
across 6 sectors, complementing the main experiment ([RESULTS.md](RESULTS.md)). Motivation:
the previous held-out cases were reconstructions from the literature *without* primary user voice; the
product's differentiator is precisely incorporating the **testimony of whoever uses the system**, so
it needed to be tested on cases that had it.

**How it was measured.** Generator (the reviewer) = cheap model (Haiku), **blind**: it only sees the dossier,
never the golden. Adjudication by transparent golden-finding mapping. The dossiers and goldens of each
case live in `data/external/<case>/`.

> **Honest method note.** This batch was run in an **assisted** way (with subagents), not with the
> `compare` code-pipeline. The reproducible number with an independent LLM judge is pending the
> code-run (see [TASKS.md](TASKS.md)). That is why the result that really counts is the **hard test**
> below, designed to eliminate the bias of the same engine building and detecting.

## The 6 cases built for the test

| Case | Sector | Golden | Recall | Precision |
|---|---|---|---|---|
| Alert fatigue in EHR alerts | Healthcare | 8 | 8/8 | high · +5 discoveries |
| CONCERN (predictive ML CDS) | Healthcare | 9 | 8/9 (+1 partial) | high |
| Asiana 214 (autothrottle, cockpit) | Aviation | 9 | 9/9 | high |
| Algorithmic closure of bank accounts | Finance | 9 | 9/9 | high |
| Post Office Horizon | Operator (UK) | 9 | 9/9 | high |
| Toeslagenaffaire (benefits) | Public admin. (NL) | 10 | 9/10 (+1 partial) | high |
| **Total** | **5 sectors** | **54** | **52/54 clear + 2 partial ≈ 0.96-1.00** | ~0.9-1.0 |

Haiku sufficed in all 6; no more expensive model was needed.

**Caveat, circularity.** In these 6, the same type of model (Claude) built the dossiers+goldens
*and* generated the findings, so the generator easily finds what another model annotated. This **inflates
recall**. To measure it, the hard test below breaks that bias.

## Hard test: Robodebt (circularity broken)

Design with **separated hands**:
- **Golden** ← derived from the **Royal Commission into the Robodebt Scheme** (Holmes report 2023),
  Commonwealth Ombudsman and Victoria Legal Aid, by an agent that **did not see the dossier**.
- **Dossier** ← raw facts + real literal testimonies (Masterton, Amato, Colleen Taylor, Holmes),
  by another agent that **did not see the golden** and with an explicit prohibition on labeling problems.
- Blind Haiku generator · transparent adjudication.

It breaks the two biases that inflated the most: own golden + curated dossier.

**Recall = 9/10 = 0.90.** The only miss (the AAT tribunal set-asides that the scheme ignored) is
because **that information was not in the raw dossier**, the reviewer could not see it and **did not invent it**.
The drop is not blindness, it is lack of data.

| Failure flagged by the Royal Commission | Recovered |
|---|---|
| Notice without explaining the calculation | ✅ |
| Phone deliberately omitted | ✅ |
| Online-only channel forced | ✅ |
| Burden of proof reversed | ✅ |
| No prior human review | ✅ |
| Fictitious debt from income averaging | ✅ |
| 5 years of documentation impossible to provide | ✅ |
| Debt without communicating uncertainty | ✅ |
| Ignoring the tribunal (AAT) set-asides | ❌ (not in the dossier) |
| Intimidating tone / trauma | ✅ |

## Reading

By breaking the circularity (external human golden + raw dossier + separated hands), the reviewer
recovers **9/10 of the failures that an independent human body identified**, from raw facts and
real testimonies, with the cheapest model, **without inventing**. Circularity was inflating **little**
(~0.08: from ~0.98 to 0.90).

## Hard test extended to n=3 (2026-07-01)

To shield Robodebt's 0.90 with more than one case, **two more hard cases** were built with the
same **separated-hands** design (one builder derives the golden from the independent source without seeing
the dossier; another builds the dossier of facts + real testimonies without seeing the golden; both with
web search and cited sources), and it was measured with **blind generator (Sonnet) + independent judge (Opus)**:

| Case | Sector | Golden | Recall |
|---|---|---|---|
| Robodebt | Welfare (Australia) | 10 | 9/10 = 0.90 |
| MiDAS | Welfare / unemployment (USA) | 9 | 7/9 = 0.78 |
| Arkansas ARChoices | Healthcare/disability (USA) | 10 | 7/10 = 0.70 |
| **Mean (n=3)** | **3 jurisdictions** | **29** | **~0.79** |

Robodebt was the high end; the mean of the hard test with separated hands is **~0.79**. The misses are
honest and of two kinds: (a) problems that were in the dossier but the reviewer did not frame (MiDAS's
self-incriminating questionnaire; the magnitude of the 400% penalty); (b) angle nuances that
the strict judge did not consider covered (in Arkansas: refusal on trade-secret grounds vs. technical opacity;
immediate loss of hours during the appeal; absence of a feedback channel). Moreover, the reviewer
produced **legitimate discoveries outside the golden** (tp_new: 2 in MiDAS, 6 in Arkansas): real, anchored
interaction problems that the independent body had not listed. Cases in
`data/external/{midas-michigan,arkansas-medicaid}/`; raw and consolidated in `docs/casos-duros/`.

The MiDAS and Arkansas cases were built with web search over cited and triangulated public sources
(audits, rulings, serious press); they contain no PHI.

## Reproducible code-run (non-assisted number)

The recall above was measured in an **assisted** way (subagents). To close the honest method note, the
**`compare` code-pipeline** was run, the same one as the main experiment, over the 9 cases with
testimony, with **cloud backend: Haiku generator, Sonnet judge (a distinct and independent model)**, k=1. This way
the judge is a separate prompt/model and the flow is reproducible: it is no longer "the agent acting as
builder and as judge". Raw data and consolidated in `docs/pipeline-codigo/`.

| approach | mean recall | mean precision |
|---|---|---|
| b0 (checklist, no LLM) | 0.00 ± 0.00 | n/a |
| b1 (single prompt) | 0.68 ± 0.25 | 0.87 |
| **p3 (pipeline, product)** | **0.93 ± 0.09** | **0.96** |

Recall of p3 by case: robodebt 0.90 · alert-fatigue 1.00 · CONCERN 1.00 · Asiana 1.00 · account-closure
0.78 · Post Office 1.00 · Toeslagen 1.00 · MiDAS 0.89 · Arkansas 0.80.

**Reading:**
- **p3 recovers 0.93 of the known problems with precision 0.96**, with an independent judge and a reproducible
  flow. The assisted run gave ~0.96-1.00 (somewhat inflated by circularity); the code-pipeline
  brings it down to **0.93 but confirms the signal**, it was not an artifact of the assisted method.
- **b0 = 0.00 in all 9**: the perfect floor/canary (the deterministic checklist invents nothing).
- **p3 beats b1 (0.93 vs 0.68) by a margin far above the noise**, so the pipeline's structure is
  justified here too, over cases outside the home domain.
- **MiDAS: b1 = 0.00 but p3 = 0.89.** The single prompt did not catch a single problem (a dense and very
  documented case) and the decomposition pipeline recovered them: the clearest illustration of "hard case,
  structure is needed".
- The two new hard cases give **more** recall in p3 (MiDAS 0.89, Arkansas 0.80) than in their single-shot
  assisted run (0.78 / 0.70): p3 decomposes by blocks and is more exhaustive.

**Remaining limitations:** it is still Claude in both roles, but with distinct models (Haiku vs
Sonnet) and a reproducible flow the independence is real. (The old k=1 caveat was closed with the
k=3 run below.)

### Confirmation with k=3 (2026-07-02)

The run above was k=1 (a single pass per approach and case, without variance). It was repeated with **k=3**
(same 9 cases, same models (Haiku generator, Sonnet independent judge), `compare` code-pipeline)
to check the promise: raising k **does not move the means**, it only puts bars around what was previously a bare
number. Data in `docs/pipeline-codigo/consolidado_k3.json` (+ raws by case).

| approach | mean recall (k=1 → k=3) | precision (k=1 → k=3) | intra-case stability (k=3) |
|---|---|---|---|
| b0 (checklist, no LLM) | 0.00 → 0.00 | n/a | 0.00 |
| b1 (single prompt) | 0.68 → 0.65 ± 0.22 | 0.87 → 0.81 | 0.15 |
| **p3 (pipeline, product)** | 0.93 → **0.91** ± 0.055 | 0.96 → **0.965** | **0.043** |

Recall of p3 by case (k=3): robodebt 0.83 · alert-fatigue 0.96 · CONCERN 0.89 · Asiana 1.00 ·
account-closure 0.89 · Post Office 0.96 · Toeslagen 0.93 · MiDAS 0.89 · Arkansas 0.83.

**Reading:**
- **The mean does not move:** p3 goes from 0.93 to **0.91** (within the bar), precision from 0.96 to **0.965**.
  The reproducible number holds up with more samples; it was not luck of a single pass.
- **The bar across cases narrows**, as predicted: p3's dispersion drops from ±0.086 (k=1) to
  **±0.055** (k=3).
- **Intra-case stability (what k=1 could not see):** resampling the LLM moves p3's recall by only
  **±0.043** on average within the same case. And p3 not only beats b1 on the mean, it is **3-4× more stable**
  (0.043 vs 0.152): the single prompt dances (in MiDAS and Arkansas its recall varies ±0.29-0.37 across runs),
  the decomposition pipeline gives almost the same thing every time. Structure buys mean **and** consistency.
