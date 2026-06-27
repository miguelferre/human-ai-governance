# ADR-002: Diseno de evaluacion y metrica primaria (pre-registrada)

- **Estado:** Aceptada
- **Fecha:** 2026-06-27

## Contexto

"Funcionar" tiene que ser medible, no una intuicion. Tenemos un caso clinico real
con problemas de interaccion ya identificados por el usuario: es un **golden set**
con respuestas conocidas. La pregunta es si el sistema los redescubre solo, sin
verlos, y sin escupir genericos.

## Decision

### Golden set y ejecucion ciega
- El answer key (lista congelada de `GoldenIssue`) vive bajo `data/golden/`
  (gitignored). El sistema **no** lo ve. Recibe solo el `Dossier`.

### Adjudicacion
- Un **LLM-juez** (modelo/prompt distintos del generador) etiqueta cada hallazgo:
  `TP_MATCH` / `TP_NEW` / `FP_GENERIC` / `FP_INCORRECT`.
- El **humano revisa y corrige** (`human_confirmed`). El gold final es humano.

### Metricas (implementadas en `metrics.py`)
- recall, precision, genericity_rate, grounding_rate, tp_new.
- Cada approach se corre **k >= 3** veces; se reporta media +/- desviacion tipica.

### Metrica primaria — PRE-REGISTRADA (antes de ver resultados)
- `primary_score` = **F-beta con beta = 2.0** (prioriza recall: en auditoria no
  detectar un problema real es peor que un FP barato de descartar), **sujeta a**
  `genericity_rate <= 0.25`. Si no pasa ese techo, `primary_score = 0`.
- Estos valores estan fijados en codigo (`metrics.BETA`, `metrics.GENERICITY_THRESHOLD`)
  para no racionalizarlos a posteriori. Cambiarlos exige un nuevo ADR.

### Regla de decision entre peldanos
- `metrics.beats(candidato, baseline)`: el candidato gana si la media de su
  primary_score supera a la del baseline por mas que la suma de sus desviaciones
  tipicas (margen > ruido).

## Consecuencias y limites asumidos

- **n = 1 caso golden** -> evaluacion **formativa**, no benchmark. El segundo caso
  (clima) es **test parcial held-out**: no se usa para afinar prompts.
- **Overfitting**: todo ajuste se hace mirando solo el caso clinico; riesgo asumido.
- Un hallazgo generico cuenta como **fallo**, por diseno de la metrica.
