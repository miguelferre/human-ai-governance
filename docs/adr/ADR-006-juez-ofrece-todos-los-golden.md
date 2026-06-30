# ADR-006: El juez ofrece todos los golden (retirar la muleta del modelo débil)

- **Estado:** Aceptada
- **Fecha:** 2026-06-30

## Contexto

El LLM-juez pre-filtraba los candidatos del golden a los que compartían guideline **exacta**
con el hallazgo (ver ADR-004: reducir la tarea del juez 14B local de "escanea los 15" a
"confirma uno de estos 1-3"). Ese filtro causaba **falsos fallos**: un hallazgo que citaba la
guideline "equivocada" (otra fase, u otro corpus) no tenía el golden correcto entre sus
candidatos y no podía emparejarse (deuda de medición destapada por la adjudicación humana,
TESTPLAN B2). La "lista corta" era una muleta para el modelo local débil; tras el cambio a
nube (ADR-004 addendum) el juez es Sonnet, **fuerte**, y puede escanear los 15.

## Decisión

`judge._candidates` ofrece **todos** los golden como candidatos, con los que comparten
guideline/grupo (fase HAX / capítulo PAIR) **primero** como pista (marcados `[*]` en el prompt)
y el resto ordenado por similitud de texto. El juez fuerte decide sobre el conjunto completo.

La calibración descartó la alternativa de expandir candidatos **solo por similitud de texto**:
es señal débil (los matches reales tienen Jaccard mediana 0.127 entre hallazgo y golden).

## Consecuencias

- **Las medias NO cambian** (re-juzgado de control: EII-Claude b1 0.44 / p3 0.78 / a4 0.82
  idénticas al juez viejo; a2 p3 0.82→0.82), pero la **varianza cae ~½** (±0.08→±0.03), precisión
  intacta. Es un win de **reproducibilidad** y de metodología (el recall ya no depende de qué
  guideline se citó), no de recall.
- **Revisa el "P3 real ≈14/15"**: era una corrida con suerte (run0 0.93→0.80 con el juez nuevo),
  no la media a k=3. P3 es robustamente ~0.82 en EII difícil.
- La tabla histórica de RESULTADOS es del juez viejo; re-juzgarla entera solo estrecharía las
  barras (no se hizo: sin valor, conclusiones idénticas). El fichero principal sí se re-juzgó.
- Coste: el prompt del juez crece (15 candidatos por hallazgo en vez de 1-3); asumible en nube.
