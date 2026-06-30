# Resultados del experimento — ¿hace falta un agente para revisar la capa de interacción?

Síntesis a 2026-06-30. Detalle de cada corrida en `runs/` (gitignored); plan en
[TESTPLAN.md](TESTPLAN.md); decisiones de diseño en [docs/adr/](adr/).

## La pregunta

¿Para revisar la capa de interacción humano-IA hace falta un **agente**, o basta un
**prompt único** (o incluso una **checklist determinista**)? Regla del proyecto: la
complejidad solo se justifica si **gana de forma medible** al peldaño anterior.

## Método

Escalera de approaches, todos con el mismo contrato (dossier → hallazgos anclados a
HAX-18/PAIR):
- **B0** checklist determinista (sin LLM) · **B1** prompt único · **B2** few-shot ·
  **P3** pipeline determinista (barrido por bloques, NO agente) · **A4** agente (bucle
  donde el MODELO decide qué investigar y cuándo parar).
- Golden set con problemas conocidos; **LLM-juez** que adjudica (recall, precisión,
  genericidad); regla `beats` = margen > ruido entre k corridas.
- Validación contra **overfitting** con casos **held-out** documentados en literatura
  (Epic Sepsis, HireVue) y control de **falsos positivos** en un sistema bien diseñado.

## El mapa de resultados (recall, k=3)

| Caso | Dificultad | Modelo | B1 | P3 | A4 |
|---|---|---|---|---|---|
| EII (clínico) | difícil (15 issues) | qwen2.5:14b local | 0.38 | **0.80** | 0.67 |
| EII (clínico) | difícil (15) | Claude (Haiku/Sonnet) | 0.44 *±0.32 inestable* | 0.78 | **0.82** |
| HireVue (held-out, NO clínico) | fácil (7) | Claude | 0.90 | **1.00** | 0.90 |
| Epic Sepsis (held-out, clínico distinto) | fácil (7) | Claude | **0.95** | 0.95 | 0.86 |
| COMPAS (held-out, NO clínico) | medio (9) | Claude | 0.85 | **1.00** | **1.00** |
| MCAS aviación (held-out, NO clínico) | medio (9) | Claude | 0.96 | 0.93 | 0.96 |
| Moderación (held-out, NO clínico) | medio (9) | Claude | 0.81 | **1.00** | 0.93 |

B0 = 0.00 en todos (suelo). Todos los approaches con LLM: precisión ~0.93-1.0, genericidad 0.
Los tres últimos (held-out 2026-06-30, juez nuevo) son casos públicos documentados por fuentes
independientes; reproducen el patrón → refuerzan "no es overfitting" (ya van **5 held-out**, 3 dominios).

## Conclusión: no es un ganador único, es un mapa

1. **El LLM bate a la checklist siempre.** B0 (genérico por construcción) nunca compite.
2. **Caso fácil + modelo fuerte → el prompt único basta** y es el más conciso. En Epic,
   B1 clava 7/7 con ~11 hallazgos; P3 saca los mismos 7 con ~42 (pura redundancia).
3. **Caso difícil → hace falta ESTRUCTURA.** El prompt único es inestable (en EII-Claude
   una de tres corridas se fue a **0 hallazgos**): no tiene red.
   - **Modelo débil → pipeline (P3)** es lo seguro; la autonomía del agente es ruidosa ahí.
   - **Modelo fuerte → el agente (A4) iguala** al pipeline (0.82 vs 0.78) y es **más conciso**
     (~30 vs ~55 hallazgos) — pero **solo con entrada completa**. Esa ventaja **no es robusta**
     (ver C3 abajo): si la entrada se degrada, A4 se desploma y P3 aguanta.

Es decir: la complejidad que paga **depende de la dificultad del caso y de la capacidad
del modelo**. No "el agente siempre sobra" ni "el agente siempre gana".

## Hallazgos transversales (lo más valioso)

- **El eslabón frágil fue el JUEZ (la medición), no el generador.** Costó 4 iteraciones
  hacerlo fiable; la solución siempre fue **mover el juicio determinista al código** y
  dejar al modelo solo lo irreducible (razonar antes de etiquetar → derivar la etiqueta
  en código → gate estructural de genericidad → candidatos preseleccionados por guideline).
  Para gobernanza de IA es una lección en sí: *fíate del modelo para juzgar, pero pon
  barandillas deterministas*. **B0 es el canario**: si puntúa > 0, la medición está rota.
