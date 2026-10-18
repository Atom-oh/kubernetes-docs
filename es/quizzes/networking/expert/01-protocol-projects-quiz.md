# Cuestionario sobre proyectos de protocolos

> **Última actualización**: 15 de septiembre de 2026

Lee primero [Proyectos de protocolos](../../../networking/expert/01-protocol-projects.md).
Elige la mejor respuesta para cada pregunta y explica qué pruebas adicionales cambiarían tu conclusión.

1. ¿Qué plan de estudio refleja correctamente la comprobación de disponibilidad del 15 de septiembre de 2026?
   - A) Tratar el sitio incompleto de CS168 de otoño de 2026 como un calendario de tareas completo e inamovible.
   - B) Usar el archivo oficial del verano de 2026, registrar el periodo y comprobar los requisitos de acceso aparte para las tareas.
   - C) Exigir un calificador actual de CS144 disponible gratuitamente para completar este cuaderno.
   - D) Cambiar el Python del entorno invitado a Python 3.7 para todos los ejercicios.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** Se puede acceder al archivo del verano, mientras que el sitio de otoño está en construcción. Una especificación pública no garantiza acceso a la calificación institucional. CS144 es opcional y su entrada histórica devolvió 404. Las notas archivadas sobre pruebas con Python pertenecen al entorno de esa tarea, no al entorno invitado Python 3.9+ del cuaderno.

</details>

2. Una sonda UDP usa `192.0.2.10:41000 → 198.51.100.20:33452`. Una respuesta ICMP Time Exceeded incluye el destino `198.51.100.99` con los mismos puertos. ¿Qué debe hacer el registro?
   - A) Asociarla a la sonda porque coinciden ambos puertos.
   - B) Asociarla si la dirección del router exterior parece plausible.
   - C) Marcarla como no relacionada con esta sonda y conservar el destino diferente.
   - D) Reescribir el registro de envío para que coincida con la respuesta.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** La correlación usa el paquete original citado, incluidas sus direcciones y su protocolo. La coincidencia de los puertos no compensa un destino diferente. La dirección de origen exterior identifica al remitente del error, no a la sonda original. Conserva el registro como prueba sin permitir que cuente como respuesta esperada.

</details>

3. Ninguna respuesta coincide con la sonda de TTL 2, pero una sonda UDP de TTL 3 tiene un mensaje Destination Port Unreachable correlacionado. ¿Qué se deduce?
   - A) El segundo router descarta todo el tráfico de aplicaciones.
   - B) Hay pruebas de que la sonda de TTL 3 llegó al destino; no se observó la de TTL 2.
   - C) El router que no respondió tiene un RTT de cero.
   - D) Las respuestas TTL 1 duplicadas pueden completar el salto que falta.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** La falta de una respuesta dentro del plazo es un límite de observación. El filtrado, los límites de frecuencia de respuestas o el comportamiento de la ruta de retorno pueden ocultar la respuesta intermedia. La prueba posterior de llegada al destino no identifica ese router intermedio ni demuestra una ruta fija para la aplicación. Las respuestas duplicadas siguen siendo duplicados.

</details>

4. El protocolo de encuadre, que usa un campo de longitud de dos bytes, recibe los mismos bytes completos en cuatro particiones distintas de `recv()`. ¿Qué resultado se requiere?
   - A) Un registro de aplicación por cada `recv()`.
   - B) Los mismos registros lógicos para cada partición completa.
   - C) Si se fragmenta el campo de longitud, hay que cerrar la conexión de inmediato.
   - D) EOF durante un cuerpo completa ese cuerpo.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** TCP expone un flujo de bytes, no límites de mensajes. El analizador debe conservar los encabezados y cuerpos parciales, y emitir los registros completos de forma coherente. EOF durante un cuerpo es un error de truncamiento y se rechaza una longitud superior al límite elegido antes de asignar memoria sin límite. Estas son propiedades del protocolo del ejercicio original, no una solución para el proyecto universitario.

</details>

5. Un emisor tiene una ventana de recepción anunciada grande, pero una ventana de congestión pequeña. ¿Por qué podría enviar datos lentamente?
   - A) La capacidad disponible del receptor elimina todos los límites del emisor.
   - B) El control de congestión puede limitar los datos en tránsito de forma independiente del control de flujo del receptor.
   - C) La ventana de recepción y la ventana de congestión son dos nombres para el mismo campo.
   - D) El Proyecto 3 de CS168 implementa todos los controladores de congestión necesarios para decidirlo.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** El control de flujo del receptor protege el extremo receptor; el control de congestión limita la carga en la ruta. También influyen los bytes pendientes, la temporización de envío y los datos disponibles en la aplicación. El Proyecto 3 archivado de CS168 excluye explícitamente el control de congestión, así que completarlo no valida un controlador de producción.

