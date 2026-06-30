# Qué es esto y cómo sé que funciona

Pues te cuento, sin rodeos. Esto es un revisor automático de la capa de interacción entre una IA y la persona que la usa. No revisa el modelo por dentro. Revisa cómo el sistema le habla al usuario.

Se ve mejor con el coche. Cuando compras uno, todo el mundo te mira el motor: potencia, consumo, lo que contamina. Eso está medido y regulado hasta el último tornillo. Pero casi nadie te pregunta si el salpicadero está bien pensado. Si el aviso de ángulo muerto te salta en buen momento o te despista justo cuando vas a girar. Si puedes silenciar una alerta que no paras de ver. Si entiendes lo que te dice el coche o te fías a ciegas.

Con la IA en sanidad pasa lo mismo. Las herramientas de gobernanza que hay hoy (watsonx, Fiddler, Arize y compañía) auditan el motor: sesgo, precisión, deriva, explicabilidad técnica. El salpicadero no lo mira casi nadie. Y el salpicadero es justo donde un médico decide si se fía del modelo, si lo corrige o si lo ignora. Ahí es donde se cuela el exceso de confianza, la fatiga de alerta, el override que nadie captura, el aviso que llega en mal momento. Eso es lo que revisa esto.

## Qué hace

Le das la descripción de un sistema (qué hace, cómo se le presenta al usuario, qué cuentan los que lo usan) y te devuelve una lista de problemas de esa capa. Pero no problemas de manual. Cada hallazgo va atado a tres anclas. Una guía reconocida que se incumple (uso las 18 de Microsoft y el guidebook de Google, que son el estándar de facto), el punto concreto del sistema donde ocurre, y la prueba sacada de la propia documentación. Si no puede apoyar un hallazgo en evidencia, no lo suelta.

Esto último es a propósito. Un informe lleno de "mejora la explicabilidad" o "ten cuidado con el sesgo" no sirve de nada, porque vale para cualquier sistema. Lo que aporta valor es "aquí, en esta pantalla, el score aparece prerrellenado y eso empuja al médico a aceptarlo sin pensar". Eso sí puedes accionarlo.

## Cómo sé que funciona

Y ahora lo importante, que es cómo sé que esto va en serio y no es humo.

Lo probé contra un caso clínico real que ya estaba trabajado a mano. Un sistema de cribado para priorizar derivaciones a Digestivo, con sus problemas de interacción ya identificados por personas. De los 15 problemas que un humano había encontrado, el revisor redescubre él solo 13 o 14. Sin pistas. Y casi todo lo que señala es real, la precisión ronda el 100%. No te llena el informe de ruido para parecer productivo.

Lo segundo es lo que más me tranquiliza. Le di un sistema bien diseñado, de los que apenas tienen problemas, y se calló. Cero hallazgos. No se inventó nada para justificar que estaba trabajando. Un auditor que siempre encuentra veinticinco fallos es inútil, porque no sabes cuándo creerle.

Lo tercero era descartar que fuese suerte de ese caso. Cogí dos sistemas más, sacados de la literatura, con problemas documentados por gente independiente. Uno clínico distinto y otro que no tiene nada que ver con sanidad. Saca los mismos patrones. No estaba aprendido de memoria al caso de casa.

Y lo cuarto, que no dependiera de cómo le escribo la entrada. Reescribí entera la descripción del sistema, la misma información pero con otras palabras y otro formato. Saca lo mismo. Entiende lo que lee, no pesca palabras clave.

## Qué no es todavía

Seamos honestos. No es un producto cerrado con su botón bonito. Es un motor que funciona y un método que se sostiene. Ya tiene un primer paso de limpieza que quita las repeticiones evidentes sin perder nada por el camino, y eso lo he medido: no se deja ni un problema de los que ya encontraba. Pero la limpieza fina todavía no está. El mismo problema se le puede colar dicho de dos o tres formas cuando lo mira desde guías distintas, y rebajar eso del todo ya no es cosa de reglas, pide la capa lista. Y los casos con los que lo he medido son pocos, los justos para fiarme de la señal pero no para presumir.

## La parte que igual te sorprende

Hay una cosa más, y es la que más me ha costado sacar. La pregunta de partida era si para esto hacía falta un agente de IA de los modernos, de esos que deciden solos qué investigar y cuándo parar. La respuesta, con datos en la mano, es que no.

Un proceso de pasos fijos, mucho más simple y más barato de mantener, funciona igual o mejor. Y es más fiable justo cuando la información que le das está incompleta, que en una auditoría es lo normal. El agente listo, cuando le falta información, se viene arriba, decide que ya ha terminado y deja cosas sin mirar. El proceso ordenado y aburrido las mira todas. Para algo que va a revisar decisiones clínicas, me quedo con lo segundo sin dudarlo.

Así que en una frase. Tengo un revisor que encuentra casi todo lo que encontraría un experto, no se inventa nada, no depende del caso ni de cómo le escribas, y lo hace sin necesidad de la maquinaria más cara. Lo que queda es pulirlo para que dé gusto usarlo.