- **No era overfitting.** **Cinco** held-out en **tres dominios** (Epic Sepsis y HireVue;
  COMPAS, MCAS-aviación y moderación de contenido, estos tres construidos desde fuentes
  independientes citadas) reproducen los patrones. El alto recall del caso clínico no era un
  truco del caso: P3/A4 recuperan 0.93-1.00 de problemas documentados por terceros, precisión 0.93-1.0.
- **No hay falsa alarma (C1).** En un sistema bien diseñado, B1/P3/A4 devuelven **0
  hallazgos**: no inventan problemas. La verbosidad de P3 es **redundancia**, no
  fabricación → se arregla con un paso de deduplicado.
- **La adjudicación humana es imprescindible:** destapó dos sesgos de medición (juez bajo
  carga; desajuste golden↔dossier) que habrían falseado conclusiones.

## Validación de robustez (A2 · C3 · C2, k=3, nube, caso difícil EII v2)

Tres pruebas más para distinguir señal de artefacto y cerrar la pregunta del agente:

- **A2 — ¿la ventaja del pipeline son MIS bloques (overfitting) o descomponer?** Se re-corrió P3 con una
  partición **neutral** (la taxonomía de los autores: 4 fases HAX + 6 capítulos PAIR, derivada del dato,
  sin diseño a mano). **0.89 ≥ 0.82** del P3 a mano → **no es overfitting de bloques**: la ventaja es
  *descomponer*, y la partición neutral resulta además más estable (±0.03).
- **C3 — ¿es la entrada incompleta el nicho del agente?** A4 vs P3 con el dossier recortado (sin voz de
  usuario ni logs). Resultado **contraintuitivo**: A4 **0.62** vs P3 **0.78**; frente a entrada completa
  (A4 0.82, P3 0.78), **P3 no cae y A4 se desploma −0.20**. El nicho hipotetizado **no existe**: la
  entrada pobre es justo donde el barrido exhaustivo fijo más gana. A4, al decidir cuándo parar, corta
  antes (~30 hallazgos vs 53) y se deja issues recuperables.
- **C2 — ¿depende del fraseo exacto?** P3 sobre el dossier parafraseado (model-card telegráfica → prosa,
  mismos hechos): **0.78 ≈ 0.82** original, precisión 1.00. **Robusto al fraseo**: entiende, no pesca
  formato. (B1 sigue ruidoso, 0.47 ±0.33: su fragilidad es estructural, no del fraseo.)

**Qué cambia en la conclusión:** la celda *"modelo fuerte → el agente se justifica"* se **debilita**. El
agente solo iguala en el mejor caso (fácil/completo) y es más conciso, pero **no tiene un nicho robusto**:
pierde ante el pipeline en cuanto la entrada se degrada. La complejidad que paga de forma **robusta** es la
**descomposición fija del pipeline (P3)**, no la autonomía del agente.

## Deduplicado: el paso de producto (determinista, offline, k=3)

El anti-patron vivo de P3/p3n: emite el MISMO problema varias veces, casi siempre
citando una guideline DISTINTA cada vez (en un run, "onboarding sin reciclaje" aparecio
**7 veces** via HAX-G1, HAX-G12, PAIR-UN-2, PAIR-MM-1, PAIR-EF-2, PAIR-DE-1...). Un
auditor humano no quiere leerlo siete veces.

`src/interaction_review/dedup.py` colapsa hallazgos casi-duplicados en uno que **une las
guidelines de todos** (un hallazgo por problema, anotado con todas las que incumple). Es
DETERMINISTA, vive en codigo, sin LLM, y **no mira el golden** (en produccion no existe):
agrupa por similitud lexica del problema (Jaccard de titulo+locus, mas ratio de titulo con
guarda anti-plantilla). Coherente con ADR-004: lo mecanico al codigo.

Validado OFFLINE sobre runs ya juzgados (`scripts/dedup_report.py`), usando las
adjudicaciones -que el dedup nunca ve- como vara independiente: ¿pierde cobertura? ¿funde
problemas reales distintos (impureza)?

