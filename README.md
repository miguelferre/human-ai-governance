# Human-AI Interaction Layer Reviewer

> **Audit an AI system's dashboard, not its engine.**

![The ecosystem around the human-AI interaction layer: data feeds the model; the model drives connected tools and guides the person; the person acts and adapts; outcomes loop back to improve the model, all under a governance layer.](docs/assets/human-ai-ecosystem.jpg)

When an AI helps a person make a decision (a doctor, a pilot, a caseworker), the point where things
most often go wrong is usually not the model itself but **how the system talks to that person**:
whether it presents the result in a way that invites over-trust, whether it can be corrected, whether
the alert fires at the right moment. This tool audits that layer, the interaction layer, and returns a
list of concrete problems, each anchored to a recognized design guideline and to the evidence that
supports it.

A plain-language overview is in **[docs/PRODUCT.md](docs/PRODUCT.md)**.

## The problem: the engine gets audited, the dashboard does not

It is easiest to see with a car. When buying one, everyone looks at the engine: power, fuel use,
emissions. That is measured and regulated down to the last bolt. Almost nobody asks whether the
dashboard is well designed: whether the blind-spot warning fires when it should or distracts right as
the driver turns, whether an alert that keeps showing can be silenced, whether the driver understands
what the car is saying or trusts it blindly.

The same holds for AI. Today's governance tools (watsonx.governance, Fiddler, Arize) audit the engine:
bias, accuracy, drift, technical explainability. Almost nobody looks at the dashboard, how the result
is presented to the person, which is exactly where over-trust in the machine, alert fatigue, the
uncaptured override, and mistimed prompts creep in. That is where a professional decides whether to
trust the model, correct it, or ignore it. Today this is reviewed by hand, in a spreadsheet. This
project automates it.

## What it does

Given a description of a system (what it does, how it is shown to the user, and **what the people who
use it report**), it returns a list of problems in that layer. Not textbook problems: every finding is
**anchored to three things**:

1. a **recognized design guideline** it breaks,
2. the **specific point** in the system where it happens,
3. the **evidence** taken from the system's own documentation.

If a finding cannot be supported by evidence, it is not reported. A report full of "improve
explainability" is useless, because it fits any system. This one points to "here, on this screen, the
score appears pre-filled and pushes the clinician to accept it without thinking." That is actionable.

The guidelines come pre-digested: it uses Microsoft's 18 (**HAX-18**) and Google's guidebook
(**PAIR**), the de facto standard, translated into concrete findings. No prior knowledge of them is
required.

## How it works

The system is fed by **three templates** filled in by the stakeholders, turns them into a case file (a
*dossier*), and generates the report from it.

### The three templates

- **[Technical profile](templates/01_system_card__technical_profile.md)**: whoever builds or maintains the system.
- **[Usage experience](templates/02_usage_experience__end_user.md)**: **the end user**. This is the piece nobody else audits, the real testimony of whoever lives with the AI (do they accept it out of inertia? can they correct it? do they ignore it?).
- **[Document inventory](templates/03_document_inventory.md)**: what documentation is available.

Those three answers **are** the input. The differentiator is the second one: contrasting what the
technical team *believes* happens with what the user *experiences*, because that mismatch is itself a
signal about the interaction layer.

### From input to report

There is no JSON to edit. The templates are filled in Markdown and `ingest` builds the case file on its
own, so preparing the input does not cost as much as auditing by hand. Already have a PDF, a model card,
or an interview transcript? `prefill` passes it to the model to fill the template (the technical profile
from the technical document, the usage experience from the interview) with what is actually there, and
only that: whatever is missing is left blank, not made up. The human reviews and corrects, and from
there to `review`, which generates the findings report.

### Deterministic by default, model only where needed, and local if wanted

The work is split on purpose: **the mechanical parts in code, the model only for what cannot be done
with rules**.

- **No language model, deterministic** (same result every time, offline): turning the templates into the
  case file (`ingest`), consolidating duplicates (`dedup`), the regulatory mapping (`crosswalk`), the
  HTML report, the metrics, and the **B0** approach, a checklist that serves as a control floor.
- **Need a model**: generating the findings from the case file, the smart template pre-fill, and the
  judge that scores the evaluation. This is the irreducible link: detecting an interaction problem and
  anchoring it in evidence cannot be done with a rule.

And that model **can be local**: with `LLM_BACKEND=ollama` the whole pipeline runs on the user's machine
with an open model (qwen, gemma...), without any data leaving for the cloud. That is what is wanted when
privacy is paramount.

## Does it work?

