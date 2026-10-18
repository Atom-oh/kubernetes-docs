# Cuestionario de fundamentos de redes, parte 3: protocolos de aplicación

> **Última actualización**: 14 de septiembre de 2026

Comprueba tus conocimientos sobre los 10 protocolos de la capa de aplicación, desde DNS hasta MQTT.

## Preguntas de opción múltiple

1. Si HTTP/3 está habilitado pero no muestra una mejora de velocidad, ¿qué comprobación de la capa de transporte resulta útil?
   - A) La fecha de vencimiento del certificado del servidor
   - B) Si se puede acceder a UDP 443 y realmente se negoció HTTP/3
   - C) La configuración del TTL de DNS
   - D) La configuración de compresión de encabezados HPACK de HTTP/2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Si se puede acceder a UDP 443 y realmente se negoció HTTP/3**

**Explicación:**
HTTP/3 suele usar QUIC sobre UDP 443. Si esa ruta está bloqueada, cuando sea posible, el cliente puede usar HTTP/2 o HTTP/1.1 basados en TCP. Verifique el protocolo negociado antes de comparar el rendimiento. La pérdida, el RTT, la carga de trabajo, la implementación y el comportamiento de la CPU y de la descarga de trabajo al hardware influyen en el resultado; esta pregunta no establece la causa de un incidente real.

</details>

2. ¿Qué factor puede retrasar la conmutación por error de DNS después de cambiar un registro autoritativo?
   - A) DNS usa únicamente TCP, por lo que el costo del protocolo de enlace es alto
   - B) Las respuestas almacenadas previamente en caché, la caché de la aplicación y las conexiones existentes pueden seguir vigentes después del cambio del registro
   - C) Los servidores de nombres raíz deben aprobar la actualización
   - D) Los registros A no se pueden cambiar

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Las respuestas almacenadas previamente en caché, la caché de la aplicación y las conexiones existentes pueden seguir vigentes después del cambio del registro**

**Explicación:**
Reducir el TTL ahora no acorta la duración de una respuesta que ya se almacenó en caché con un TTL anterior más largo. La detección de fallos, las actualizaciones de registros, la caché de la aplicación y la reutilización de conexiones también afectan a la recuperación. En condiciones de fallo definidas, los resolutores pueden servir datos obsoletos (RFC 8767). Los diseños de DNS, balanceador de carga y anycast requieren medir el comportamiento ante fallos y la convergencia.

</details>

3. ¿Qué problema de políticas puede surgir cuando un navegador elige un resolutor público de DoH no aprobado?
   - A) Las respuestas de DNS aumentan de tamaño y desperdician ancho de banda
   - B) Puede eludir las políticas del resolutor de la organización y no resolver nombres privados
   - C) Se sobrecarga el puerto UDP 53
   - D) Es incompatible con DNSSEC

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Puede eludir las políticas del resolutor de la organización y no resolver nombres privados**

**Explicación:**
DoH protege con HTTPS el tramo entre el cliente y el resolutor, incluida la integridad. Un resolutor público independiente puede eludir los controles del resolutor de la organización, aunque DoH administrado también puede aplicar políticas y proporcionar registros. Seleccione resolutores aprobados mediante una política de endpoints y pruebe el DNS dividido. El cifrado no vuelve invisible el endpoint del resolutor ni todos los metadatos del tráfico.

</details>

4. ¿Por qué un balanceador de carga L4 puede concentrar el tráfico gRPC en unos pocos backends?
    - A) La serialización de Protocol Buffers es asimétrica
    - B) Muchas llamadas RPC pueden compartir conexiones de larga duración, mientras que el balanceo L4 selecciona backends por conexión
    - C) La compresión de encabezados HTTP/2 deja de funcionar en el balanceador
    - D) gRPC se basa en UDP, por lo que el balanceo L4 es imposible

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Muchas llamadas RPC pueden compartir conexiones de larga duración, mientras que el balanceo L4 selecciona backends por conexión**

**Explicación:**
Un canal gRPC puede usar cero o más conexiones HTTP/2. Un pequeño número de conexiones de larga duración puede transportar muchas llamadas RPC, y un balanceador L4 no redistribuye cada llamada RPC. Una política adecuada en el cliente o un proxy L7 compatible con gRPC puede mejorar la distribución de solicitudes; un flujo establecido permanece en su backend.

