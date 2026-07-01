# Tareas pendientes

Trabajo planificado del proyecto. Estado a 2026-06-30. Lo de "rigor" **se saca de cara** (no es
respaldo defensivo): es lo que cierra el resultado de [RESULTADOS-testimonio.md](RESULTADOS-testimonio.md).

## Rigor de los resultados

- [x] **2-3 casos duros más** (golden de fuente humana externa + dossier en bruto + manos separadas),
      como Robodebt (0.90). HECHO: **MiDAS** (Michigan, bienestar/desempleo; 7/9 = 0.78) y **Arkansas
      ARChoices** (sanidad/discapacidad; 7/10 = 0.70), construidos con manos separadas y búsqueda web sobre
      fuentes públicas citadas (auditorías, sentencias, prensa). **Test duro n=3: media ~0.79** (Robodebt
      0.90 era el extremo alto). Casos en `data/external/{midas-michigan,arkansas-medicaid}/`; consolidado en
      `docs/casos-duros/`. Detalle en [RESULTADOS-testimonio.md](RESULTADOS-testimonio.md).
- [~] **Corrida-código reproducible.** El recall de los casos con testimonio ya se midió de forma
      **asistida** (generador ciego + juez independiente, roles y modelos separados). **Falta** correrlo con
      el pipeline-código `comparar` para el número reproducible no asistido; necesita la API key (o rehacerlo
      con subagentes replicando el protocolo del pipeline). Cierre de la nota honesta de RESULTADOS-testimonio.

## Producto

- [x] **Ablación dirigida del testimonio.** HECHA entera
      ([RESULTADOS-ablacion-testimonio.md](RESULTADOS-ablacion-testimonio.md), [ADR-007](adr/ADR-007-ablacion-del-testimonio.md)).
      Andamiaje (campo `revealed_by`, `ablation.without_voice`, `metrics.recall_by_revealed_by`, `scripts/ablacion_report.py`),
      etiquetado de los 7 goldens y **corrida del efecto voz vs sin-voz** (within-subject, generador ciego +
      juez independiente; datos en `runs/ablacion_voz_k1.json`). **Resultado:** (1) techo — 12/64 (19%) de
      los problemas solo los revela la voz, sistemáticamente los cognitivos; (2) efecto — el recall de
      `user_only` cae **0.83→0.33 sin voz** (Δ−0.50), con controles planos (both −0.05, tech_only ni baja):
      el testimonio **descubre** la capa cognitiva, no solo la refuerza. Confirma la predicción pre-registrada.
      Corrida asistida (subagentes), k=1; la varianza con k=3 y el pipeline-código quedan como pulido.
- [~] **Semi-automatizar el dossier.** Parte OFFLINE HECHA: `ingest.py` convierte las plantillas rellenas
      (01/02/03) en un `Dossier` validado, determinista, sin API (`interaction-review ingerir --ficha … --experiencia …`).
      Extrae nombre/dominio de la ficha, admite varios técnicos/usuarios (ids distintos), saca los documentos
      marcados del inventario, y asigna el `kind` correcto por plantilla. Verificado end-to-end contra el formato
      real (plantillas → dossier → `revisar`). 9 tests. **Falta (API):** ingerir documentación arbitraria (PDFs,
      model cards) de forma inteligente → plantillas prerrellenas; eso sí necesita LLM.
- [x] **Informe presentable** (HTML) — HECHO. `report_html.render_findings_html`: informe autocontenido
      (CSS embebido, sin dependencias de red), diseño editorial sobrio para gobernanza sanitaria, imprime a
      PDF (`@media print`). Escapa todo el texto libre (anti-inyección). `revisar --format html`
      (combina con `--crosswalk`). Verificado en navegador. 8 tests (incl. escapado de HTML).

## Narrativa / comercial

- [x] **Mapeo a marco normativo** (EU AI Act / NIST AI RMF) — HECHO ([ADR-008](adr/ADR-008-mapeo-normativo.md)).
      `guidelines/regulatory_map.yaml` mapea las 30 guidelines HAX/PAIR a artículos del AI Act (13, 14 —incl.
      14(4)(b) automation bias—, 15, 26, 50, 86…) y subcategorías NIST; `revisar --crosswalk` anexa al informe
      qué requisitos tocan los hallazgos. Orientativo, no dictamen legal (disclaimer en YAML/informe/ADR).
      Test de integridad: todas las guidelines mapeadas, sin ids fantasma. Convierte el informe académico en
      evidencia de conformidad situada. Extensión de narrativa, no del motor.
- [x] README que vende el producto (hecho 2026-06-30).

## Seguridad

- [ ] **Rotar la API key de Anthropic.** Quedó expuesta en el chat y el `.env` actual da 401: generar una
      nueva en console.anthropic.com y revocar la vieja.
