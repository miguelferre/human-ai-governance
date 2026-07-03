# Results: testimony ablation, does the user's voice add anything?

The reviewer's commercial differentiator is incorporating the **end user's testimony**, not
just auditing the design in the abstract. But it was an **undemonstrated** promise: control C3
(RESULTS.md) showed that, in **global** recall, the dossier with voice and without voice perform almost
the same. That does not refute it (the value of the voice could lie in a subset of problems that
*only* it reveals) but it forces measuring it rather than asserting it. This is that targeted measurement.

Full design in [ADR-007](adr/ADR-007-testimony-ablation.md). In one sentence: each known problem is
labeled by **the source that reveals it** and the recall of the problems that only the voice reveals is separated out.

## What was measured

Over each `GoldenIssue` of the **7 cases with real testimony** (64 problems in 6 sectors),
it was labeled by hand (reading the content of each source in the dossier) as to where it is *detectable*:

- **`user_only`**: only the testimony of an end user sustains it. Without that voice, the
  problem is invisible in the dossier.
- **`tech_only`**: only the documentation or the technical profile sustains it.
- **`both`**: the documentation describes it **and** the user lives it.

The labeling goes in the answer key (outside the blind dossier; the reviewer does not see it). It was done with
independent annotators per case and the ADR criterion (be strict: if a user does not really
mention the problem, it does not count as sustaining it). It is reproducible with
`scripts/ablacion_report.py dist`.

## Offline result: how much of the golden depends on the voice

This count **does not spend API** and is informative on its own: it is the **ceiling** of what the
testimony can add to recall. If there were almost no `user_only`, the voice could not add
much even if we wanted it to.

| case | total | user_only | both | tech_only | unknown | % voice-dependent |
|---|---|---|---|---|---|---|
| robodebt-hard | 10 | 0 | 4 | 5 | 1 | 0% |
| concern-cds | 9 | 0 | 7 | 2 | 0 | 0% |
| alert-fatigue-ehr | 8 | 2 | 5 | 1 | 0 | 25% |
| post-office-horizon | 9 | 2 | 5 | 2 | 0 | 22% |
| toeslagenaffaire | 10 | 2 | 4 | 4 | 0 | 20% |
| asiana-214 | 9 | 3 | 3 | 3 | 0 | 33% |
| cierre-cuentas-bancarias | 9 | 3 | 3 | 3 | 0 | 33% |
| **TOTAL** | **64** | **12 (19%)** | **31 (48%)** | **20 (31%)** | **1** |  |

## Honest reading

**1. The voice does add, but not as massive recall: it is 1 in every 5 problems.** 19% of the
known problems are revealed **only** by the testimony. It is neither zero (this qualifies the C3 headline, which
looked only at global recall) nor the majority. The bulk of the voice's value (the 48% `both`)
is **grounding**: it gives vivid, credible evidence to problems the documentation already reveals.

**2. The contribution depends on how documented the case is.** The two cases with **0 `user_only`**
(robodebt and CONCERN) are the most covered by official reports or exhaustive technical sheets:
there almost everything is already written down and the testimony only confirms. By contrast, where
the living source is the operator or the pilot (Asiana, account closure: **3/9**), a third of
the problems would be lost without the voice. **Product implication:** the less documented
a system is (the normal case in a real audit) the more the testimony adds.

**3. What *only* the voice reveals is systematically the cognitive layer.** The 12 `user_only`
are not random; they are almost always the same type of problem:

- **Automation bias / deference to the machine**: closing the alert without reading it (alert-fatigue),
  "acabo confiando en que la máquina tendrá razón" (account closure), "llegué a dudar de mí
  mismo antes que del programa" (Post Office).
- **Wrong mental model of the automation**: the pilot who takes for granted that the A/T maintains the
  speed, or that a protection expectation from another aircraft is relevant (Asiana).
- **Lived timing**: the alert that fires at the worst moment and cuts off the task
  (alert-fatigue).
- **Erosion of trust / perceived burden of proof**: "pierdes la confianza en el propio
  gobierno", "eres tú quien tiene que demostrar que no eres una defraudadora" (Toeslagen).

The technical documentation reveals the **structure** (model opacity, no capture of the
override, poorly calibrated thresholds). The testimony reveals the **lived experience and the cognition**: the
overconfidence, the mental model, the fatigue, the wrong moment. And that cognitive layer is
precisely the most dangerous one in a clinical system and the one no technical sheet is going to declare.

## The effect: recall with voice vs without voice (run done)

The count above measures the **ceiling** (how many problems depend on the voice). This run measures
the **effect**: how much the reviewer's recall drops when the testimony is removed. **Within-subject** design
over the 5 cases with `user_only` (45 problems):

- **Blind generator** (Sonnet): produces anchored findings over the dossier **with voice** and,
  separately, over the **same dossier without the `end_user` sources** (`ablation.without_voice`).
  Same prompt; it does not see the golden nor know the hypothesis.
