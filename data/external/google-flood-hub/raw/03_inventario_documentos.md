# Template 03: Documents you can provide

> Inventario de fuentes **públicas** usadas para reconstruir el caso (ver 00_LEEME_enfoque.md). Todas
> citables; ninguna con datos de personas.

---

## Useful documents (from most to least valuable for this review)

- [x] **Screenshots of what the user sees** (the proposal, the alerts, the override step).
  - Who holds it / format:
    ✍️ Público: el mapa de Flood Hub (sites.research.google/floods) y las páginas de ayuda que describen
    los niveles de severidad, el panel del gauge y las capas. Descrito en palabras en la ficha técnica.

- [x] **Technical spec / model card** (what the model does, performance, limits).
  - Who holds it / format:
    ✍️ Paper en *Nature* (Nearing et al. 2024) y blog de Google Research sobre el modelo global (7 días,
    ~700 M de personas). Describen el modelo LSTM, la generalización a cuencas sin aforo y la fiabilidad.

- [x] **Onboarding material or user manual** (how it is taught).
  - Who holds it / format:
    ✍️ Páginas de ayuda de Flood Hub (qué es, mapa y capas, FAQ, panel del gauge) con los avisos de "solo
    informativo" y "no usar como fuente única".

- [ ] **Design document / functional spec** (how the interaction was conceived).
  - Who holds it / format:
    ✍️ No público.

- [x] **Usage protocol** (how the system fits into the real workflow).
  - Who holds it / format:
    ✍️ Despliegues de acción anticipatoria que operacionalizan Flood Hub: GiveDirectly (triggers propios,
    p. ej. porcentaje del pueblo inundable) y su socio hidrológico JBA; casos con cruces rojas y agencias.

- [x] **Validation / performance report**, ideally with results by subgroup.
  - Who holds it / format:
    ✍️ Evaluación del propio paper (fiabilidad por horizonte) y evaluación independiente crítica (Li et
    al. 2026, *Journal of Hydrology X*) sobre el acierto en eventos extremos, metodológicamente discutida.

- [ ] **Summary of usage logs** (acceptance/change rates, alert counts), aggregated.
  - Who holds it / format:
    ✍️ No público de forma agregada.

- [x] **Other** (anything you think is relevant):
  ✍️ Reportaje de campo sobre conectividad, idioma y recepción del aviso en zonas vulnerables (Rest of
  World, isla Jamira). Evaluaciones de acción anticipatoria en Bangladesh 2020 (CSAE Oxford, Gros et
  al.), útiles como contexto pero **disparadas con GloFAS + FFWC, no con Flood Hub** (no atribuir).
