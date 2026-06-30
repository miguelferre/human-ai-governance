# Plan de pruebas — validez y overfitting de los resultados

Motivado por una pregunta de Miguel: ¿P3 (el pipeline) parece tan bueno por **overfitting**?
Este documento registra la batería de pruebas para distinguir señal real de artefacto, y
para evaluar si esto sirve como **producto** (no solo como ganador de un benchmark de un caso).

## Riesgos de overfitting identificados

- **R-A. Bloques de P3 diseñados a mano** conociendo guidelines/caso → ventaja que no generaliza.
- **R-B. Cantidad, no calidad:** P3 emite ~25 hallazgos vs ~6 de B1 → más tiros a emparejar.
- **R-C. n=1 caso:** todo (dossier, golden, bloques, prompts, juez) se afinó alrededor del caso clínico.
- **R-D. Juez algo indulgente / artefactos del corrector** (ver hallazgo en B2 abajo).
- **R-E. Golden y dossier co-evolucionados** con el equipo evaluador.

## Resultado base a validar (v2, k=1)

B1 (prompt único) 0.38  <  A4 (agente) 0.67  <  P3 (pipeline fijo) 0.80  (todos precisión ~1.00).
Lectura provisional: el pipeline gana; el agente NO se justifica. Falta validar contra los riesgos.

## Batería de pruebas

### A. ¿Generaliza? (lo más importante)
- **A1 — Casos externos held-out.** Buscar en literatura/web casos reales con problemas de
  interacción DOCUMENTADOS por fuentes independientes (golden objetivo, no nuestra interpretación);
  construir dossier + golden y correr B1/P3/A4. Es LA prueba de overfitting. _Estado: ✅ HECHO — **5
  held-out en 3 dominios**._
  - Epic Sepsis (clínico distinto) + HireVue (RRHH) — 2026-06-29.
  - **COMPAS** (justicia), **MCAS-aviación** (cabina 737 MAX) y **moderación de contenido** — 2026-06-30,
    construidos desde fuentes independientes citadas (dossier ciego neutralizado + golden de 9 issues c/u
    en `data/external/{compas,mcas-aviacion,moderacion}/`). Resultados k=3: P3 0.93-1.00, A4 0.93-1.00,
    B1 0.81-0.96, precisión 0.93-1.0; B0=0. **Overfitting DESCARTADO**: el patrón se reproduce en todos.
    (Son de dificultad media → B1 ya rinde alto; no son casos "difíciles" como EII.)
- **A2 — Bloques alternativos.** Re-correr P3 con una agrupación neutral (4 fases HAX + capítulos
  PAIR, sin mano). Si P3 aguanta, la ventaja es la *descomposición*, no mis bloques. _Estado: ✅ HECHO
  (2026-06-29, EII v2, k=3, nube)._
  - **Resultado:** P3-neutral (`p3n`, 10 buckets DERIVADOS del campo `group`: 4 fases HAX + 6 capítulos
    PAIR, sin diseño a mano) recall **0.89 ±0.03** vs P3-a-mano (`p3`) **0.82 ±0.08**. Precisión 0.99 y
    genericidad 0.00 en ambos.
  - **Lectura:** R-A **DESCARTADO**. La partición neutral iguala/supera a mis bloques → la ventaja es
    *descomponer*, no el diseño manual. `p3n` es además más estable (±0.03). Coste: `p3n` genera ~2×
    hallazgos (102 vs 56/corrida) para el mismo recall → más verboso, pero NO fabrica (precisión intacta).
    Implicación de producto: agrupar por la taxonomía oficial (gratis, robusto) ≥ bloques a mano.

### B. ¿Son reales los números?
- **B1 — ¿Estructura o cantidad?** Un "B1-exhaustivo" (prompt único pidiendo MUCHOS hallazgos, una
  pasada). Si iguala a P3, la ventaja era cantidad; si no, la estructura aporta. _Estado: pendiente._
