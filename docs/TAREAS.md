# Tareas pendientes

Trabajo planificado del proyecto. Estado a 2026-06-30. Lo de "rigor" **se saca de cara** (no es
respaldo defensivo): es lo que cierra el resultado de [RESULTADOS-testimonio.md](RESULTADOS-testimonio.md).

## Rigor de los resultados

- [ ] **2-3 casos duros más** (golden de fuente **humana externa** + dossier **en bruto** + manos
      separadas), como el de Robodebt (recall 0.90). Blinda el 0.90 con n>1. Candidatos: Asiana 214 con
      el informe NTSB como golden; un clínico con un estudio que ya liste los problemas de interacción.
- [ ] **Corrida-código reproducible.** Reponer la API key y correr `comparar` (juez LLM **independiente**)
      sobre los 7 casos con testimonio → el número "oficial", sin que el mismo motor haga de juez y de
      constructor. Es el cierre de la nota honesta de RESULTADOS-testimonio.

## Producto

- [~] **Ablación dirigida del testimonio.** Andamiaje + resultado offline HECHOS
      ([RESULTADOS-ablacion-testimonio.md](RESULTADOS-ablacion-testimonio.md), [ADR-007](adr/ADR-007-ablacion-del-testimonio.md)):
      campo `revealed_by` en el esquema, control sin-voz (`ablation.without_voice`), métrica por
      subconjunto (`metrics.recall_by_revealed_by`), los 7 goldens con testimonio etiquetados a mano y el
      reporte de distribución (`scripts/ablacion_report.py`). **Resultado:** 12/64 (19%) de los problemas
      solo los revela la voz —y son sistemáticamente los cognitivos (automation bias, modelo mental,
      timing, confianza)—; el 48% los revela también la documentación (ahí la voz da grounding, no recall).
      **Falta (API):** la corrida con voz vs sin voz para el *delta* de recall en `user_only` (el conteo es
      el techo, no el efecto). Comando listo en el doc.
- [ ] **Semi-automatizar el dossier.** Ingerir la documentación de un sistema → plantillas rellenas, para
      que construir la entrada no cueste lo mismo que auditar a mano (hoy es el cuello de botella del caso
      de uso real).
- [ ] **Informe presentable** (HTML) en vez de markdown plano.

## Narrativa / comercial

- [ ] **Mapeo a marco normativo** (EU AI Act / NIST AI RMF). Convierte "informe académico HAX/PAIR" en
      "evidencia de conformidad" que el comprador (gobernanza/calidad) reconoce y puede meter en su
      expediente. Es extensión de *narrativa*, no del motor.
- [x] README que vende el producto (hecho 2026-06-30).

## Seguridad

- [ ] **Rotar la API key de Anthropic.** Quedó expuesta en el chat y el `.env` actual da 401: generar una
      nueva en console.anthropic.com y revocar la vieja.