Yes, and it is measured, not promised, against public cases documented by independent sources. The corpus
spans **8 sectors** (healthcare, aviation, justice, finance, public administration, HR, welfare,
disability); the table reports the specific experiments run on subsets of it:

| Test | Result |
|---|---|
| Real clinical case (golden set from a human expert) | rediscovers **13-14 of 15** problems, ~100% precision |
| **5 held-out** cases from independent sources (Epic Sepsis, HireVue, COMPAS, MCAS-aviation, moderation) | recall **0.80-1.00**, not overfitting |
| **Well-designed** system (false-positive control) | **0 findings**, does not invent to look productive |
| Phrasing robustness (same case, different words) | stable recall, understands rather than keyword-matches |
| **Hard test**, n=3: golden set from an independent body (a Royal Commission, a state auditor, a federal court) + raw dossier, separate hands | recall **0.70-0.90** (mean ~0.79): recovers what they flagged without seeing it |
| **Product number**, over the **9 testimony cases**, with the reproducible pipeline and an **independent judge** (a different model), k=3 | p3: recall **0.91 ± 0.055**, precision **0.965** |

The last one matters most, because it is not scored by the same engine that generates it: the judge is a
different model and the flow is reproducible. And it does so with a **cheap** generator model. Run three
times per case, the number holds and the spread across cases narrows, so it was not a fluke of a single
run.

**And the testimony is not a hunch, it is measured.** Removing the user's voice from the case file and
leaving only the technical documentation, the reviewer loses recall precisely on the problems that only
that voice reveals: it drops from **0.83 to 0.56**, while the controls do not move. And the most
experiential ones, deference to the machine, feeling guilty in front of the system, eroded trust, drop
**to zero** without the voice, because no technical spec hints at them. How far the aggregate falls
depends on how much the generator infers from the documentation itself (with a more conservative model
the drop reached 0.33), but the hard core, what the person lives through, is brought only by the voice.
That is the differentiator's argument, now with data.

Detail and method: **[docs/RESULTS.md](docs/RESULTS.md)** (the experiment) ·
**[docs/RESULTS-testimony.md](docs/RESULTS-testimony.md)** (cases with real testimony, hard test n=3, and
the reproducible number) · **[docs/RESULTS-ablation-testimony.md](docs/RESULTS-ablation-testimony.md)**
(the effect of the voice).

## In the language of whoever signs the purchase

HAX and PAIR are the design standard, but whoever approves the purchase (governance, quality, compliance)
does not reason in HAX-G2, they reason in the AI Act and NIST. So the report translates itself. With
`--crosswalk`, each finding also comes mapped to the articles of the **EU AI Act** (Article 13 on
transparency, Article 14 on human oversight, which names *automation bias* explicitly, Article 86 on the
right to explanation) and to the subcategories of the **NIST AI RMF**. It stops being a design critique
and becomes conformity evidence that goes into their file. It is indicative, not a legal ruling, and the
report says so itself. And when it needs to be shown, `--format html` produces a self-contained,
presentable report that prints to PDF without depending on anything external.

