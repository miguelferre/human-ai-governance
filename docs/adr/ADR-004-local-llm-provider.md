# ADR-004: LLM provider, local backend (Ollama) in addition to cloud (Anthropic)

- **Status:** Accepted
- **Date:** 2026-06-27

## Context

The engine needs an LLM for B1/B2 and for the judge. The cloud (Anthropic) offers
maximum capability and reliable tool-use, but sends the dossier outside the machine
(ADR-003). For a clinical case, running **locally** eliminates that category of risk
and fits the project's governance angle. The user has capable hardware
(RTX 5080 Laptop, 16 GB VRAM; 64 GB RAM) and chose local.

## Decision

Support **two backends** behind a single interface (`llm.call_structured`),
selectable by environment (`LLM_BACKEND`):

- **`anthropic`** (cloud): forced tool-use. Useful as a "reference ceiling" of
  capability and for interpreting the local results.
- **`ollama`** (local, default in this phase): calls to `/api/chat` with
  **structured output via `format` (JSON-schema)**, constrained decoding that
  guarantees valid JSON even in small models (Gemma is not reliable at
  tool-calling, so tool-use is NOT used locally).

Default local models (override with `GEN_MODEL`/`JUDGE_MODEL`):

- **Generator:** `qwen2.5:14b` (instruct), fits entirely in 16 GB, fast, strong at
  instruction following and JSON.
- **Judge:** `qwen2.5:14b`, the only model that **fits entirely in 16 GB of VRAM** and
  at the same time **judges well** (verified: matches 5/5).
  - **Why not `qwen2.5:32b`** (ideal judge by capability): it weighs ~24 GB, does NOT fit
    in 16 GB, and Ollama overflows it to shared memory over PCIe. A `k=3` run took
    ~4 h crawling without finishing. **Unusable for iterating** on this hardware.
  - **Why not `gemma3:12b`** (fits in VRAM): it was tried as judge and **failed the
    matching** (labeling everything `tp_new` even while recognizing the correspondence in
    its reasoning). Too weak.
  - **Independence (ADR-002):** generator and judge end up being the same model. It is a
    conscious compromise, mitigated because the judge matches against a fixed truth (the
    golden), it does not "score freely". An **independent re-judgment** over the already
    saved findings remains available with another family that also fits (e.g. `phi4:14b`),
    without needing to re-generate.

### Design finding: the ORDER of schema fields matters

With constrained decoding (`format`), the model generates the JSON fields in the
schema order. If `label` comes before the reasoning, the model **decides the label
blind** and then writes a rationale that contradicts it (observed: it reasoned
"corresponds to GI-03" but labeled `tp_new`). Reordering (`judge_rationale` first)
helped with B1, but **with B2 (12 findings per call) the model regressed**: it kept
labeling `tp_new` even while naming the correct golden in its rationale. This
underestimated recall and inflated variance (it was a judge artifact, not the generator).

**Robust fix:** the model no longer emits the label. It gives atomic sub-answers
(`corresponde_a_golden`, `es_generico`, `es_real`) and the **label is derived in code**
(`judge.py`). This way it cannot contradict itself. General lesson: with structured
output, do not ask for a conclusion that depends on a reasoning it has not yet written;
ask for atomic facts and compose the conclusion yourself.

**Third hardening (structural genericity):** in one run the judge started matching
the B0 items (checklist with EMPTY locus/evidence) to golden BY THE CITED GUIDELINE,
contaminating the floor (B0 recall 0.80). Cause: in the derivation, a guideline match
beat genericity. Fix: **hard gate in code**, a finding without anchoring
(`is_grounded()==False`) is `fp_generic` ALWAYS, before looking at the judge; only
anchored ones are adjudicated. **B0 is the canary**: if B0 scores > 0, the measurement
is broken. Pattern: move to code every judgment that can be deterministic; leave the
model only what requires criteria.

### Addendum (2026-06-29): the validation battery was run in the CLOUD

The local 14B became unusable for a large battery (~10-30 min/call when the machine
is in use; runs paused by suspension). Decision: **keep local as a "runs on your
hardware" proof, but run the validation battery (held-out, k=3, external cases) in
the CLOUD (Claude: `GEN_MODEL` Haiku, `JUDGE_MODEL` Sonnet)**. The data allows it:
the clinical case goes de-identified and the held-out ones are public (ADR-003). It
was also **key to the conclusion**: locally (weak model) the agent lost; in the cloud
(strong model) the agent is justified -> the answer depends on the model's capability
(see docs/RESULTS.md). Added robustness for the cloud backend: Anthropic's tool-use
does not guarantee the structure the way local `format` does, so non-dict items are
filtered out. The key lives in `.env` (gitignored).

`OLLAMA_NUM_CTX` (default 16384) avoids truncating the dossier + guideline catalog.

## Consequences

- **Privacy:** locally the data does not leave the machine; the de-identification
  pressure from ADR-003 is relaxed (though the hygiene of not putting in PHI is kept).
- **Capability confound:** a weak local model may fail due to capacity, not because the
  approach does not work. Mitigation: use the most capable local model the hardware
  allows and, optionally, a run with Anthropic as a reference ceiling.
- **Reversible / no lock-in:** all OpenAI-compatible runtimes (Ollama, LM Studio,
  llama.cpp-server, vLLM) work with the same code; Ollama was chosen for minimal
  friction on Windows and `format` with JSON-schema.
- **Reproducibility:** fixed weights + seed are possible locally; models and `k` are
  logged per run (ADR-002).
