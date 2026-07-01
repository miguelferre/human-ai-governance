# ADR-007: Ablación del testimonio del usuario (campo `revealed_by`)

- **Estado:** Aceptada
- **Fecha:** 2026-07-01

## Contexto

El diferenciador comercial del revisor (ver PRODUCTO y el go-to-market) es incorporar el
**testimonio del usuario final**, no solo auditar el diseño en abstracto. Pero es una promesa
**aún sin demostrar**: el control C3 (RESULTADOS.md) mostró que, en recall **global**, el
dossier con voz y sin voz rinden casi igual (P3 0.78 = 0.78). Eso no refuta la promesa —el
valor del testimonio podría estar en un subconjunto pequeño de problemas que *solo* la voz
revela, o en el grounding/credibilidad de los hallazgos— pero sí obliga a medirlo de forma
dirigida en vez de afirmarlo.

El problema de medición: el recall global mezcla issues que cualquier fuente revela con los
que dependen del testimonio. Para aislar el aporte de la voz hace falta saber, **por cada
GoldenIssue, desde qué tipo de fuente es detectable**.

## Decisión

1. **Campo `revealed_by` en `GoldenIssue`** (enum `RevealedBy`), etiquetado a mano sobre el
   contenido real de las fuentes del dossier:
   - `USER_ONLY` — solo identificable a partir del testimonio de un usuario final (`END_USER`).
     Sin esa voz, el problema es invisible en el dossier.
   - `TECH_ONLY` — solo desde documentación o perfil técnico (`DOCUMENT` / `TECHNICIAN`).
   - `BOTH` — la documentación lo describe **y** el usuario lo vive/confirma.
   - `UNKNOWN` — sin etiquetar (default): no participa en la ablación. Mantiene compatibles
     los golden previos (EII, held-out sin voz) sin tocarlos.

   **Criterio de etiquetado:** para cada issue, ¿en qué fuentes hay evidencia que lo sustente?
   Solo en `END_USER` → `USER_ONLY`; solo en `DOCUMENT`/`TECHNICIAN` → `TECH_ONLY`; en ambas
   → `BOTH`. Se decide leyendo las fuentes, no por la guideline citada.

2. **Condición de control "sin voz"** (`ablation.without_voice`): el mismo dossier retirando
   las fuentes `END_USER`. Determinista, offline, no muta el original.

3. **Métrica** (`metrics.recall_by_revealed_by`): recall desglosado por subconjunto
   `revealed_by`. La comparación que importa es el recall de `USER_ONLY` **con voz vs sin voz**.

## Cómo se lee el resultado (pre-registrado, antes de la corrida)

- **La promesa se sostiene** si el recall de `USER_ONLY` es alto con voz y **se desploma** sin
  voz (el revisor deja de ver esos problemas cuando le quitas el testimonio).
- **La promesa se debilita a "grounding, no descubrimiento"** si el recall de `USER_ONLY` no
  cae de forma apreciable sin voz (el revisor los infiere igual desde la documentación; el
  testimonio añade evidencia y credibilidad, no hallazgos nuevos). Sería coherente con C3.
- **Techo previo, gratis:** `ablation.revealed_by_distribution` cuenta los `USER_ONLY` del
  golden **sin gastar API**. Si son muy pocos, el aporte máximo posible al recall ya es bajo
  antes de correr nada — un resultado honesto por sí mismo.

## Consecuencias

- Etiquetar es **juicio humano** y va en el answer key (fuera del dossier ciego; el revisor no
  lo ve). Un etiquetado sesgado hacia `USER_ONLY` inflaría el aporte del testimonio → se
  documenta la evidencia por issue y queda revisable.
- El campo es aditivo y con default `UNKNOWN`: no cambia ninguna métrica existente ni rompe
  golden previos. La ablación es un análisis aparte, no un cambio del experimento principal.
- La corrida final (recall con voz vs sin voz) necesita el LLM (flujo `comparar` sobre el
  dossier completo y sobre `without_voice`); el andamiaje —campo, control, métrica, conteo
  offline— no.
