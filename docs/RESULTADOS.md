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
   - **Modelo fuerte → el agente (A4) se justifica**: iguala o supera al pipeline (0.82 vs
     0.78) y es **más conciso** (~30 vs ~55 hallazgos).

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

## Limitaciones honestas

- Golden sets pequeños y construidos por el evaluador (caso EII) o desde fuentes públicas
  (held-out); n de casos aún bajo.
- El "cero" de B1 en EII-Claude podría ser un hipo puntual de la API, pero ilustra la
  falta de red del prompt único.
- Falta confirmar A4-vs-P3 con más casos difíciles y modelos intermedios; y construir los
  3 held-out documentados restantes (moderación, aviación, COMPAS).

## Próximos pasos

- **Producto:** P3 + paso de **deduplicado**; y enrutado por dificultad (prompt único para
  casos simples, estructura para los complejos).
- **Pruebas pendientes:** A2 (bloques alternativos), C2 (robustez de entrada), C3 (nicho
  del agente con entrada incompleta).
