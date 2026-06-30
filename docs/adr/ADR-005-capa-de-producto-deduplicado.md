# ADR-005: Capa de producto — deduplicado determinista por defecto

- **Estado:** Aceptada
- **Fecha:** 2026-06-30

## Contexto

P3 (y p3n) arrastran un anti-patrón vivo: emiten el MISMO problema varias veces, casi
siempre citando una guideline distinta cada vez (en un run, "onboarding sin reciclaje"
apareció 7 veces vía HAX-G1, HAX-G12, PAIR-UN-2, PAIR-MM-1, PAIR-EF-2, PAIR-DE-1...).
~50-100 hallazgos para ~15 problemas reales. Un auditor humano no quiere leer el mismo
problema cinco veces. El control de falsos positivos (C1) ya mostró que la verbosidad es
**redundancia, no fabricación** → se arregla consolidando, no recortando señal.

## Decisión

Un paso de deduplicado **de dos capas, con la determinista por defecto**:

1. **Determinista** (`dedup.py`, `revisar --dedup`) — **el default**. Agrupa por similitud
   léxica (Jaccard de título+locus + ratio de título con guarda anti-plantilla) y **une las
   guidelines del cluster** (un hallazgo por problema, anotado con todas las que incumple).
   Sin LLM, no ve el golden (en producción no existe). Validado offline: **cobertura perdida
   0 en 6 escenarios**, impureza ~0, reducción 13-26% en p3, generaliza a held-out, no daña
   lo ya conciso (b1/a4).
2. **Semántica con LLM** (`dedup_llm.py`, `revisar --dedup-llm`) — **opcional, NO por defecto**.
   Para el residual "mismo problema, guideline distinta" que el léxico no junta (calibración:
   matches reales con Jaccard mediana 0.127 → el texto no basta). El LLM **propone** grupos; el
   código **garantiza** no perder ni duplicar hallazgos y aplica una **barandilla** (`locus_floor`)
   que veta fusiones de locus dispar (el LLM propone, el código comprueba).

**Por qué el LLM no es el default:** es un trade-off fundamental, no una mejora limpia. Sin
barandilla colapsa fuerte (~17 hallazgos) pero sobre-funde (impureza 6/5/9); con barandilla la
impureza baja ~½ (Epic a 0) pero la conciseness cae a ~28-31, apenas mejor que el determinista.

**Enrutado por dificultad** (`router.py`, `revisar --approach auto`) — **explorado, NO adoptado
como recomendación**. Corre b1 y escala a p3+dedup si el gap-check detecta huecos o b1 viene
escaso. El gap-check **sobre-escala** (3/4) y no discrimina dificultad a priori (se quedó en b1
en HireVue dejando 0.10 sin detectar). Queda como opción *lean-safe* (sí blinda la inestabilidad
de b1, la corrida a 0), pero **p3+dedup es el default robusto**.

## Consecuencias

- **El producto mínimo = P3 + dedup determinista.** Conciso, seguro y sin coste de LLM.
- `--dedup-llm` y `--approach auto` quedan como opciones documentadas con sus trade-offs medidos.
- Lección (coherente con ADR-001): la complejidad extra (LLM-dedup, router) **no se paga sola**;
  lo robusto es el pipeline fijo + dedup determinista. La misma tesis del proyecto, otra vez.
- Pulido pendiente (no cambia la recomendación): re-juzgar con el juez nuevo (ADR-006) para medir
  la impureza REAL del LLM-dedup; la medida actual es cota superior (contaminada por el juez viejo).