- **B2 — Adjudicación humana de P3.** _Estado: HECHO (2026-06-29)._
  - **Resultado:** los 12 matches distintos son legítimos → **0.80 real, no inflado**.
  - **Hallazgo importante:** P3 está **infravalorado**. De los 3 "perdidos", GI-13 (onboarding) y
    GI-06 (automation bias) **sí se encontraron**, pero el corrector no los emparejó porque el
    hallazgo citó una guideline distinta de la del golden (sin solape → no candidato). **P3 real
    ≈ 14/15.**
  - **Bug derivado (afecta a todos por igual):** el filtro por guideline del corrector produce
    FALSOS FALLOS cuando el generador cita la guideline "equivocada". Mitigación posible: ampliar
    candidatos por grupo/capítulo o por similitud semántica, no solo por id exacto. Sube el recall
    de todos los approaches; la comparación relativa se mantiene.
  - **ARREGLADO (2026-06-30):** `judge._candidates` ahora ofrece TODOS los golden (los que comparten
    guideline/grupo primero); la "lista corta" era muleta del 14B, no hace falta con juez nube fuerte.
    Sorpresa al medir (re-juzgado control p3, k=3): la media NO sube (0.82→0.82), pero la **varianza
    cae a la mitad (±0.08→±0.03)** con precisión intacta. El "≈14/15" era una corrida con suerte, no
    la media. Es un win de reproducibilidad, no de recall. Detalle en [RESULTADOS.md](RESULTADOS.md).

### C. ¿Es buen producto (no solo gana el benchmark)?
- **C0 — Deduplicado (el paso de producto).** El anti-patrón vivo: P3 emite el mismo problema
  varias veces (a menudo citando guidelines distintas). _Estado: ✅ HECHO (2026-06-30, determinista,
  offline)._ `src/interaction_review/dedup.py` + `scripts/dedup_report.py`; expuesto como
  `revisar --dedup`. Validado sobre runs ya juzgados: **cobertura perdida 0 en 6 escenarios**
  (recall intacto), reducción 13-26% en p3 con impureza ~0, generaliza a los held-out, y no daña
  lo ya conciso (b1/a4).
  - **Capa semántica con LLM — ✅ HECHO (2026-06-30, `dedup_llm.py`, `revisar --dedup-llm`).** Para el
    residual ("mismo problema vía guideline distinta"). Colapsa fuerte (p3: 56→17, 42→15, 41→14, ~un
    hallazgo por problema) y mantiene cobertura, PERO **sobre-funde** (impureza 6/5/9 en k=3). Probados dos
    levers: prompt estricto (apenas movió) y **barandilla en código** (`locus_floor`: el LLM propone, el
    código veta loci dispares) → impureza ~½ (a2 4/Epic 0/HireVue 5) pero se come la conciseness (~28-31 ≈
    determinista). **Trade-off fundamental** → determinista = default; LLM = modo agresivo con repaso.
  - **Enrutado por dificultad (`auto`, `router.py`) — ✅ EXPLORADO (2026-06-30).** b1 + gap-check → escala a
    p3+dedup. El gap-check sobre-escala (3/4) y puede dejar un miss en la rama b1 (HireVue) → la dificultad no
    se infiere limpio a priori; **p3+dedup es el default robusto**. Detalle en [RESULTADOS.md](RESULTADOS.md).
- **C1 — Falsos positivos en un sistema "bueno".** Dar a P3 el dossier de un sistema bien diseñado
  (pocos problemas). ¿Se calla o inventa para llenar bloques? Un auditor que siempre encuentra 25
  fallos es inútil. _Estado: pendiente (requiere dossier sintético de sistema "bueno")._
- **C2 — Robustez al formato de entrada.** Variar el dossier (menos detalle, fraseo distinto) y ver
  si los hallazgos aguantan. _Estado: ✅ HECHO (2026-06-29, EII v2 parafraseado por LLM —misma
  información, prosa narrativa en vez de estilo telegráfico de model-card—, k=3, nube)._
  - **Resultado:** P3 recall **0.78 ±0.03** (parafraseado) vs **0.82 ±0.08** (original, A2); precisión
    1.00 y grounding 1.00. B1 **0.47 ±0.33** (igual de ruidoso que sin parafrasear: 0.44 histórico).
  - **Lectura:** P3 es **robusto al fraseo**: reformular la entrada no cambia su recall ni su precisión
    → entiende el significado, no "pesca" formato/palabras clave. La fragilidad de B1 es intrínseca
    (falta de estructura), no del fraseo. Refuerza P3 como candidato a producto.
