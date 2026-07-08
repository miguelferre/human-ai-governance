# Caso held-out: Google Flood Hub (enfoque y procedencia)

Caso público **no clínico** para validar el revisor fuera de sanidad. Sistema auditado: **Google
Flood Hub**, la IA de alerta temprana de inundaciones de Google/DeepMind (sites.research.google/floods).
Es el caso nº 18 de `data/external/`. A diferencia de los otros, incluye las **plantillas rellenas**
(`raw/`) versionadas, para que el flujo de dogfooding (plantillas → `ingest` → dossier → `review`) sea
reproducible y auditable de principio a fin.

## Qué se audita

La **capa de interacción**: cómo el sistema presenta sus predicciones y su incertidumbre a quien decide
(programas de acción anticipatoria, ONG, gobiernos) y a la población en riesgo. **No** se audita la
calidad hidrológica del modelo; se audita cómo comunica lo que sabe y lo que no sabe.

## Orden anti-contaminación (respetado)

1. Investigación de fuentes públicas.
2. **`answer_key.json` cerrado ANTES de correr el revisor** sobre este dossier (los GoldenIssue se
   derivan de las fuentes, no de la salida del revisor). El commit del answer_key precede a cualquier
   artefacto de corrida (ver historial git y `docs/RESULTS-floodhub.md`).
3. Plantillas rellenas (neutralizadas: hechos y experiencia, sin etiquetar el problema).
4. `ingest` → `dossier.json` (determinista; reproducible desde este `raw/`).
5. Solo entonces, `review` y `compare`.

## Neutralización

Las respuestas describen **qué hace el sistema y qué vive quien lo usa**, sin nombrar el problema de
diseño (eso es trabajo del answer_key). Se conservan hechos observables y experiencia; se evita el
diagnóstico ("esto causa sobre-confianza"). El bloque "What you already suspect" de las plantillas se
deja en blanco a propósito.

## Voces reconstruidas, no entrevistas reales

Como en el resto de casos externos, las voces de usuario están **sintetizadas a partir de material
público citado**, no son entrevistas propias. La voz del decisor institucional se ancla en el uso
**específico de Flood Hub** por programas de acción anticipatoria (GiveDirectly y partners, 2023-2025).
La voz de la población se ancla en reportaje de campo citado (Rest of World, isla Jamira, Bangladesh).

## Honestidad de atribución (importante)

La evidencia causal más fuerte de acción anticipatoria en Bangladesh 2020 (WFP/OCHA, Cruz Roja, CSAE
Oxford) se disparó con **GloFAS + la agencia gubernamental FFWC, NO con Google Flood Hub**. Aquí no se
le atribuye a Flood Hub esa evidencia: el decisor de este caso usa Flood Hub como en los despliegues
documentados de 2023-2025. Ver `casos-externos.md` y `docs/RESULTS-floodhub.md` para el detalle.

## Fuentes principales (procedencia [CITA])

- Nearing et al., *Nature* 627 (2024), "Global prediction of extreme floods in ungauged watersheds":
  https://www.nature.com/articles/s41586-024-07145-1 (abierto: https://pmc.ncbi.nlm.nih.gov/articles/PMC10954541/)
- Google Research blog (modelo global, 7 días, 700 M): https://research.google/blog/a-flood-forecasting-ai-model-trained-and-evaluated-globally/
- Flood Hub Help (qué es / mapa y capas / FAQ / panel del gauge): support.google.com/flood-hub/answer/
  15636593 · 15637289 · 15638004 · 15636998
- Blog Google (India-Bangladesh, idiomas; casos con organizaciones): blog.google/innovation-and-ai/products/flood-forecasts-india-bangladesh/ ·
  blog.google/company-news/outreach-and-initiatives/sustainability/4-flood-forecasting-collaboration-case-studies-show-how-ai-can-help-communities-in-need/
- GiveDirectly (triggers propios sobre Flood Hub): https://www.givedirectly.org/flood-forecast-ai ·
  JBA: https://jbagr.com/projects/designing-flood-triggers-for-anticipatory-action-in-bangladesh-and-nigeria/
- CSAE Oxford, Pople et al. (Bangladesh 2020, GloFAS+FFWC): https://ora.ox.ac.uk/objects/uuid:12ea16b2-edc0-4af5-8824-132aba4557bd
- Gros et al. 2023 (Cruz Roja, cuasi-experimental): https://preparecenter.org/wp-content/uploads/2023/12/Effects_of_anticipatory_cash_Gros_et_al.pdf
- Rest of World (campo, conectividad, idioma): https://restofworld.org/2025/google-flood-hub-cash-aid/
- Crítica independiente (Li, Razavi, Maier et al., *J. Hydrology X* 2026, evaluación en extremos,
  metodológicamente disputada): https://doi.org/10.1016/j.hydroa.2026.100215
- Periodo de retorno vs probabilidad (AMS, *Wea. Climate Soc.* 2018): https://journals.ametsoc.org/abstract/journals/wcas/10/1/wcas-d-16-0107_1.xml
