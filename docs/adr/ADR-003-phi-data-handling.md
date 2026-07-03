# ADR-003: Data and clinical material handling (PHI)

- **Status:** Accepted
- **Date:** 2026-06-27

## Context

The primary validation case is clinical and private. From F2 onwards, the system
calls a cloud LLM (Anthropic). **A call to the LLM sends the data outside** the
machine: it may remain in the provider's logs or caches even if later deleted.
This is incompatible with sending untreated patient data.

## Decision

- The real clinical material and the golden set live under `data/golden/` and
  `data/private/`, **gitignored**. They are never versioned or published.
- **Mandatory prior de-identification**: before any LLM call with case data, the
  `Dossier` must be free of PHI (no patient identifiers). The dossier describes the
  **system and its interaction**, not specific patients; this makes compliance easier.
- The user provides the necessary material; **nothing is sourced externally**
  (`.gitignore` and this note make it explicit).
- Raw run outputs (`runs/`) are also gitignored in case they carry fragments of the
  dossier.

## Consequences

- If in the future PHI must be processed without de-identification, the deployment
  would have to be revisited (e.g. on-prem LLM or a data-processing agreement) in a
  new ADR.
- The evaluation harness works the same with a de-identified dossier: the interaction
  layer does not need patient data to be audited.
