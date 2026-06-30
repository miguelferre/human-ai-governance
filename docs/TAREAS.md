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

- [ ] **Ablación dirigida del testimonio.** Etiquetar cada `GoldenIssue` por la fuente que lo revela
      (solo-usuario / solo-técnico / ambas) y medir el recall sobre el subconjunto *solo-usuario*, con voz
      vs sin voz. Demuestra (o refuta con honestidad) que el testimonio del usuario es el diferencial.
      Requiere un campo `revealed_by` en el esquema (merece su ADR). Nota: el C3 actual sugiere que en
      recall global la voz aportó ~0; el valor estaría en los issues *solo-usuario* y en el grounding.
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
