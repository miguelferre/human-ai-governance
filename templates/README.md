# Plantillas para describir tu sistema de IA

Gracias por ayudarnos a revisar tu sistema. Estas plantillas sirven para
contarnos **cómo es tu sistema de IA y, sobre todo, cómo lo vive la persona que
lo usa**. Con lo que nos cuentes construimos una revisión estructurada de la
*capa de interacción* y te devolvemos hallazgos concretos y recomendaciones.

No necesitas conocimientos técnicos para la mayoría de las preguntas. Escribe con
tus palabras: es mejor una respuesta sincera y concreta que una respuesta
"perfecta".

---

## ¿Qué estamos revisando exactamente?

No revisamos si el modelo "acierta" (eso ya lo miden otras herramientas).
Revisamos la **capa de interacción**: todo lo que ocurre entre el resultado del
modelo y la decisión de la persona. Por ejemplo:

- ¿Queda claro qué hace el sistema y qué **no** hace?
- ¿La persona entiende **por qué** propone lo que propone?
- ¿Se muestra cuándo el sistema está **poco seguro**?
- Cuando la persona **no está de acuerdo**, ¿puede cambiarlo? ¿queda registro? ¿sirve de algo?
- ¿Interrumpe en mal momento? ¿hay demasiadas alertas?

> Ejemplo sencillo: un sistema sugiere la prioridad de un ticket de soporte. Si
> el agente casi siempre acepta la sugerencia sin mirarla y, cuando la cambia,
> ese cambio no se guarda en ningún sitio, eso es un problema de la capa de
> interacción, aunque el modelo sea muy preciso.

---

## ¿Qué necesitamos de ti?

Tres plantillas (rellena las que te correspondan según tu rol) y, si los tienes,
algunos documentos:

| Plantilla | Qué recoge | Quién la rellena mejor |
|---|---|---|
| [`01_ficha_sistema__perfil_tecnico.md`](01_ficha_sistema__perfil_tecnico.md) | Qué hace el sistema, cómo presenta el resultado, override, alertas, supervisión | Responsable técnico, data scientist, responsable de producto/implantación |
| [`02_experiencia_uso__usuario_final.md`](02_experiencia_uso__usuario_final.md) | Cómo se vive el sistema en el día a día | Usuario final (quien usa la herramienta para decidir) |
| [`03_inventario_documentos.md`](03_inventario_documentos.md) | Qué documentos existen y nos puedes aportar | Cualquiera con acceso a la documentación |

No hace falta que una sola persona lo rellene todo. De hecho, **es mejor que no**:
nos interesa contrastar la visión técnica con la del usuario final.

---

## ¿De quién necesitamos cada cosa, y por qué?

- **Del perfil técnico / producto** → cómo está construido y diseñado el sistema
  por dentro (la "intención"). Plantilla 01 + documentos técnicos.
- **Del usuario final** → cómo se experimenta de verdad (la "realidad de uso").
  Plantilla 02.
- **El contraste entre ambas** es una de las cosas más valiosas que buscamos.
  Cuando el técnico cree que "el cambio del usuario se guarda y sirve para
  mejorar" pero el usuario dice "no sé si cambiarlo sirve de algo", ahí hay una
  señal importante. Por eso pedimos las dos voces por separado.

---

## ¿Para qué usaremos lo que nos des?

- Para construir un **dossier** del sistema (su descripción normalizada) y pasarlo
  por la revisión.
- Para producir **hallazgos anclados**: cada observación irá atada a una guideline
  reconocida (HAX-18 de Microsoft, PAIR de Google) y a un punto concreto de tu
  sistema, con la evidencia de lo que nos contaste.
- **No** se comparte con terceros ni se usa para nada más.

---

## Privacidad (importante)

- **No incluyas datos de personas** (pacientes, clientes, usuarios reales): ni
  nombres, ni identificadores, ni casos concretos identificables. Para revisar la
  interacción **no hacen falta**. Describe el sistema, no a sus usuarios.
- Si un documento contiene datos sensibles, **anonimízalo o quítalos** antes de
  enviarlo. Si tienes dudas, mejor no lo envíes y descríbelo con palabras.
- Si tu sistema es clínico, lo anterior aplica con más razón.

---

## Un matiz que nos ayuda mucho

Cuéntanos **cómo es** el sistema, no **qué crees que está mal**. La gracia de la
revisión es que detecte los problemas por sí sola a partir de una descripción
fiel. Si nos adelantas tu diagnóstico ("creo que el override está mal capturado"),
no pasa nada, pero apúntalo **al final, en la sección "Lo que tú ya sospechas"** de
cada plantilla, separado del resto. Así no se mezcla con la descripción.

---

## Cómo entregarlo

Tienes dos opciones, la que te resulte más cómoda:

1. **Rellenar los `.md`** (estas plantillas) escribiendo bajo cada pregunta, y
   enviárnoslos.
2. **Rellenar [`dossier_plantilla.json`](dossier_plantilla.json)** si prefieres un
   formato estructurado (o si vas a integrarlo con la herramienta directamente).

Adjunta también los documentos que hayas marcado en la plantilla 03.

---

<details>
<summary><strong>Mapa interno de trazabilidad (uso del equipo evaluador)</strong></summary>

Las plantillas evitan a propósito la jerga de guidelines. Esta es la correspondencia
interna entre cada bloque y las guidelines que cubre, para construir hallazgos
anclados:

| Bloque de la plantilla | Guidelines principales |
|---|---|
| Qué hace / qué no hace | HAX-G1, PAIR-MM-1, PAIR-UN-1 |
| Rendimiento y límites | HAX-G2, PAIR-MM-2 |
| Cómo se presenta el resultado | HAX-G4 |
| Confianza / incertidumbre | HAX-G2, PAIR-ET-2, PAIR-ET-3 |
| Explicación del "por qué" | HAX-G11, PAIR-ET-1 |
| Override / corrección | HAX-G9, HAX-G16, PAIR-FC-1, PAIR-FC-2 |
| Descarte y temporización / alertas | HAX-G3, HAX-G8 |
| Onboarding | HAX-G1, PAIR-MM-1 |
| Ante incertidumbre / fallo | HAX-G10, PAIR-EF-1, PAIR-EF-2 |
| Supervisión / subgrupos | PAIR-DE-1, HAX-G6 |
| Cambios y controles | HAX-G14, HAX-G17, HAX-G18 |
| Feedback | HAX-G15, PAIR-FC-1 |

El "answer key" (problemas conocidos para validar la herramienta) se recoge **por
separado** y nunca dentro de estas plantillas, para no contaminar la ejecución ciega.

</details>