- **C3 — El nicho del agente.** A4 vs P3 con **entrada incompleta** (info repartida/ausente): único
  régimen donde la autonomía debería ganar. _Estado: ✅ HECHO (2026-06-29, EII v2 con dossier recortado
  —sin voz de usuario ni logs de producción—, k=3, nube)._
  - **Resultado:** sobre entrada incompleta, **A4 recall 0.62 ±0.08** vs **P3 0.78 ±0.13**. Frente al
    baseline de entrada COMPLETA (A4 0.82, P3 0.78): **P3 NO cae (robusto); A4 se desploma −0.20**.
  - **Lectura (contraintuitiva):** el nicho hipotetizado del agente NO aparece. La entrada incompleta es
    justo donde el **barrido exhaustivo fijo de P3 más gana**: garantiza cobertura cuando la señal es
    escasa y dispersa. A4, al decidir autónomamente cuándo parar, **corta antes** (≈30 hallazgos vs 53 de
    P3) y se deja issues recuperables. A4 mantiene precisión altísima (0.99) pero a costa de recall.
  - **Salvedad → RESUELTA (2026-06-30):** control A4-completo **fresco** sobre EII v2, k=3: **0.80 ±0.09**
    (precisión 1.00) ≈ 0.82 previo. El delta de C3 (A4 completo ~0.80-0.82 vs incompleto 0.62) queda
    **blindado**: la caída de A4 con entrada incompleta es real, no un artefacto de corrida.

### Confirmación con varianza
- **k=3** de los approaches clave (P3 y A4 al menos) una vez cerradas las pruebas anteriores, para
  aplicar la regla `beats` formalmente. _Estado: pendiente (coste alto en máquina local lenta)._

## Estado a 2026-06-29 (ejecutado en NUBE Claude; síntesis en RESULTADOS.md)

- **B2** adjudicación humana de P3: ✅ HECHO (0.80 real, infravalorado; bug del corrector documentado).
- **A1** generalización: ✅ HECHO con **5 held-out en 3 dominios** (HireVue, Epic; + COMPAS, MCAS-aviación, moderación el 2026-06-30) → **NO era overfitting** (patrones reproducidos en todos: P3/A4 0.93-1.00).
- **B1** estructura vs cantidad: ✅ respondido por el mapa — la estructura aporta **reliability** en casos difíciles (B1 inestable, una corrida a 0), no solo cantidad; en casos fáciles B1≈P3. (El approach `b1x` quedó implementado; su corrida local se abortó por lentitud.)
- **C1** falsos positivos en sistema bueno: ✅ HECHO — B1/P3/A4 devuelven **0 hallazgos**; no inventan. La verbosidad de P3 es redundancia, no fabricación.
- **A2** bloques alternativos: ✅ HECHO (R-A descartado: `p3n` neutral 0.89 ≥ `p3` a-mano 0.82; ver arriba).
- **C3** nicho del agente: ✅ HECHO — el nicho NO aparece; con entrada incompleta P3 (exhaustivo) 0.78 > A4 0.62.
- **C2** robustez de entrada: ✅ HECHO — P3 robusto al fraseo (parafraseado 0.78 ≈ original 0.82, precisión 1.00).

**Batería A/C completada (2026-06-29).** A2 (overfitting de bloques) descartado · C3 (nicho del agente)
no aparece, el agente pierde donde debía ganar · C2 (robustez al fraseo) confirmada para P3. Síntesis en
[RESULTADOS.md](RESULTADOS.md).
- **k=3 confirmación**: ✅ hecho en nube (todas las corridas de la tabla son k=3).

**Conclusión validada en [RESULTADOS.md](RESULTADOS.md): mapa condicional** (la complejidad que paga depende de dificultad×modelo), no un ganador único.

## Notas de método
- Máquina local lenta (~10 min/llamada cuando se usa el equipo) → runs en segundo plano con watchdog
  y checkpoint de generación. Suspensión pausa runs (desactivar o vigilar).
- Todo crudo se guarda en `runs/` (gitignored). Material del caso en `data/golden/` (privado).
