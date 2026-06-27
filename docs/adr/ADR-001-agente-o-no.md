# ADR-001: Empezar sin agente; construir una escalera de baselines

- **Estado:** Aceptada
- **Fecha:** 2026-06-27

## Contexto

Queremos un revisor de la capa de interaccion humano-IA. La tentacion por defecto
es construir "un agente". Pero la complejidad de un sistema de agentes (bucles,
tool use, decisiones autonomas) solo se justifica si **mejora de forma medible**
sobre alternativas mas simples. No tenemos evidencia de que haga falta.

## Decision

No construimos agente en la v1. Definimos una **escalera de complejidad** y solo
subimos un peldano cuando la evaluacion lo exija:

1. **B0** - checklist determinista (sin LLM). El suelo.
2. **B1** - prompt unico zero-shot.
3. **B2** - prompt unico few-shot.
4. **P3** - pipeline determinista (control de flujo fijo, NO agente).
5. **A4** - agente (decisiones autonomas, tool use, bucle).

"Agente" no es sinonimo de "mas complejo": B1 < B2 < P3 < A4. Cada salto debe
**ganar** al peldano anterior en la metrica primaria por un margen mayor que la
varianza entre ejecuciones (ver `metrics.beats` y ADR-002). Si no, se descarta y
se documenta por que.

## Consecuencias

- La v1 entrega B0 (y, en F2, B1/B2) y un arnes de evaluacion, no un agente.
- Evitamos sobre-ingenieria: el coste de complejidad se paga solo cuando hay datos.
- Riesgo: quiza ningun peldano supere a B1; ese seria un **resultado valido** del
  experimento (el agente sobra para esta tarea), no un fracaso.
