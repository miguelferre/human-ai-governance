# data/

Convención de privacidad (ver [ADR-003](../docs/adr/ADR-003-manejo-datos-phi.md)):

- `data/golden/` — **PRIVADO, gitignored.** El caso clínico real (dossier
  de-identificado) y el answer key (`GoldenIssue`). Lo aporta el usuario; no se
  busca fuera. El sistema NO ve el answer key durante la ejecución ciega.
- `data/private/` — **PRIVADO, gitignored.** Cualquier otro material sensible.
- `data/examples/` — material de ejemplo **no sensible y versionable** (p. ej. un
  dossier sintético de juguete para probar la CLI).

Solo `data/examples/` y este README se versionan.
