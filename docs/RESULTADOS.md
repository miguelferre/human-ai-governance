# Resultados del experimento — ¿hace falta un agente para revisar la capa de interacción?

Síntesis a 2026-06-29. Detalle de cada corrida en `runs/` (gitignored); plan en
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

B0 = 0.00 en todos (suelo). Todos los approaches con LLM: precisión ~1.0, genericidad 0.

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
- **No era overfitting.** Los held-out (uno NO clínico, otro clínico distinto) reproducen
  los patrones. El alto recall del caso clínico no era un truco del caso.
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
  arriesgar conflacion (por eso T se queda en el lado seguro). Esa ultima capa pediria un paso
  **semantico (LLM)** -> exactamente la tesis del proyecto: lo mecanico al codigo, al modelo solo
  lo irreducible. Queda como siguiente paso de producto (opcional, gasta API).

## Limitaciones honestas

- Golden sets pequeños y construidos por el evaluador (caso EII) o desde fuentes públicas
  (held-out); n de casos aún bajo.
- El "cero" de B1 en EII-Claude podría ser un hipo puntual de la API, pero ilustra la
  falta de red del prompt único.
- Falta confirmar A4-vs-P3 con más casos difíciles y modelos intermedios; y construir los
  3 held-out documentados restantes (moderación, aviación, COMPAS).

## Próximos pasos

- **Producto — deduplicado:** ✅ HECHO (paso determinista, ver seccion arriba). Quita las repeticiones
  evidentes sin perder cobertura (0 en 6 escenarios) y confirma **p3 > p3n** como candidato (p3n es mas
  sucio de limpiar). Pendiente: (a) capa **semántica (LLM)** opcional para el residual "mismo problema vía
  guideline distinta" —gasta API—; (b) **enrutado por dificultad** (prompt único para casos fáciles,
  pipeline+dedup para los difíciles).
- **Deuda de medición:** el filtro por id de guideline del juez produce falsos fallos (P3 real ≈ 14/15);
  ampliar candidatos por grupo/similitud subiría el recall medido de todos los approaches por igual.
  (Necesita re-juzgar = gasta API.)
- **Opcional (rigor):** control A4-completo fresco para blindar el delta de C3; y construir los 3 held-out
  documentados restantes (moderación, aviación, COMPAS). (Generación nueva = gasta API.)
