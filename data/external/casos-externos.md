# Casos held-out externos (fuentes públicas) — para la prueba de generalización (A1)

Recopilado por agente de investigación (2026-06-29). Material PÚBLICO citado (no privado).
Uso: convertir cada uno en `dossier` (hechos, neutralizado) + `answer_key` (golden = problemas
documentados, mapeados a HAX/PAIR). Diversidad de dominio: 4 NO clínicos (los más valiosos
contra overfitting). Cada problema: [CITA] = explícito en fuente, [INF] = inferencia/mapeo.

---

## CASO E1 — Epic Sepsis Model (ESM) · sanidad/alerta de sepsis · CLÍNICO
**Dossier (hechos):** modelo propietario integrado en el HCE de Epic, desplegado en cientos de
hospitales. Calcula en continuo una puntuación de riesgo de sepsis; al superar un umbral fijado
por el hospital (en Michigan, ≥6), genera avisos/pages al clínico (estación, habitación o móvil).
El clínico ve la alerta y decide evaluar/pedir pruebas/antibióticos o descartarla. Validación
Michigan: score 6+ en 18% de hospitalizaciones; VPP 12% (1 de 8); no detectó 67% de sepsis pese a
alertar. UI con acciones sugeridas limitadas, sin datos de tendencia, sin explicar por qué se
disparó. Abr 2020: pausa de alertas tras reportes de enfermería; +43% alertas/día con censo -35%.
**Problemas:** 1) fatiga de alerta (18%) [CITA · alertas-tiempo]; 2) VPP 12% percibido [CITA · alertas/incertidumbre]; 3) pico COVID y pausa [CITA · alertas/fallo]; 4) no explica por qué se dispara [CITA · explicación]; 5) UI sobrecargada, sin tendencia, no se puede reabrir la alerta cerrada [CITA · presentación]; 6) acciones limitadas, lo puentean al chocar con su juicio [CITA · override]; 7) confianza distinta por experiencia [CITA · confianza/onboarding]; 8) verificación redundante por desconfianza [CITA · supervisión]; 9) canal/lugar de alerta disruptivo (móvil) [CITA · alertas-tiempo/presentación]; 10) prefieren rol de aumento, no automatización [CITA · supervisión/override].
**Fuentes:** Wong 2021 JAMA Intern Med (10.1001/jamainternmed.2021.2626); Habib 2021 (editorial); Lin/Wong/Singh 2021 JAMA Netw Open (PMC8605481); Owoyemi 2024 JAMIA Open (10.1093/jamiaopen/ooae096) — enumera problemas.

## CASO E2 — Moderación de contenido Meta/Facebook · trust&safety · NO CLÍNICO
**Dossier:** embudo híbrido IA+humano. La IA o reportes triagean; los casos van a un moderador
(subcontratado). El moderador procesa una COLA de tickets (algunos pre-marcados por IA), ve el
contenido y botones (ignore/delete/disturbing); si borra, elige un MOTIVO de un desplegable que se
evalúa. Ritmo 30-60 s/ticket. QA audita ~50-60 de ~1.500 decisiones/semana → "accuracy score"
(contrato exige 98%); la puntuación condiciona primas/turnos/empleo. Hay disputa/apelación de QA.
Controles de visualización opcionales (difuminar, B/N, bloquear caras, silenciar).
**Problemas:** 1) cola pre-marcada por IA enmarca todo como infracción [CITA arquitectura/INF sesgo · supervisión]; 2) UI pobre, segundos para decidir [CITA hechos/INF contexto · presentación/tiempo]; 3) "accuracy" mide acuerdo, no corrección [CITA · override/fallo]; 4) penaliza el motivo del desplegable aunque la decisión sea correcta [CITA · presentación/override]; 5) apelación adversarial poco fiable [CITA · override/fallo]; 6) presión de cuota vs calidad [CITA · alertas-tiempo]; 7) discrepar del QA automático tiene coste económico [CITA · override/controles]; 8) scoring opaco sin recurso real [CITA · supervisión/explicación]; 9) medición tareas/hora endurecida [CITA · alertas-tiempo]; 10) onboarding mínimo (~8 días cursory) [CITA · onboarding]; 11) (mitigación) controles de visualización [CITA · controles].
**Fuentes:** Barrett 2020 NYU Stern; Newton 2019 The Verge; Perrigo 2022 TIME; AlgorithmWatch 2026; Santa Clara Principles v2.0.

