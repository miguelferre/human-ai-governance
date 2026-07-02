# Tareas pendientes

Trabajo planificado del proyecto. Estado a 2026-07-02. Lo de "rigor" **se saca de cara** (no es
respaldo defensivo): es lo que cierra el resultado de [RESULTADOS-testimonio.md](RESULTADOS-testimonio.md).

## Rigor de los resultados

- [x] **2-3 casos duros más** (golden de fuente humana externa + dossier en bruto + manos separadas),
      como Robodebt (0.90). HECHO: **MiDAS** (Michigan, bienestar/desempleo; 7/9 = 0.78) y **Arkansas
      ARChoices** (sanidad/discapacidad; 7/10 = 0.70), construidos con manos separadas y búsqueda web sobre
      fuentes públicas citadas (auditorías, sentencias, prensa). **Test duro n=3: media ~0.79** (Robodebt
      0.90 era el extremo alto). Casos en `data/external/{midas-michigan,arkansas-medicaid}/`; consolidado en
      `docs/casos-duros/`. Detalle en [RESULTADOS-testimonio.md](RESULTADOS-testimonio.md).
- [x] **Corrida-código reproducible.** HECHA con el pipeline-código `comparar` (backend nube: gen Haiku /
      juez Sonnet **independiente**), k=1, sobre los 9 casos con testimonio. **Resultado: p3 (producto)
      recall 0.93 ± 0.09, precisión 0.96; b1 0.68; b0 0.00 (canario).** Confirma —sin la circularidad del
      método asistido— la señal previa (que daba ~0.96–1.00). Notable: en MiDAS b1=0.00 pero p3=0.89 ("caso
      difícil → hace falta estructura"). Consolidado y crudos en `docs/pipeline-codigo/`; detalle en
      [RESULTADOS-testimonio.md](RESULTADOS-testimonio.md). Cierra la nota honesta de método.

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
- [x] **Semi-automatizar el dossier.** Parte OFFLINE HECHA: `ingest.py` convierte las plantillas rellenas
      (01/02/03) en un `Dossier` validado, determinista, sin API (`interaction-review ingerir --ficha … --experiencia …`).
      Extrae nombre/dominio de la ficha, admite varios técnicos/usuarios (ids distintos), saca los documentos
      marcados del inventario, y asigna el `kind` correcto por plantilla. Verificado end-to-end contra el formato
      real (plantillas → dossier → `revisar`). 9 tests. **Parte INTELIGENTE (API) HECHA (MVP):** `smart_ingest.py` +
      `interaction-review prerrellenar` convierten un documento arbitrario (PDF/model card) en una plantilla
      prerrellena con UNA llamada al LLM (structured output). Reparto ADR-004: lo mecánico (leer el PDF con `pypdf`,
      localizar los huecos ✍️, reconstruir el markdown) en código; al modelo solo el mapeo, con la regla de no
      inventar (pregunta sin soporte en el documento → hueco vacío). El humano revisa antes de `ingerir`. Verificado
      end-to-end contra nube (Haiku) sobre una model card sintética, cerrando el círculo con `ingerir`; 10 tests
      deterministas (LLM monkeypatcheado), incl. el round-trip prerrelleno → `extract_answers`. Mecanismo genérico
      a las tres plantillas (`--tipo`); verificada la ficha (01). Pulido: extender/verificar 02 y 03.
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
