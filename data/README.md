# data/

Privacy convention (see [ADR-003](../docs/adr/ADR-003-phi-data-handling.md)):

- `data/golden/` (**PRIVATE, gitignored**). The real clinical case (de-identified
  dossier) and the answer key (`GoldenIssue`). Provided by the user; not sought
  externally. The system does NOT see the answer key during the blind run.
- `data/private/` (**PRIVATE, gitignored**). Any other sensitive material.
- `data/examples/`, **non-sensitive, versionable** example material (e.g. a toy
  synthetic dossier to test the CLI).

Only `data/examples/` and this README are versioned.