To be precise: this is an **audit for governance**, not a system that governs in real time. It produces
the evidence that feeds the compliance file and the decision on what to fix. It does not stay watching
the system or intervene on its own (see [What it is and what it is not](#what-it-is-and-what-it-is-not)).

## An experiment with method, not hype

The starting question was not "how do I build the agent" but **whether one is needed**. Before building
anything large, simple baselines were set and measured: complexity is justified only if it **wins
measurably**.

- Ladder: **B0** deterministic checklist, **B1** single prompt, **P3** deterministic pipeline, **A4** agent.
- Conclusion, a map rather than a single winner: the **deterministic pipeline + dedup** is the robust
  option. The **modern agent does not pay for itself**: it ties in the best case but loses when the input
  degrades (the norm in an audit).
- Cross-cutting lesson: the fragile link was the **LLM judge** (the measurement), not the generator, so the
  measurement was hardened with deterministic guardrails in code.

Design decisions in **[docs/adr/](docs/adr/)**; validation plan and honest limitations in
**[docs/TESTPLAN.md](docs/TESTPLAN.md)**.

## What it is and what it is not

So that no one gets the wrong idea:

- **It is an audit, not real-time governance.** It gives a rigorous snapshot of the interaction layer at a
  given moment, with actionable findings. It does not stay attached to the system watching it, nor does it
  intervene on its own. Its place is to feed governance, not replace it.
- **The testimony captures what the person lives through and can articulate, not what they do not even
  perceive.** That is both its strength and its honest limit: someone with over-trust in the machine who is
  not aware of it will not narrate it, and there the interview does not reach. The natural complement is
  **objective telemetry**: how long they take to accept a recommendation versus how long reading it would
  take, the real correction rate, how many alerts they ignore. Today that can be supplied as usage logs
  (template 03); integrating it as a source that is cross-checked against the rest is the direction the
  product grows in.
- **It gives the snapshot; the loop is not yet closed.** The report is a list of anchored problems.
  Recording what was fixed and measuring again to show the risk went down is the next step, not yet built.
- **Generating the findings needs a language model**, and that is on purpose (it is the irreducible part),
  not an accidental dependency. Everything else is deterministic and runs offline; the model, moreover, can
  be local. So "nothing works without the API" is false: ingestion, dedup, crosswalk, HTML, and the B0
  canary all run without a connection.

## Installation

```bash
uv sync --extra dev
```

## Usage

```bash
# (Optional) From a document to a pre-filled template with the model (review it afterwards):
uv run interaction-review prefill --doc path/model_card.pdf --type profile    --out templates/01_filled.md
uv run interaction-review prefill --doc path/interview.txt  --type experience --out templates/02_filled.md

# From the three filled templates to the case file (deterministic, no API):
uv run interaction-review ingest \
    --profile templates/01_filled.md --experience templates/02_filled.md \
    --inventory templates/03_filled.md --out path/dossier.json

# Findings report, with the regulatory mapping and in HTML ready to print to PDF:
uv run interaction-review review --dossier path/dossier.json --approach p3 --dedup \
    --crosswalk --format html --out report.html

# 'auto' (product router): b1 if the case is easy, p3+dedup if it is hard:
uv run interaction-review review --dossier path/dossier.json --approach auto

# Metrics against a golden set (with LLM judge):
uv run interaction-review compare \
    --dossier path/dossier.json --golden path/answer_key.json \
    --approaches b0,b1,p3 --k 3 --save runs/output.json
```

Approaches: `b0` (checklist, no model) · `b1` (single prompt) · `p3` (pipeline, **the product**) ·
`a4` (agent). `--dedup` consolidates near-duplicates (deterministic); `--dedup-llm` is the optional
semantic layer (uses the model). `--crosswalk` adds the mapping to EU AI Act / NIST; `--format html`
produces the presentable report. The `compare` command requires `ANTHROPIC_API_KEY` (except for `b0`
alone), or runs entirely local with `LLM_BACKEND=ollama`.

> **Local / Windows.** To run locally with [Ollama](https://ollama.com) prefix `LLM_BACKEND=ollama`.
> If Windows Application Control blocks the `.exe` launcher, invoke the module directly:
> `uv run python -m interaction_review.cli ...`.

## Layout

```
src/interaction_review/
  schemas.py        Data contract (Dossier, Finding, GoldenIssue, ...)
  guidelines/       HAX-18 and PAIR as linkable data + regulatory_map.yaml (AI Act / NIST)
  approaches/       Approach ladder (b0/b1/b2/p3/p3n/a4)
  ingest.py         Filled templates -> case file (deterministic, no API)
  smart_ingest.py   Document (PDF/model card/interview) -> pre-filled template (model; human reviews)
  dedup.py          Deterministic finding consolidation (product)
  dedup_llm.py      Optional semantic layer (model)
  router.py         'auto' routing by difficulty
  regulatory.py     Crosswalk of findings to EU AI Act / NIST AI RMF
  ablation.py       Testimony ablation (case file with voice vs without voice)
  metrics.py        recall, precision, genericity, grounding, F-beta, recall by source
  report.py         Markdown report · report_html.py self-contained HTML report
  cli.py            Commands prefill / ingest / review / evaluate / compare
docs/adr/           Design decisions (ADR-001..008)
data/external/      Public held-out cases (dossier + golden per case)
data/golden/        PRIVATE, gitignored (real clinical case)
templates/          The three input templates
```

Note on language: the tooling, documentation, and code are in English. Spanish is kept on purpose in the
evidence layer: the prompts that produced the measured numbers, the case data and result files under
`data/` and `docs/`, and the test fixtures that mirror that domain content. Translating the prompts or the
case data would require re-running the experiments to keep the figures valid.

## Privacy

Clinical material is private and **never versioned** (`data/golden/`, `data/private/`). Cloud model calls
send data out, so the dossier must be **de-identified** before any run with real data (see
[ADR-003](docs/adr/ADR-003-phi-data-handling.md)). When that is not enough, the local backend
(`LLM_BACKEND=ollama`) keeps everything on the machine.

## References

- Amershi et al. (2019), *Guidelines for Human-AI Interaction*, CHI. (HAX-18)
- Google PAIR, *People + AI Guidebook*.