- **Independent judge** (Opus, a different role and model, blind to `revealed_by`): adjudicates which golden
  each set covers, with the same standard in both conditions.

Data in `ablacion-voz/consolidado_k1.json` (recomputes the table) and `ablacion-voz/raw/` (raw findings and verdicts).

| revealed_by | n | recall WITH voice | recall WITHOUT voice | Δ |
|---|---|---|---|---|
| **user_only** | 12 | **0.83** | **0.33** | **−0.50** |
| both (control) | 20 | 0.90 | 0.85 | −0.05 |
| tech_only (control) | 13 | 0.85 | 1.00 | +0.15 |
| **global** | 45 | 0.87 | 0.76 | −0.11 |

**It confirms the pre-registered prediction (ADR-007).** The recall of the problems that only the
voice reveals **collapses by half** (0.83 → 0.33) when the testimony is removed, while the controls
barely move: `both` −0.05 (the documentation sustains them) and `tech_only` does not even drop (the reviewer
without voice concentrates on the documental). The effect is localized in `user_only`, which is
exactly what the hypothesis predicted. The global falls only −0.11 because `user_only` is 12 of 45,
consistent with C3, which looked at the aggregate and therefore did not see the effect.

**Why the delta is defensible despite being done with the model itself.** Circularity (Claude
built the cases and here generates/judges) inflates the *absolute* recall, but it is the **same blind
generator in both conditions**: the only difference is the presence of the voice, so the delta
−0.50 is attributable to the testimony, not to the model. The flat controls (both, tech_only) confirm
it: if it were a model artifact, they would have dropped too.

**Honest nuance (account closure).** It is the only case where `user_only` does not fall (3 → 3): it has an
*ex-programmer* (technical source) so eloquent about automation bias that he acts as a substitute
voice. Same pattern as the offline count (robodebt/CONCERN with 0 `user_only` for being
hyper-documented): **when a technical person "speaks like a user", the user's voice adds less**.
The result does not hide this; it explains it.

**Caveats of this run (assisted).** It was **assisted** with subagents (separated roles), not with the
`compare` code-pipeline, and **k=1**. To close it, it was redone with the reproducible code-pipeline and k=3
(see below), which confirms the direction and recalibrates the magnitude. Two `user_only` were not detected even with voice
(PO-09 training, TO-10 loss of trust): the blind generator did not report them even with the voice, and that
is why the recall with voice is 0.83 and not 1.00.

## Confirmation with the code-pipeline (k=3, 2026-07-02)

The run was redone with the **reproducible** flow (`compare` code-pipeline, not subagents), approach p3,
**Haiku generator / Sonnet independent judge**, k=3, over the same 5 cases. Data in
`docs/ablacion-voz/consolidado_k3.json` (+ raws by case and condition).

| revealed_by | n | recall WITH voice | recall WITHOUT voice | Δ (without − with) |
|---|---|---|---|---|
| **user_only** | 12 | **0.83** | **0.56** | **−0.28** |
| both (control) | 20 | 0.97 | 0.95 | −0.02 |
| tech_only (control) | 13 | 0.95 | 1.00 | +0.05 |
| **global** | 45 | 0.93 | 0.86 | −0.07 |

**The direction is confirmed; the magnitude is recalibrated.** The effect remains **localized in `user_only`** (the
controls do not move), but it falls **−0.28** instead of the assisted −0.50. The difference is the **generator**: the
assisted run used Sonnet (conservative, which without the voice did not report the cognitive part); this one uses **Haiku, which
infers from the technical documentation** part of those problems. Part of the −0.50 was an artifact of the conservative
generator, not a pure effect of the testimony.

**Issue by issue** (in how many of the 3 runs WITHOUT voice each `user_only` is still detected) yields a
finer and more useful reading:

- **They fall to zero without the voice (0/3), the purely experiential ones:** deference to the machine (PO-01, *"llegué a
  dudar de mí mismo antes que del programa"*), the reversed and lived burden of proof (TO-04, *"eres tú
  quien tiene que demostrar que no eres una defraudadora"*), the erosion of trust (TO-10). No generator
  infers them from a technical sheet: **only the voice reveals them**.
- **Haiku recovers them without the voice (3/3), the cognitive-structural ones:** automation bias where the docs say
  alerts are closed (AF-02, cc-04), fatigue where they say hourly alerts (AF-04), lack of an override where there
  is no appeal (cc-03), protection expectation (AS-05). There the voice adds **grounding**, not
  discovery: a capable model deduces them from the already documented structure.

**Refined conclusion.** The testimony is **indispensable for the experiential-emotional layer** (invisible in
any document; it falls to zero without the voice in both runs) and **adds grounding for the
cognitive-structural layer** (which a capable generator infers from the docs). That is why the magnitude of the effect depends on
how inferential the generator is, hence the −0.50 with Sonnet against the −0.28 with Haiku, but the testimony's
differentiator holds up when measured with an independent method, and its hard core (what the person *lives* and no
sheet declares) is exactly what disappears without it.
