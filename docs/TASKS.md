# Pending tasks

Planned project work. Status as of 2026-07-02. The "rigor" work **is a selling point** (not
defensive backup): it is what closes out the result in [RESULTS-testimony.md](RESULTS-testimony.md).

## Rigor of the results

- [x] **2-3 more hard cases** (golden from an external human source + raw dossier + hands separated),
      like Robodebt (0.90). DONE: **MiDAS** (Michigan, welfare/unemployment; 7/9 = 0.78) and **Arkansas
      ARChoices** (healthcare/disability; 7/10 = 0.70), built with hands separated and web search over
      cited public sources (audits, rulings, press). **Hard test n=3: average ~0.79** (Robodebt
      0.90 was the high extreme). Cases in `data/external/{midas-michigan,arkansas-medicaid}/`; consolidated in
      `docs/casos-duros/`. Detail in [RESULTS-testimony.md](RESULTS-testimony.md).
- [x] **Reproducible code run.** DONE with the code-pipeline `compare` (cloud backend: gen Haiku /
      **independent** Sonnet judge), k=1, over the 9 cases with testimony. **Result: p3 (product)
      recall 0.93 ± 0.09, precision 0.96; b1 0.68; b0 0.00 (canary).** It confirms, without the circularity of the
      assisted method, the previous signal (which gave ~0.96-1.00). Notable: in MiDAS b1=0.00 but p3=0.89 ("hard
      case -> structure is needed"). Consolidated and raw in `docs/pipeline-codigo/`; detail in
      [RESULTS-testimony.md](RESULTS-testimony.md). It closes the honest note on method.
      **k=3 (2026-07-02):** repeated with 3 passes per approach and case; it confirms that the averages do not
      move (p3 0.91 ± 0.055 recall / 0.965 precision) and narrows the spread across cases (0.086 -> 0.055).
      It adds the intra-case stability that k=1 did not measure: p3 ±0.043 vs b1 ±0.152 (the pipeline is 3-4x more
      consistent than the single prompt). `consolidado_k3.json` + raws `*_k3.json`.

## Product

- [x] **Targeted ablation of the testimony.** DONE in full
      ([RESULTS-ablation-testimony.md](RESULTS-ablation-testimony.md), [ADR-007](adr/ADR-007-testimony-ablation.md)).
      Scaffolding (`revealed_by` field, `ablation.without_voice`, `metrics.recall_by_revealed_by`, `scripts/ablacion_report.py`),
      labeling of the 9 goldens and **run of the voice vs no-voice effect** (within-subject, blind generator +
      independent judge; data in `docs/ablacion-voz/consolidado_k1.json`). **Result:** (1) ceiling, 16/83 (19%) of
      the problems are revealed only by the voice, systematically the cognitive ones; (2) effect, the recall of
      `user_only` drops **0.83->0.33 without voice** (Δ−0.50), with flat controls (both −0.05, tech_only does not even drop):
      the testimony **discovers** the cognitive layer, it does not just reinforce it. It confirms the pre-registered prediction.
      Assisted run (subagents), k=1. **Redone with the code-pipeline and k=3 (2026-07-02):** it confirms the
      direction (user_only 0.83->0.56, flat controls) but recalibrates the magnitude relative to the assisted run
      (−0.28 vs −0.50): the Haiku generator infers part of the cognitive layer from the documentation. The purely
      lived aspects (deference, burden of proof, trust) drop to zero without voice in both. `docs/ablacion-voz/consolidado_k3.json`;
      detail in [RESULTS-ablation-testimony.md](RESULTS-ablation-testimony.md).
- [x] **Semi-automate the dossier.** OFFLINE part DONE: `ingest.py` converts the filled-in templates
      (01/02/03) into a validated, deterministic `Dossier`, with no API (`interaction-review ingest --profile … --experience …`).
      It extracts name/domain from the profile, admits several technical/user roles (distinct ids), pulls the documents
      marked in the inventory, and assigns the correct `kind` per template. Verified end-to-end against the real
      format (templates -> dossier -> `review`). 9 tests. **SMART part (API) DONE (MVP):** `smart_ingest.py` +
      `interaction-review prefill` convert an arbitrary document (PDF/model card) into a prefilled
      template with ONE call to the LLM (structured output). ADR-004 split: the mechanical part (reading the PDF with `pypdf`,
      locating the gaps ✍️, reconstructing the markdown) in code; the model only handles the mapping, with the rule of not
      inventing (a question with no support in the document -> empty gap). The human reviews before `ingest`. Verified
      end-to-end against cloud (Haiku) over a synthetic model card, closing the loop with `ingest`; 10 deterministic
      tests (LLM monkeypatched), incl. the prefill -> `extract_answers` round-trip. Both templates verified
      end-to-end against cloud with a natural source: `profile` (01) from a PDF/model card, and
      `experience` (02) from a transcript of a user interview (both close the loop with
      `ingest`). The `inventory` (03) is a checklist + logistical data, not narrative info: it does not fit
      with prefill and is filled in by hand; `--type` was restricted to profile/experience (with `--template`
      remaining to force any template).
- [x] **Presentable report** (HTML), DONE. `report_html.render_findings_html`: self-contained report
      (embedded CSS, no network dependencies), sober editorial design for healthcare governance, prints to
      PDF (`@media print`). Escapes all free text (anti-injection). `review --format html`
      (combines with `--crosswalk`). Verified in browser. 8 tests (incl. HTML escaping).

## Narrative / commercial

- [x] **Mapping to regulatory framework** (EU AI Act / NIST AI RMF), DONE ([ADR-008](adr/ADR-008-regulatory-mapping.md)).
      `guidelines/regulatory_map.yaml` maps the 30 HAX/PAIR guidelines to AI Act articles (13, 14 incl.
      14(4)(b) automation bias, 15, 26, 50, 86…) and NIST subcategories; `review --crosswalk` appends to the report
      which requirements the findings touch. Indicative, not a legal ruling (disclaimer in YAML/report/ADR).
      Integrity test: all guidelines mapped, no phantom ids. It turns the academic report into
      situated evidence of conformity. Narrative extension, not an engine one.
- [x] README that sells the product (done 2026-06-30).