</details>

6. Una conexión capturada tiene un SYN con número de secuencia 1000 y luego seis bytes de carga útil a partir de 1001. Si no hay huecos, ¿qué ACK del siguiente byte corresponde a la recepción de esa carga útil?
   - A) 1006
   - B) 1007
   - C) 1008 porque un ACK sin datos consume una posición
   - D) El número de segmentos determina la respuesta

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** SYN consume una posición de secuencia. La carga útil ocupa las posiciones 1001 a 1006, por lo que el siguiente byte esperado es 1007. Un ACK sin datos no consume espacio de secuencia; FIN consumiría una posición adicional si estuviera presente. El recuento se basa en los bytes del flujo, no en cómo el software de captura agrupa los paquetes.

</details>

7. `curl` se ejecuta correctamente sin `--fail` y muestra HTTP 404 para `/missing`. ¿Qué se ha demostrado?
   - A) No se llegó a ningún servidor HTTP.
   - B) El recurso solicitado existe.
   - C) La comunicación HTTP finalizó con una búsqueda fallida del recurso.
   - D) La suma de comprobación TCP debe ser incorrecta.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** El éxito del transporte o de la herramienta y el estado de la aplicación son cosas distintas. La ruta negativa es un fallo deliberado de la aplicación, entregado a través de una conexión HTTP funcional. Inspecciona el estado y el cuerpo en lugar de interpretar el código de salida cero como éxito de la operación solicitada. Añadir `--fail` cambia la forma en que curl gestiona los estados HTTP de error, no el resultado del servidor.

</details>

8. ¿Qué prueba respalda mejor una afirmación sobre HTTP/3?
   - A) Un paquete UDP arbitrario dirigido al puerto 443.
   - B) Una línea de comandos que contiene `--http3`, sin importar el fallback ni la compatibilidad de la herramienta.
   - C) Pruebas del endpoint de QUIC y de la negociación de HTTP/3, con la capacidad del cliente registrada.
   - D) Salida HTTP/1.1 del servidor de ejemplo de loopback de la lección.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** Los números de puerto y los modos solicitados no demuestran cuál fue el protocolo negociado. `--http3` puede recurrir a otro protocolo; `--http3-only` se comporta de otra manera y también requiere una compilación compatible. QUIC transporta flujos sobre UDP, mientras que HTTP/3 asigna HTTP a esos flujos. Se sigue compartiendo el control de congestión, aunque los flujos independientes evitan el bloqueo de entrega entre flujos propio de TCP.

</details>

9. ¿Qué cambia al extender a IPv6 el registro ICMP?
   - A) Solo hay que cambiar el nombre de TTL; los desplazamientos de encabezado y el tipo ICMP son idénticos.
   - B) Usar Hop Limit, tener en cuenta los encabezados de extensión de IPv6 y los tipos de ICMPv6, y registrar la familia y el ámbito.
   - C) Suponer que los routers fragmentan los paquetes IPv6 reenviados.
   - D) Tratar una respuesta AAAA como prueba de que el entorno invitado tiene una ruta IPv6.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B**

**Explicación:** El análisis de IPv6 y los tipos de error ICMPv6 son diferentes. Los routers no fragmentan los paquetes reenviados; Packet Too Big sirve para un diagnóstico distinto de Time Exceeded. Los datos AAAA confirman un resultado de resolución de nombres, no que exista una ruta utilizable. El descubrimiento de vecinos de IPv6 también difiere de ARP.

</details>

10. La captura alcanza el límite de 20 segundos antes de que aparezca el cierre de la conexión. ¿Cuál es el registro de finalización correcto?
   - A) Declarar que el servidor no puede cerrar conexiones.
   - B) Ocultar el estado de timeout e inferir que faltan paquetes FIN.
   - C) Registrar el resultado del temporizador y la cobertura parcial, detener el auxiliar y comprobar el listener.
   - D) Detener todos los procesos que usen TCP y volver a capturar sin límite.

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C**

**Explicación:** El plazo de captura es un límite de recopilación. Conserva el estado de salida y los contadores de captura, y marca el cierre como no observado en lugar de fallido. Detén solo el auxiliar en primer plano que hayas iniciado o deja que venza su temporizador; después, verifica el filtro del listener. Del mismo modo, un análisis sin conexión limitado por privilegios debe seguir etiquetado como tal.

</details>

Vuelve a los [criterios de finalización del cuaderno](../../../networking/expert/01-protocol-projects.md#completion) o al [mapa del curso avanzado](../../../networking/expert/README.md).
