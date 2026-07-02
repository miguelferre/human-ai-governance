# Qué es esto y cómo sé que funciona

Pues te cuento, sin rodeos. Esto es un revisor automático de la capa de interacción entre una IA y la persona que la usa. No revisa el modelo por dentro. Revisa cómo el sistema le habla al usuario.

Se ve mejor con el coche. Cuando compras uno, todo el mundo te mira el motor: potencia, consumo, lo que contamina. Eso está medido y regulado hasta el último tornillo. Pero casi nadie te pregunta si el salpicadero está bien pensado. Si el aviso de ángulo muerto te salta en buen momento o te despista justo cuando vas a girar. Si puedes silenciar una alerta que no paras de ver. Si entiendes lo que te dice el coche o te fías a ciegas.

Con la IA en sanidad pasa lo mismo. Las herramientas de gobernanza que hay hoy (watsonx, Fiddler, Arize y compañía) auditan el motor: sesgo, precisión, deriva, explicabilidad técnica. El salpicadero no lo mira casi nadie. Y el salpicadero es justo donde un médico decide si se fía del modelo, si lo corrige o si lo ignora. Ahí es donde se cuela el exceso de confianza, la fatiga de alerta, el override que nadie captura, el aviso que llega en mal momento. Eso es lo que revisa esto.

## Qué hace

Le das la descripción de un sistema (qué hace, cómo se le presenta al usuario, qué cuentan los que lo usan) y te devuelve una lista de problemas de esa capa. Pero no problemas de manual. Cada hallazgo va atado a tres anclas. Una guía reconocida que se incumple (uso las 18 de Microsoft y el guidebook de Google, que son el estándar de facto), el punto concreto del sistema donde ocurre, y la prueba sacada de la propia documentación. Si no puede apoyar un hallazgo en evidencia, no lo suelta.

Esto último es a propósito. Un informe lleno de "mejora la explicabilidad" o "ten cuidado con el sesgo" no sirve de nada, porque vale para cualquier sistema. Lo que aporta valor es "aquí, en esta pantalla, el score aparece prerrellenado y eso empuja al médico a aceptarlo sin pensar". Eso sí puedes accionarlo.

## Cómo se le da de comer

Y para dárselo no hace falta escribir un informe ni pelearse con ningún archivo raro. Son tres plantillas en texto normal que rellena la gente que ya conoce el sistema. Una la rellena quien lo construye o lo mantiene. Otra es el inventario de documentos que hay. Y la tercera, que es la que de verdad marca la diferencia, la rellena el que usa la IA todos los días.

Esa voz, la del que convive con la máquina, es la pieza que ningún otro auditor mira. ¿La acepta por inercia? ¿Puede corregirla cuando se equivoca? ¿La ignora directamente? Ahí está media película. Y cruzar lo que el equipo técnico cree que pasa con lo que el usuario vive ya es, en sí mismo, una señal de que algo en esa capa no encaja.

Rellenas las tres plantillas, ejecutas `ingerir` y te arma el expediente solo, sin tocar JSON ni nada por el estilo. Así preparar la entrada no te cuesta lo mismo que hacer la auditoría a mano.

Y si ya tienes un PDF o una model card del sistema, ni copiar a mano hace falta. El comando `prerrellenar` se lo pasa al modelo, que rellena la ficha con lo que pone en el documento y deja en blanco lo que no aparece, sin inventárselo. Tú lo repasas y a correr. Es el único paso de la entrada que usa el modelo; rellenar las plantillas a mano sigue sin gastar nada.

## Cómo sé que funciona

Y ahora lo importante, que es cómo sé que esto va en serio y no es humo.

Lo probé contra un caso clínico real que ya estaba trabajado a mano. Un sistema de cribado para priorizar derivaciones a Digestivo, con sus problemas de interacción ya identificados por personas. De los 15 problemas que un humano había encontrado, el revisor redescubre él solo 13 o 14. Sin pistas. Y casi todo lo que señala es real, la precisión ronda el 100%. No te llena el informe de ruido para parecer productivo.

Lo segundo es lo que más me tranquiliza. Le di un sistema bien diseñado, de los que apenas tienen problemas, y se calló. Cero hallazgos. No se inventó nada para justificar que estaba trabajando. Un auditor que siempre encuentra veinticinco fallos es inútil, porque no sabes cuándo creerle.

Lo tercero era descartar que fuese suerte de ese caso. Cogí más sistemas sacados de la literatura, con problemas documentados por gente independiente, y ya van ocho sectores que no se parecen en nada, de sanidad a aviación, justicia, finanzas o administración pública. Saca los mismos patrones. No estaba aprendido de memoria al caso de casa.

Lo cuarto, que no dependiera de cómo le escribo la entrada. Reescribí entera la descripción del sistema, la misma información pero con otras palabras y otro formato. Saca lo mismo. Entiende lo que lee, no pesca palabras clave.