</details>

5. ¿Qué emparejamiento problema → respuesta para operar servicios WebSocket es INCORRECTO?
    - A) Desconexiones por tiempos de espera de inactividad del balanceador → mantener la conexión activa con tramas ping/pong
    - B) Oleadas de reconexiones durante las implementaciones → retroceso exponencial con fluctuación aleatoria (jitter)
    - C) Distribuir eventos de aplicación entre instancias → usar mensajería como Redis Pub/Sub, mientras cada socket sigue siendo propiedad local
    - D) Un proxy bloquea el encabezado Upgrade → subir a QoS 2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Un proxy bloquea el encabezado Upgrade → subir a QoS 2**

**Explicación:**
Los niveles de QoS pertenecen a MQTT y no reparan los protocolos de enlace de WebSocket. HTTP/1.1 usa Upgrade, mientras que HTTP/2 y HTTP/3 usan Extended CONNECT cuando es compatible. Los latidos deben ajustarse al comportamiento del tiempo de espera de inactividad; el retroceso y el drenaje reducen los picos de reconexión. Pub/Sub puede distribuir eventos de aplicación, pero no migra sockets ni garantiza por sí solo la entrega duradera de mensajes.

</details>

6. ¿Qué asociación identifica correctamente las funciones de los tres mecanismos de autenticación de dominios de correo electrónico (SPF, DKIM y DMARC)?
    - A) SPF: firma de mensajes / DKIM: publicación de las IP de remitentes permitidas / DMARC: aplicación del cifrado
    - B) SPF: autorizar hosts para identidades de sobre/HELO / DKIM: firmar el contenido cubierto con una clave de dominio / DMARC: alinear el dominio visible de From con SPF o DKIM que hayan superado la comprobación y publicar una política
    - C) SPF: autenticación del servidor receptor / DKIM: cifrado del transporte / DMARC: filtrado de spam
    - D) SPF: administración de la cola de correo / DKIM: validación de registros MX / DMARC: aplicación de TLS

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) SPF: autorizar hosts para identidades de sobre/HELO / DKIM: firmar el contenido cubierto con una clave de dominio / DMARC: alinear el dominio visible de From con SPF o DKIM que hayan superado la comprobación y publicar una política**

**Explicación:**
SPF comprueba el dominio del sobre/HELO y DKIM verifica el contenido cubierto para el dominio que firma. DMARC requiere al menos un mecanismo que haya superado la comprobación y esté alineado con el dominio visible de From; no exige que ambos la superen. Estos mecanismos ayudan a proteger los dominios, pero no garantizan la entrega ni impiden la suplantación mediante nombres para mostrar o dominios parecidos.

</details>

7. Una solicitud HTTP/1.1 comienza con `POST /echo HTTP/1.1` y su respuesta con `HTTP/1.1 200 OK`. ¿Cuál es la interpretación correcta?
   - A) `POST` es un campo de encabezado y `/echo` es el estado de respuesta
   - B) `200` es la longitud del cuerpo y `OK` determina si la solicitud tuvo éxito
   - C) La línea de solicitud contiene el método, el destino y la versión; la línea de estado contiene la versión, el código de estado y una frase descriptiva opcional
   - D) La primera línea en blanco termina todo el mensaje, incluido el cuerpo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) La línea de solicitud contiene el método, el destino y la versión; la línea de estado contiene la versión, el código de estado y una frase descriptiva opcional**

**Explicación:**
POST solicita que el destino procese el contenido proporcionado; 200 es un estado de éxito. Las líneas de campos de encabezado vienen después de la línea inicial, y luego una línea en blanco termina la sección de encabezados. El cuerpo solo aparece cuando las reglas del mensaje lo permiten. HTTP/1.1 usa CRLF como terminadores de línea en el protocolo, aunque un ejemplo ilustrativo se muestre con LF.

</details>

8. El único contenido del cuerpo de un mensaje HTTP/1.1 son los cinco bytes ASCII `hello`, sin salto de línea final ni codificación de contenido o de transferencia. ¿Qué cuenta `Content-Length: 5`?
   - A) El mensaje completo, incluidas la línea inicial y los encabezados
   - B) Solo los cinco bytes del cuerpo; `Content-Type` describe por separado su tipo de medio
   - C) Cinco caracteres Unicode, independientemente de su codificación en bytes
   - D) El número de paquetes TCP que transportan el cuerpo

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: B) Solo los cinco bytes del cuerpo; `Content-Type` describe por separado su tipo de medio**

