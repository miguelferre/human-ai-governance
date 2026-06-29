# Caso externo held-out: IBM Watson for Oncology (investigación, fuentes públicas)

Material recopilado por agente de investigación (2026-06-29) para construir un caso de
prueba **held-out** (generalización / anti-overfitting). NO es material privado: son
fuentes públicas citadas. Pendiente: convertir en `dossier` (hechos, neutralizado) +
`answer_key` (golden = problemas documentados, mapeados a HAX/PAIR).

## Sistema y dominio
IBM Watson for Oncology (WFO) + variante Oncology Expert Advisor (MD Anderson). CDSS para
recomendación de tratamiento oncológico. El oncólogo introduce atributos del paciente
(diagnóstico, estadio, biomarcadores) en una interfaz estructurada (~10 min la 1ª vez,
~1,5 min tras ~20 casos; percibido "cumbersome"). Watson devuelve una lista de opciones
de tratamiento en **tres tiers de color**: verde = recomendado, naranja = a considerar,
rojo = no recomendado, cada una con enlaces a literatura de apoyo. Las recomendaciones
codifican las preferencias de los médicos del MSKCC (entrenado en parte con casos
sintéticos). Es advisory: el oncólogo lee, inspecciona evidencia y decide; no actúa solo.
La variante de MD Anderson no integraba con el EHR Epic.

## Problemas de interacción documentados (fuente → categoría)
1. No explica POR QUÉ recomienda para ESE paciente (muestra literatura, no su razonamiento). [explicación] — STAT 2017 (cita textual).
2. Caja negra; razonamiento opaco, no evaluable externamente. [explicación] — Keikes et al. 2018 (cita).
3. El usuario no sabe qué factores pesa o ignora (p. ej. la edad) → mina el override seguro. [explicación/supervisión] — Keikes et al. 2018 (cita).
4. Las recomendaciones llevan el sesgo de una institución, presentado como autoritativo. [confianza-sesgo/presentación] — STAT 2017 (cita Seidman).
5. No refleja guías locales, disponibilidad de fármacos ni cobertura → recomendaciones inadoptables. [presentación/confianza] — Choi et al. 2019 (cita).
6. Confianza/incertidumbre mal transmitida: los colores cuesta distinguirlos y "verde" puede aparecer sin evidencia. [incertidumbre/presentación] — STAT 2017 (cita Kollmeier).
7. No considera el historial médico complejo, pero presenta la recomendación como si lo hiciera. [presentación/fallo] — Choi et al. 2019 (cita).
8. Fallos de contexto local → confusión y corrección manual de la salida. [override/presentación] — STAT 2017 (citas Jensen, Chiou).
9. Desconfianza / no aporta: sugiere solo tratamientos estándar que ya conocen. [confianza-sesgo] — IEEE Spectrum 2019; STAT 2017 (citas).
10. Feedback interno demoledor sobre utilidad real ("a piece of s—", "unsafe and incorrect"). [confianza/fallo] — STAT 2018 (citas).
11. Sesgo de automatización / sobre-confianza, sobre todo en usuarios noveles (Mongolia ~100% seguimiento). [automatización/supervisión] — STAT 2017; Yun 2021 (cita + inferencia de etiqueta).
12. El onboarding/actualización del sistema no sigue el ritmo → guía obsoleta sin saberlo. [onboarding/fallo] — STAT 2017 (cita Kris).
13. Fallo de integración/workflow (no sincroniza con Epic → datos desactualizados). [controles/supervisión] — auditoría UT (fuente secundaria, verificar primaria).
14. Entrada manual cumbersome, no interoperable → fricción de flujo. [controles/presentación] — Keikes et al. 2018 (cita).
15. Ambigüedad de responsabilidad en el lazo humano-IA al seguir/anular una recomendación opaca. [supervisión/override] — Luxton 2019 (de abstract, no verbatim).
16. Campos de entrada ausentes degradan la recomendación en silencio. [fallo/presentación] — Yun 2021 (cita).

## Fuentes (principales)
- Ross & Swetlitz, STAT 2017 (statnews.com/2017/09/05/watson-ibm-cancer/) — fuente más rica.
- Ross & Swetlitz, STAT 2018 (unsafe/incorrect treatments).
- Strickland, IEEE Spectrum 2019.
- Keikes et al. 2018, J Clin Transl Research (PMC6412599) — mejor fuente académica de caja-negra/usabilidad.
- Choi et al. 2019 (PMC6377977); JCO CCI 2019 (PMID 30652564); Yun et al. 2021 (PMC7968416).
- Schmidt, JNCI 2017 (DOI 10.1093/jnci/djx113); Luxton, AMA J Ethics 2019 (PMID 30794122).

**Calidad:** la mayoría de #1-#10,#12,#14,#16 son cita textual de fuente fetchada; #11/#13/#15 mezclan hecho citado + etiqueta inferida o fuente secundaria (verificar primaria antes de citar como definitivo).