Y luego subí la exigencia todo lo que pude. Cogí tres casos donde la respuesta correcta no la puse yo, sino un órgano independiente que ya los había investigado a fondo. Una comisión real, un auditor estatal, un tribunal federal. Le di el material en bruto y con las manos separadas, o sea sin que yo tocara ni la pregunta ni la solución. Aun así recupera entre el 70 y el 90% de lo que ellos señalaron, con una media cerca del 80%. Encuentra por su cuenta lo que encontró gente que se dedica a esto profesionalmente.

Hay un número que es el que más me importa de todos, porque no lo pongo yo. El que corrige el examen es otro modelo distinto del que genera, para que no se apruebe a sí mismo, y todo el proceso está montado para que cualquiera lo repita y le salga lo mismo. Ahí el revisor pilla el 93% de los problemas y, de lo que dice, el 96% es de verdad. Y ojo, con un modelo barato haciendo el trabajo pesado. Y no es de una sola tirada: lo he repetido tres veces por caso y sale prácticamente lo mismo, así que descarto que sea un golpe de suerte.

## La voz del usuario, que es la parte que más me gusta

Antes te decía que la joya es la voz del que usa la IA. Eso no es una corazonada mía, lo he medido a propósito. Cogí los expedientes y les quité esa voz, dejando solo la documentación técnica, la que tendría cualquiera. Y el revisor se queda medio ciego. Los problemas que solo se ven desde la experiencia de quien lo usa pasan de encontrarse ocho de cada diez a apenas tres de cada diez.

Y no es un grupo cualquiera de problemas. Son justo los de la cabeza. El exceso de confianza en la máquina, el fiarse a ciegas, el modelo mental equivocado de lo que la IA hace de verdad, la alerta que salta en mal momento. Nada de eso está en una ficha técnica. Solo lo cuenta quien lo sufre. Por eso insisto tanto con esa segunda plantilla, no es relleno.

## Para el que firma la compra

Una cosa más, muy de andar por casa pero que pesa. El que aprueba pagar esto casi nunca es el que diseña las pantallas. Es gobernanza, calidad, cumplimiento. Y esa gente no razona en guías de diseño, razona en normativa. Así que el informe se traduce solo a su idioma. Cada problema sale también apuntando al artículo del reglamento europeo de IA que toca (el de transparencia, el de supervisión humana, que nombra el exceso de confianza en la máquina con todas las letras) y a la parte del marco americano, el NIST, que le corresponde. Deja de ser una crítica de diseño y pasa a ser papeleo que pueden meter en su expediente. Es orientativo, no un dictamen legal, y así lo dice el propio informe para no vender humo.

Y si hay que enseñarlo en una reunión, saca el informe en una página autocontenida que se imprime a PDF sin depender de nada de fuera. Presentable, vamos.

## Qué no es todavía

Seamos honestos. No es un producto cerrado con su botón bonito. Es un motor que funciona y un método que se sostiene. Ya tiene un paso de limpieza que quita las repeticiones evidentes sin perder nada por el camino, y eso lo he medido, no se deja ni un problema de los que ya encontraba. Luego probé la limpieza fina, la que usa el modelo listo para juntar el mismo problema dicho de cinco maneras distintas. Y aquí va la parte honesta. Limpia bastante más, pero de vez en cuando junta dos problemas que en realidad eran distintos, y en una auditoría eso es peor que dejar un duplicado, porque te esconde algo. Así que de momento me quedo con la limpieza segura por defecto y dejo la otra como opción para revisar a mano.

Lo que queda es más de acabado que de fondo, sobre todo llevar el prerrelleno desde PDF, que ya cubre bien la ficha técnica, a las otras dos plantillas. Nada que cambie la conclusión, cosas de que dé gusto usarlo.

## La parte que igual te sorprende

Hay una cosa más, y es la que más me ha costado sacar. La pregunta de partida era si para esto hacía falta un agente de IA de los modernos, de esos que deciden solos qué investigar y cuándo parar. La respuesta, con datos en la mano, es que no.

Un proceso de pasos fijos, mucho más simple y más barato de mantener, funciona igual o mejor. Y es más fiable justo cuando la información que le das está incompleta, que en una auditoría es lo normal. El agente listo, cuando le falta información, se viene arriba, decide que ya ha terminado y deja cosas sin mirar. El proceso ordenado y aburrido las mira todas. Para algo que va a revisar decisiones clínicas, me quedo con lo segundo sin dudarlo.

Así que en una frase. Tengo un revisor que encuentra casi todo lo que encontraría un experto, no se inventa nada, no depende del caso ni de cómo le escribas, sabe traducirle el resultado al que firma la compra, y lo hace sin necesidad de la maquinaria más cara. Lo que queda es pulirlo para que dé gusto usarlo.
