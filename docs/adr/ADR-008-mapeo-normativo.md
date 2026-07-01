# ADR-008: Mapeo normativo (EU AI Act / NIST AI RMF)

- **Estado:** Aceptada
- **Fecha:** 2026-07-01

## Contexto

El revisor produce hallazgos atados a HAX-18 y PAIR. Son el estándar de facto del diseño
humano-IA, pero **el comprador no los conoce**: quien decide la compra en una institución es
gobernanza, calidad o cumplimiento, y ese perfil razona en términos de **marco regulatorio**
(EU AI Act, NIST AI RMF), no de guidelines académicas. Un informe que dice "incumple HAX-G2" no
entra en su expediente; uno que dice "esto toca el Art. 13 del AI Act y MEASURE 2.9 del NIST AI
RMF" sí. El go-to-market pedía convertir el informe de *crítica de diseño* en *evidencia de
conformidad* que el comprador reconozca.

## Decisión

Un **mapeo orientativo** de cada guideline HAX/PAIR a artículos del AI Act y subcategorías/
características del NIST AI RMF, en `guidelines/regulatory_map.yaml`, expuesto en el informe con
`revisar --crosswalk`. El módulo `regulatory.py` carga el mapa y agrega, para un conjunto de
hallazgos, qué requisitos tocan y por qué guideline (`crosswalk`).

**Nivel de granularidad:** artículo del AI Act (y sub-punto **solo** donde es inequívoco y
vendible — p. ej. Art. 14(4)(b), que nombra el *automation bias* de forma explícita, o Art. 86,
derecho a explicación de decisiones individuales). NIST a nivel de subcategoría (MAP 3.5,
MEASURE 2.9, …) y de característica de IA confiable (Explainable & Interpretable, etc.).

**No es dictamen legal.** El aviso va en el YAML, en la sección del informe y aquí: la
aplicabilidad real del AI Act depende de si el sistema es de alto riesgo (Anexo III), del rol
(proveedor vs responsable del despliegue) y del caso. El mapeo **sitúa**, no dictamina; antes de
usarlo como conformidad formal, revisión jurídica.

## Consecuencias

- El informe pasa de académico a **situado en el marco que el comprador maneja** sin cambiar el
  motor: es una capa de traducción sobre los `guideline_ids` que ya emiten los hallazgos.
- **Riesgo:** dar falsa sensación de conformidad legal. Se mitiga con el disclaimer explícito y
  con la granularidad honesta (no se inventan sub-apartados dudosos).
- **Integridad verificada por test** (`test_regulatory.py`): todas las guidelines reales están
  mapeadas (`unmapped_guidelines() == []`) y el mapa no cita ids fantasma (`unknown_map_ids() ==
  []`). Si se añade una guideline nueva, el test obliga a mapearla.
- **Mantenimiento:** si cambia el articulado (correcciones del Reglamento) o sale NIST AI RMF
  2.0, se actualiza solo el YAML; el código no depende de los números concretos.
- La opción es **opt-in** (`--crosswalk`): no ensucia el informe base de quien solo quiere la
  revisión de diseño.