| Caso | approach | n antes->desp | reduccion | cobertura | impuros (k=3) |
|---|---|---|---|---|---|
| EII (dificil) | p3 | 56 -> 44 | 21% | 12.3 intacta | 0 |
| EII (dificil) | p3n | 102 -> 77 | 24% | 13.3 intacta | 5 |
| EII C2 (parafraseado) | p3 | 58 -> 42 | 26% | 11.7 intacta | 4 |
| EII C3 (incompleto) | p3 | 53 -> 39 | 25% | 11.7 intacta | 0 |
| Epic (held-out) | p3 | 42 -> 36 | 14% | 6.7 intacta | 0 |
| HireVue (held-out) | p3 | 41 -> 35 | 13% | 7.0 intacta | 2 |

**Lo que dicen los numeros (T=0.60, calibrado por el barrido de `--sweep`):**
- **Es SEGURO: cobertura perdida = 0 en los 6 escenarios** (recall intacto siempre; el dedup
  no tira hallazgos, funde). Precision intacta. Y **no dana lo ya conciso**: b1 y a4 apenas
  cambian (0-7%), no hay nada que colapsar.
- **Generaliza:** misma ganancia en los dos held-out, no afinado a EII.
- **El win determinista es MODESTO:** ~13-26% menos hallazgos en p3 con impureza ~0. Quita los
  duplicados textualmente evidentes; baja la consola pero no la vacia.
- **p3n es mas dificil de limpiar** (5 impuros, duplicacion 4.2x/golden) -> otro punto a favor de
  **p3 como producto** frente a p3n.
- **El residual es juicio irreducible:** "el mismo problema colado por una guideline distinta"
  con vocabulario muy diferente no se distingue a nivel lexico de dos problemas vecinos sin
  arriesgar conflacion (por eso T se queda en el lado seguro). Esa ultima capa pide un paso
  **semantico (LLM)** -> exactamente la tesis del proyecto: lo mecanico al codigo, al modelo solo
  lo irreducible.

### Capa semantica con LLM (frente 1b, `dedup_llm.py`) — el trade-off

Sobre el residual, una llamada al modelo agrupa por problema subyacente (el merge y la garantia de
no perder hallazgos siguen siendo deterministas, en codigo). Validado sobre runs p3 ya juzgados:

| Caso | n crudo -> lexico -> LLM | cobertura | impuros (clusters que mezclan golden, k=3) |
|---|---|---|---|
| EII (a2) | 56 -> 44 -> **17** | 12.3 intacta | 6 |
| Epic (held-out) | 42 -> 36 -> **15** | 6.7 intacta | 5 |
| HireVue (held-out) | 41 -> 35 -> **14** | 7.0 intacta | 9 |

**Trade-off honesto, no victoria limpia:** el LLM **colapsa de verdad** (~un hallazgo por problema, lo que
el determinista no logra) y **mantiene la cobertura** (recall intacto), pero **sobre-funde** (impureza 6/5/9,
hasta ~2/3 de clusters en HireVue mezclan problemas distintos).

**Se intentaron dos levers (2026-06-30):** (1) prompt estricto "por defecto NO agrupar, ante la duda separa"
→ apenas movio la impureza (a2 6→6, Epic 5→4). (2) **barandilla en codigo** (`SEMANTIC_LOCUS_FLOOR`: el LLM
propone grupos, el codigo VETA al miembro con locus dispar del representante) → **baja la impureza ~a la mitad
(a2 4, Epic 0, HireVue 5)** pero **se come la conciseness**: con barandilla el LLM queda en ~28-31, apenas
mejor que el determinista (~36-44).

**Conclusion (honesta) del frente 1b:** la capa semantica es un **trade-off fundamental**, no una mejora
limpia — agresiva conflaciona; con barandilla apenas supera al determinista. Por eso el **dedup determinista
es el default recomendado** (seguro, impureza ~0) y `--dedup-llm` (con barandilla 0.18 por defecto) es un
**modo agresivo opcional con repaso**. Lo que de verdad cerraria el residual sin conflar pediria la vara
buena: el **juez nuevo** re-juzgando estos runs (la impureza medida es cota superior, parte es ruido del
juez viejo que parte un mismo problema en dos golden).

## Enrutado por dificultad (frente b, `router.py`, `revisar --approach auto`)

El mapa dice: fácil→b1 (conciso), difícil→p3 (estructura). Como la dificultad no se sabe a priori, el
router corre b1 y **escala a p3+dedup** si el gap-check (reusado de A4) detecta áreas sin cubrir, o si b1
viene escaso (esto último cubre su inestabilidad: la corrida a 0). Comprobación de la decisión sobre b1 ya
generados (gap-check real):

