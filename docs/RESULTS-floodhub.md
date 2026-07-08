# Results: Google Flood Hub (out-of-domain climate case)

Held-out case added on 2026-07-08 to test the reviewer **outside healthcare and outside all the
sectors seen so far**: a public AI early-warning system for river floods (Google/DeepMind). It is the
16th case of `data/external/`, and the **first with the filled-in templates versioned**
(`data/external/google-flood-hub/raw/`), so the dossier is reproducible from them with `ingest`.

Motivation: the differentiator (auditing the interaction layer of a decision-support AI, with the end
user's voice) should hold when the "decision" is *should we trigger anticipatory action before a
flood?* and the users are an aid-program officer and a villager, not a clinician. Climate risk
communication is a domain the P3 prompts never saw.

## What the case is

**System under review:** Google Flood Hub, an ML (LSTM) flood-forecasting system that predicts river
crossings up to 7 days out across 80-100 countries and ~700M people, presenting four return-period
severity levels (~2/5/20-year events), a hydrograph, and inundation maps, distributed through Search,
Maps and notifications.

**Two end-user voices** (the interaction layer is the point): an **institutional decision-maker** who
uses the forecast to trigger anticipatory cash (grounded in the GiveDirectly / partner deployments,
2023-2025), and a **vulnerable resident** with poor connectivity to whom the alert arrives mediated, or
not at all (grounded in field reporting). The answer key has **10 GoldenIssues** spanning uncertainty
communication, return-period misreading, the system-level-vs-action-trigger gap, missing feedback,
extreme-event reliability not surfaced, no "why", the confidence caveat not reaching the end user,
last-mile reach, alert fatigue, and the "not a sole source" disclaimer without integration.

## Order of authoring (anti-contamination)

The **answer key was closed before running the reviewer** on this dossier. The order is recorded in git
history (the answer_key commit precedes any run artifact) and described in
[raw/00_LEEME_enfoque.md](../data/external/google-flood-hub/raw/00_LEEME_enfoque.md). The reviewer sees
only the dossier, never the golden.

## Honest caveats

- **Attribution.** The strongest causal evidence of anticipatory action in Bangladesh 2020 (CSAE
  Oxford; Gros et al.) was triggered with **GloFAS + the government FFWC, not Google Flood Hub**. This
  case does not attribute that evidence to Flood Hub; the decision-maker voice is grounded in the
  documented Flood Hub deployments (GiveDirectly and partners).
- **A live scientific dispute.** An independent evaluation (Li et al. 2026, *Journal of Hydrology X*)
  reports very high error rates for extreme events; it is methodologically contested (it evaluates
  against observation-based thresholds rather than the model's own). The case uses it only to motivate
  an *interaction-layer* issue (reliability limits not surfaced to the user), and anchors that issue
  additionally in the Nature paper's own statement that local reliability is not predictable.

## Results

**These numbers are outside the pre-registered aggregate.** The canonical product number
(recall 0.91 ± 0.055 over the 9 testimony cases, [RESULTS-testimony.md](RESULTS-testimony.md)) is
frozen and **does not change**: this case was added *after* pre-registration and is reported on its
own, whatever it says, as an honest out-of-domain probe.

Run on 2026-07-08 with the independent judge (generator Haiku, judge Sonnet), k=3, over the 10
GoldenIssues. Raw runs in `docs/floodhub/consolidado.json`.

| Approach | k | Recall | Precision | Genericity | Primary (F2*) |
|---|---|---|---|---|---|
| b1 (single prompt) | 3 | 0.27 +/- 0.38 | 0.33 +/- 0.47 | 0.00 | 0.28 +/- 0.39 |
| **p3 (pipeline)** | 3 | **0.90 +/- 0.08** | **1.00 +/- 0.00** | 0.00 | **0.92 +/- 0.07** |

Read it two ways. First, **p3 holds out of domain**: recall 0.90 on a climate early-warning system is
essentially the pre-registered multi-sector figure (0.91), with precision 1.00 and zero genericity. The
method was built on clinical cases and prompts and did not overfit to them. Second, **the pipeline earns
its keep here more than anywhere**: b1 (a single prompt) collapsed to **0 findings in 2 of its 3 runs** on
this dense dossier (recall 0.27, huge variance), while p3 stayed at 0.80-1.00 across runs (per-run detail
in the raw file). p3 also surfaced **7-8 grounded problems per run beyond the 10** in the answer key
(`tp_new`): real interaction issues that were not catalogued.

Not run in this pass: the testimony ablation (recall with vs without the user voice). It needs a
with/without-voice re-run and is left as future work for this case.

### Reproduce

```bash
# Dossier is reproducible from the filled templates:
uv run interaction-review ingest \
  --profile     data/external/google-flood-hub/raw/01_ficha_sistema__perfil_tecnico.md \
  --experience  data/external/google-flood-hub/raw/02_experiencia_uso__decisor.md \
  --experience  data/external/google-flood-hub/raw/02b_experiencia_uso__poblacion.md \
  --inventory   data/external/google-flood-hub/raw/03_inventario_documentos.md \
  --out         data/external/google-flood-hub/dossier.json

# Demo report (HTML, with the regulatory crosswalk):
uv run interaction-review review --dossier data/external/google-flood-hub/dossier.json \
  --approach p3 --crosswalk --format html --out docs/demo/google-flood-hub-review.html

# Metrics (independent LLM judge), k=3:
uv run interaction-review compare \
  --dossier data/external/google-flood-hub/dossier.json \
  --golden  data/external/google-flood-hub/answer_key.json \
  --approaches b1,p3 --k 3 --save docs/floodhub/consolidado.json
```

## Sources

See [raw/00_LEEME_enfoque.md](../data/external/google-flood-hub/raw/00_LEEME_enfoque.md) and the case
entry in [casos-externos.md](../data/external/casos-externos.md) for the full, cited source list.