## CASO E3 — Aviación: MCAS 737 MAX y autopiloto A330 (AF447) · NO CLÍNICO
**Dossier:** MCAS empuja el morro abajo automáticamente; en Lion Air 610 / Ethiopian 302 se activó
con datos de UN solo sensor AoA y ordenó picados repetidos. Pilotos "largely unaware that MCAS
existed" (Boeing lo retiró de manuales); la alerta "AoA Disagree" estaba inoperativa en la mayoría
de la flota (ligada a opción de pago). En cabina, múltiples alertas simultáneas; override (corte de
trim) no evidente. AF447: hielo en sondas Pitot → desconexión del autopiloto, "alternate law";
tripulación "completely surprised"; stall warning intermitente y contradictorio.
**Problemas:** 1) modelo mental ausente (no sabían que MCAS existía) [CITA · onboarding]; 2) alerta de discrepancia inoperativa y de pago [CITA · presentación/fallo]; 3) sensor único dispara la automatización [CITA · fallo]; 4) override no evidente, la automatización "lucha" [CITA hecho/INF · override]; 5) desconexión súbita + efecto sorpresa [CITA · fallo/supervisión]; 6) stall warning intermitente/contradictorio [CITA · presentación/alertas]; 7) cambio de "law"/modo no comprendido [CITA · presentación/explicación].
**Fuentes:** US House T&I Final Report 2020 (Boeing 737 MAX); BEA Final Report AF447 2012; Parasuraman & Riley 1997 (terminología). Caveat: citas de comunicado/cobertura, paginación exacta pendiente.

## CASO E4 — HireVue · contratación / cribado por vídeo · NO CLÍNICO
**Dossier:** evaluación de preempleo por IA para empleadores. El candidato graba entrevista
unidireccional por webcam; el sistema analiza palabras, voz y (hasta 2021) cara, y produce una
"employability score" que ordena candidatos. El candidato NO ve su puntuación, no sabe qué
conductas importaron, no puede preguntar/corregir/apelar; la guía dice "como una entrevista
normal". El reclutador recibe candidatos ordenados con su puntuación y filtra por ranking. La
composición de la puntuación es opaca incluso para el empleador (y a veces para HireVue).
**Problemas:** 1) no se da al candidato su puntuación [CITA · presentación]; 2) sin acceso a factores/lógica; opaco hasta para el vendor [CITA · explicación]; 3) no transparente ni comprensible [CITA · explicación]; 4) sin vía de impugnar/optar fuera [CITA · override]; 5) el empleador decide apoyándose en la puntuación [CITA · supervisión]; 6) diseño que invita a filtrar por ranking (sesgo de automatización) [CITA · supervisión/presentación]; 7) el candidato no ve cómo mejorar [CITA · explicación/override]; 8) negativa a auditoría independiente [CITA · controles/explicación]; 9) onboarding miscalibrado ("como una entrevista normal") [CITA texto/INF · onboarding].
**Fuentes:** EPIC FTC Complaint 2019 (párrafos numerados §27,§30,§61-63,§76,§80,§32) — PRIMARIA; Harwell 2019 Washington Post; Chen 2019 MIT Tech Review; Maurer 2021 SHRM.

## CASO E5 — COMPAS · justicia penal / apoyo a decisión judicial · NO CLÍNICO (secundario)
**Dossier:** toma ~137 variables y emite puntuación de riesgo de reincidencia: categoría bajo/medio/
alto + escala numérica. Jueces/oficiales la ven en fianza, sentencia, condicional. El juez ve una
etiqueta + número sin cálculo divulgado (fórmula propietaria); el acusado rara vez ve la base o la
impugna. Jueces citan la puntuación como motivo. State v. Loomis (2016) exigió "warning labels" y
prohibió que fuera el factor determinante.
**Problemas:** 1) categoría escueta sin razonamiento [CITA · presentación]; 2) cálculo no divulgado, opaco [CITA · explicación]; 3) el acusado rara vez puede impugnar [CITA · override]; 4) deferencia del juez a la puntuación [CITA · supervisión]; 5) brecha de debido proceso por opacidad [CITA · explicación/override]; 6) los "warning labels" pueden ser inviables en la práctica [CITA · supervisión/controles]; 7) sin ventaja de exactitud sobre un lego pese a presentarse con autoridad [CITA hallazgo/INF marco · incertidumbre-confianza].
**Fuentes:** Angwin/Larson/Mattu/Kirchner 2016 ProPublica "Machine Bias"; Kirchner 2016 ProPublica (Loomis); Dressel & Farid 2018 Sci Adv (10.1126/sciadv.aao5580); State v. Loomis 2016 WI 68.

---

**Prioridad para A1 (anti-overfitting):** los NO clínicos (E4 HireVue y E2/E5) son los más valiosos
porque el diseño de P3/prompts se hizo en dominio clínico. Plan: construir 1 clínico distinto (E1)
+ 1-2 no clínicos (E4, y E2 o E5) como dossier+golden y correr B1/P3/A4. Si el orden P3>A4>B1
aguanta fuera de lo clínico, la ventaja del pipeline generaliza.