**Explicación:**
Content-Length cuenta bytes y excluye la línea inicial, los encabezados y el separador de línea en blanco. El texto ASCII `hello` ocupa cinco bytes; si se añadiera un LF real, serían seis. Los caracteres UTF-8 que no sean ASCII pueden ocupar varios bytes. Content-Type indica al destinatario cómo interpretar la representación, no dónde termina el mensaje.

</details>

9. Una respuesta HTTP/1.1 `200` válida a GET usa `Transfer-Encoding: chunked` y mantiene abierta la conexión TCP. ¿Cómo se delimita el cuerpo?
   - A) Mediante los límites de los paquetes TCP
   - B) Solo mediante Content-Type
   - C) Mediante un Content-Length obligatorio que se envía junto con Transfer-Encoding
   - D) Mediante el encuadre por fragmentos, que termina con el fragmento de tamaño cero, los tráileres que pueda haber y la línea en blanco final

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: D) Mediante el encuadre por fragmentos, que termina con el fragmento de tamaño cero, los tráileres que pueda haber y la línea en blanco final**

**Explicación:**
El encuadre por fragmentos identifica el final sin cerrar la conexión. El emisor no debe enviar Content-Length junto con Transfer-Encoding. TCP es un flujo de bytes: un mensaje puede abarcar varios paquetes y un paquete puede transportar bytes de más de un mensaje.

</details>

10. Una respuesta HTTP/1.1 válida a HEAD incluye `Content-Length: 500`. ¿Debe el cliente leer 500 bytes del cuerpo después de la sección de encabezados?
   - A) No; una respuesta a HEAD no tiene cuerpo de mensaje y el campo describe la longitud que tendría una respuesta GET correspondiente
   - B) Sí; Content-Length siempre prevalece sobre el método
   - C) Sí, pero solo si Content-Type es text/plain
   - D) No; Content-Length está prohibido en todas las respuestas a HEAD

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: A) No; una respuesta a HEAD no tiene cuerpo de mensaje y el campo describe la longitud que tendría una respuesta GET correspondiente**

**Explicación:**
Las reglas del método y del estado tienen prioridad sobre el encuadre genérico de longitud. Las respuestas a HEAD no llevan cuerpo; el campo de longitud permitido es metadato. Las respuestas con estado 1xx, 204 o 304 tampoco tienen cuerpo, con restricciones específicas sobre los campos que se permiten.

</details>

11. Una herramienta cliente muestra encabezados legibles de una solicitud HTTPS negociada como HTTP/2. ¿Qué se debe esperar en una captura pasiva sin secretos de sesión?
   - A) La misma línea de solicitud en texto sin cifrar `GET ... HTTP/1.1`
   - B) Encabezados visibles en texto sin cifrar y solo el cuerpo cifrado
   - C) Datos de aplicación protegidos; HTTP/2 usa tramas binarias y la herramienta muestra los campos decodificados
   - D) Tamaños de fragmentos HTTP/1.1 que separan cada flujo HTTP/2

<details>
<summary>Mostrar respuesta</summary>

**Respuesta: C) Datos de aplicación protegidos; HTTP/2 usa tramas binarias y la herramienta muestra los campos decodificados**

**Explicación:**
TLS protege los encabezados y el contenido HTTP/2 en una conexión HTTPS. HTTP/2 usa tramas HEADERS/DATA sobre TCP; HTTP/3 usa sus propias tramas en flujos QUIC protegidos. Ambos conservan la semántica HTTP, pero ninguno usa líneas iniciales textuales ni codificación de transferencia por fragmentos de HTTP/1.1. Observe los mensajes decodificados en un endpoint autorizado o en el punto de terminación.

</details>

---

[Volver al material de estudio](../../basics/06-network-fundamentals-part3.md) | [Siguiente cuestionario: parte 4](./06-network-fundamentals-part4-quiz.md)

Repase la [estructura de mensajes HTTP, el encuadre y la visibilidad](../../basics/06-network-fundamentals-part3.md#http11-message-structure), incluidas sus referencias principales.
