# data/

Privacy convention (see [ADR-003](../docs/adr/ADR-003-phi-data-handling.md)):

- `data/golden/` (**PRIVATE, gitignored**). The real clinical case (de-identified
  dossier) and the answer key (`GoldenIssue`). Provided by the user; not sought
  externally. The system does NOT see the answer key during the blind run.
- `data/private/` (**PRIVATE, gitignored**). Any other sensitive material.
- `data/examples/`, **non-sensitive, versionable** example material (e.g. a toy
  synthetic dossier to test the CLI).
- `data/external/`, **public held-out cases (versioned)**: a dossier + answer key
  per case, built from cited public sources (no PHI). They feed the generalization /
  anti-overfitting tests.

`data/examples/`, `data/external/` and this README are versioned; `data/golden/` and
`data/private/` are not.