| Caso | b1→p3 conocido | decisión del router | ¿acierta? |
|---|---|---|---|
| EII (difícil) | 0.44→0.78 | escala a p3+dedup | ✓ b1 insuficiente |
| COMPAS (medio) | 0.85→1.00 | escala | ✓ p3 mejora |
| Epic (fácil) | 0.95→0.95 | escala | ~ innecesario (p3 no mejora pero no pierde; +verbosidad) |
| HireVue (fácil) | 0.90→1.00 | se queda en b1 | ✗ deja 0.10 (p3 daría 1.00) |

**Honesto:** el gap-check es **eager** → escala 3/4 (en la práctica ≈ "p3+dedup salvo que b1 ya lo cubra
todo") y, cuando se queda en b1, puede dejar un issue sin ver (HireVue: el gap-check no detectó el hueco).
**La dificultad NO se infiere limpio desde una sola pasada de b1.** Conclusión: la **recomendación robusta
es p3+dedup por defecto** (nunca pierde mucho: 0.78-1.00 en todos los casos); `auto` lean-safe es útil
(además blinda la inestabilidad de b1) pero su rama b1 tiene riesgo de miss → es una optimización de
conciseness, no un discriminador fiable. Otro resultado honesto: la complejidad del router no se paga sola.

## Limitaciones honestas

- Golden sets pequeños y construidos por el evaluador (caso EII) o desde fuentes públicas
  (held-out); n de casos ya razonable (6 casos, 5 held-out, 3 dominios) pero aún no un benchmark.
- El "cero" de B1 en EII-Claude podría ser un hipo puntual de la API, pero ilustra la
  falta de red del prompt único.
- Los 3 held-out nuevos (COMPAS/MCAS/moderación) son de dificultad **media** y bien documentados,
  así que B1 ya rinde alto (0.81-0.96): confirman generalización pero no son casos "difíciles" como EII.
- Falta confirmar A4-vs-P3 con más casos **difíciles** y modelos intermedios.

## Próximos pasos

- **Producto — deduplicado:** ✅ HECHO en sus **dos capas** (determinista seguro + semántica LLM). El 1b
  resultó un **trade-off fundamental** (ver arriba): default determinista, `--dedup-llm` como modo agresivo.
- **Enrutado por dificultad (`auto`):** ✅ EXPLORADO (ver arriba). Resultado honesto: la dificultad no se
  infiere limpio a priori (el gap-check sobre-escala); **p3+dedup es el default robusto**. `auto` queda como
  opción lean-safe.
- **Lo que de verdad cerraría el residual del dedup:** re-juzgar estos runs con el **juez nuevo** para medir
  la impureza real (la actual es cota superior, contaminada por el juez viejo) — pero es pulido, no cambia la
  recomendación (determinista por defecto). El experimento y el producto mínimo están **cerrados**.
- **Deuda de medición — arreglada (2026-06-30).** El filtro de candidatos del juez solo ofrecía
  golden con guideline EXACTA compartida (muleta del juez 14B local, ADR-004): un hallazgo que citaba
  otra guideline no tenía como candidato al golden correcto → falso fallo. Ahora el juez nube (fuerte)
  ve **todos** los golden, con los que comparten guideline/grupo primero como pista (`judge._candidates`).
  Re-juzgado de control (p3, a2, k=3): **media recall estable 0.82→0.82, varianza a la mitad
  (±0.08→±0.03), precisión intacta (0.99)**. Lectura honesta: el arreglo mejora la **reproducibilidad**
  y quita la dependencia de qué guideline se citó, pero **NO sube la media** — el "P3 real ≈14/15" era
  una corrida con suerte (run0 baja 0.93→0.80 con el juez nuevo; runs 1-2 suben), no la verdad a k=3.
  Re-juzgado además el fichero principal **EII-Claude completo (b1/p3/a4): medias IDÉNTICAS al juez viejo
  (0.44 / 0.78 / 0.82)** → el arreglo no toca el titular. Recortado ahí: re-juzgar los otros 5 ficheros
  de la tabla no aportaría (medias estables, solo cambia varianza). **Conclusiones sin cambios.**
- **Control A4-completo fresco — ✅ HECHO (2026-06-30).** A4 sobre EII v2 completo, k=3 fresco: **0.80 ±0.09**
  (precisión 1.00), frente al 0.82 previo → el delta de C3 (A4 completo 0.80-0.82 vs A4 incompleto 0.62) queda
  **blindado**: la caída de A4 con entrada incompleta es real, no artefacto de una corrida.
