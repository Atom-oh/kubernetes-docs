# Fundamentos de redes, parte 3 — Diez protocolos de aplicación

> **Última actualización**: September 14, 2026

::: tip Esta es una serie de cuatro partes
[Parte 1: El modelo de capas, enlace y enrutamiento](./06-network-fundamentals-part1.md) ·
[Parte 2: La capa de transporte y TLS](./06-network-fundamentals-part2.md) ·
**Parte 3: Protocolos de aplicación** *(este documento)* ·
[Parte 4: El recorrido de una solicitud y la nube](./06-network-fundamentals-part4.md)
:::

Los protocolos de transporte proporcionan flujos o datagramas; los protocolos de aplicación los convierten en servicios. Esta parte cubre la resolución de nombres (DNS y DoH), el arranque (DHCP), el acceso operativo (SSH), el correo (SMTP), y HTTP/3, WebSocket, WebRTC, gRPC y MQTT.

---

## 5. Capa de aplicación — Servicios reales

### DNS

**Definición:** El sistema de directorio distribuido que resuelve nombres de dominio en direcciones IP y otros registros.

**Cómo funciona:** DNS utiliza delegación jerárquica. Ante una ausencia en caché, un resolver recursivo sigue referencias desde la raíz hasta el TLD y los servidores de nombres autoritativos, o reenvía a otro resolver. Las respuestas almacenadas en caché pueden evitar parte o todo ese trabajo. Los registros A/AAAA contienen direcciones, los registros CNAME alias, los registros MX servidores de correo y los registros TXT texto utilizado por varios protocolos.

**En la práctica:** DNS está distribuido, pero un resolver, proveedor o configuración puede convertirse en una dependencia compartida. Para la conmutación por error de DNS, tenga en cuenta la detección de fallos, las actualizaciones de registros, el TTL de las respuestas ya almacenadas en caché, el almacenamiento en caché de la aplicación y las conexiones existentes. Reducir el TTL ahora no acorta el TTL de una respuesta antigua almacenada en caché. Algunos resolvers también sirven respuestas obsoletas bajo condiciones de fallo definidas (RFC 8767). Mida cada etapa; un TTL corto por sí solo no garantiza el tiempo de conmutación por error. Los balanceadores de carga y anycast pueden complementar DNS, con sus propios límites de detección de salud y convergencia.

**Tipos de registros comunes de un vistazo:**

| Tipo | Propósito | Nota práctica |
|---|---|---|
| A / AAAA | Dominio → IPv4 / IPv6 | Lo básico |
| CNAME | Alias → nombre canónico | No puede coexistir con SOA/NS del ápice; ALIAS/ANAME específicos del proveedor o Route 53 Alias pueden ofrecer mapeo del ápice a destinos compatibles |
| MX | Servidor que recibe correo | Gana el número de prioridad más bajo |
| TXT | Cadenas arbitrarias | SPF/DKIM/DMARC, verificación de propiedad del dominio |
| NS | Servidores de nombres delegados | Delegación de subzona |
| SRV | Ubicación del servicio (host+port) | Descubrimiento para algunos protocolos |
| CAA | Restringir emisores de certificados autorizados | Requiere aplicación por parte de la CA; por sí solo no evita toda emisión incorrecta |

**DNSSEC y DoH resuelven problemas diferentes.** DNSSEC autentica los datos DNS firmados y su integridad mediante una cadena de confianza validada; no cifra las consultas. DoH utiliza HTTPS para autenticar el resolver elegido y proteger la confidencialidad e integridad en el salto entre cliente y resolver. No demuestra que un resolver malicioso o equivocado haya devuelto datos autoritativos. Pueden utilizarse juntos.

![Muestra la resolución DNS recursiva: la consulta del stub resolver recorre el resolver recursivo hasta los servidores de nombres raíz, TLD y autoritativos, y la respuesta se almacena en caché durante su TTL.](../.gitbook/assets/en-basics-06-network-fundamentals-part3-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part3-0.html)

### DoH

**Definición:** Consultas DNS encapsuladas y transportadas sobre HTTPS.

**Cómo funciona:** DNS tradicional utiliza habitualmente UDP **y TCP** en texto sin cifrar por el puerto 53. DoH transporta mensajes DNS sobre HTTPS, protegiéndolos de la inspección pasiva y la modificación en ese salto. Los endpoints del resolver y los metadatos de tráfico aún pueden identificar el uso de DoH; el resolver elegido puede ver las consultas.

**En la práctica:** Un resolver DoH público seleccionado de forma independiente puede omitir el filtrado o registro del resolver de la organización y no resolver nombres privados. DoH no deshabilita inherentemente las políticas: un resolver DoH administrado puede aplicar registro/filtrado, y las políticas del navegador/SO pueden seleccionar resolvers aprobados. Pruebe DNS dividido y la política de endpoints en lugar de asumir que siempre es necesario deshabilitar el cifrado.

### DHCP

**Definición:** El protocolo que asigna automáticamente a los hosts una dirección IP y configuración de red.

**Cómo funciona:** Un intercambio inicial común de **DHCPv4** es DORA: Discover → Offer → Request → Acknowledge. Una difusión local o un relay DHCP localiza un servidor. El lease puede incluir dirección IPv4, máscara de subred, gateway y configuración DNS. La renovación puede utilizar un intercambio más corto. DHCPv6 utiliza mensajes diferentes; la información del router predeterminado de IPv6 proviene normalmente de Router Advertisements, y SLAAC es otro mecanismo de configuración de direcciones.

**En la práctica:** En la nube está mayormente abstraído, pero vuelve a aparecer en el conjunto de opciones DHCP de la VPC, donde se configuran los servidores DNS y los nombres de dominio. Cuando falla la resolución de nombres en una configuración híbrida que utiliza DNS on-premises, esta es la configuración que debe revisar.

### SSH

**Definición:** El protocolo que proporciona acceso remoto cifrado a shell y tunelización.

**Cómo funciona:** El servidor se autentica con su host key, un intercambio de claves deriva claves de sesión y, después, el usuario se autentica (clave pública o contraseña). Todo el tráfico posterior se cifra. Además de shells remotos, SSH admite reenvío de puertos, SFTP y reenvío de agentes.

**En la práctica:** Restrinja el reenvío según la política de acceso y valide las host keys del servidor. Un host comprometido con acceso a un socket de agente reenviado puede solicitar firmas/autenticación al agente; normalmente, el reenvío no copia allí el material de la clave privada. Prefiera un jump host (`ProxyJump`) cuando el reenvío de agentes no sea necesario. Las claves sin procesar no tienen caducidad intrínseca, pero OpenSSH admite períodos de validez de certificados y restricciones de caducidad de `authorized_keys`. Elimine el acceso de los usuarios que se marchen y rote o revoque las credenciales.

AWS Systems Manager Session Manager puede proporcionar acceso a shell sin puertos SSH entrantes ni distribución de claves SSH, siempre que el nodo administrado, los permisos de IAM y la conectividad del servicio estén configurados. CloudTrail registra la actividad de API; el registro del contenido de shell en CloudWatch Logs/S3 requiere configuración. **El registro del contenido de sesión no está disponible para las sesiones SSH y de reenvío de puertos de Session Manager.** El acceso basado en IAM por sí solo no implica que se registre cada comando.

### SMTP

**Definición:** El protocolo que retransmite mensajes entre servidores de correo.

**Cómo funciona:** Los clientes envían correo a un servidor de envío, y los servidores SMTP retransmiten y reciben mensajes, comúnmente utilizando una búsqueda MX para el enrutamiento. IMAP y POP3 permiten a los usuarios recuperar o acceder a mensajes ya almacenados en un buzón; no reemplazan la recepción del lado del servidor de SMTP.

**En la práctica:** La autenticación SMTP y TLS protegen el envío/transporte, pero por sí solos no demuestran el dominio del remitente visible. Importan tres mecanismos de dominio complementarios:

- **SPF** — autoriza hosts emisores para la identidad MAIL FROM o HELO del sobre; esto no es automáticamente el encabezado From visible.
- **DKIM** — verifica una firma sobre el contenido del mensaje incluido usando la clave DNS del dominio firmante; el dominio firmante puede diferir del dominio From visible.
- **DMARC** — exige que el dominio From visible se alinee con una identidad SPF **o** DKIM válida, y publica la política solicitada de manejo/generación de informes.

Configure SPF, DKIM y DMARC juntos cuando corresponda, supervise los informes y tenga en cuenta el comportamiento de reenvío/listas de correo. DMARC puede aprobar con un mecanismo alineado. Estos controles no garantizan la entrega ni eliminan la suplantación mediante nombres visibles o dominios parecidos; los receptores también aplican políticas locales.

### HTTP/3

**Definición:** La tercera versión principal de HTTP, que se ejecuta sobre QUIC.

**Cómo funciona:** La semántica HTTP se comparte entre versiones, pero HTTP/3 utiliza flujos QUIC y su propio framing y mapeo. Elimina la dependencia de ordenación entre flujos de TCP; las pérdidas dentro de un flujo, las dependencias de QPACK y el control de congestión compartido aún pueden retrasar el trabajo. Un handshake completo típico toma alrededor de 1 RTT, y la migración compatible puede preservar una conexión ante un cambio de dirección. QPACK reemplaza HPACK para adaptarse a flujos entregados de forma independiente.

**En la práctica:** Los clientes pueden descubrir HTTP/3 mediante `Alt-Svc`, conocimiento previo o registros DNS HTTPS que anuncian un protocolo compatible. `Alt-Svc` puede aprenderse mediante una conexión TCP anterior; un cliente que admite el registro HTTPS puede descubrir HTTP/3 antes de ese intercambio. Ningún método garantiza la accesibilidad ni un ahorro de latencia concreto.

La entrega independiente y los handshakes integrados pueden ayudar en rutas con pérdidas o alta latencia. La latencia, el rendimiento y el coste de CPU reales dependen de la implementación, las descargas, la carga de trabajo y las condiciones de red. Mida tráfico representativo móvil y de centro de datos en lugar de asumir una ganancia o pérdida universal.

**Las tres generaciones en paralelo:**

| | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| Transporte | TCP | TCP | QUIC (UDP) |
| Solicitudes por conexión | Secuenciales, o canalizadas con respuestas ordenadas | Multiplexadas | Multiplexadas |
| Bloqueo HOL | Respuestas ordenadas y entrega TCP | Ordenación TCP entre flujos | Sin ordenación TCP entre flujos; persisten otros bloqueos |
| Compresión de encabezados | Ninguna | HPACK | QPACK |
| Cifrado | Opcional (HTTPS) | TLS para HTTPS; también existe HTTP/2 en texto sin cifrar | TLS 1.3 integrado en QUIC |

La multiplexación cambia dónde surgen las dependencias de ordenación; HTTP/3 reduce una fuente de bloqueo sin eliminar todas las dependencias de planificación, control de flujo o aplicación.

#### Lectura de solicitudes y respuestas HTTP/1.1 {#http11-message-structure}

Las versiones de HTTP comparten métodos, códigos de estado y semántica de campos. HTTP/1.1 hace visibles esos conceptos como una **línea inicial → líneas de campos de encabezado → línea en blanco → cuerpo opcional**. Un cuerpo puede contener datos de texto o binarios; «HTTP/1.1 textual» describe su línea inicial y encabezados, no toda carga útil.

Estos son **mensajes HTTP/1.1 ilustrativos, no salida capturada ni una receta de comandos**. Para facilitar la lectura, la visualización utiliza saltos de línea LF. En el cable, la línea inicial y cada línea de encabezado terminan en **CRLF (`\r\n`)**, y un CRLF adicional termina la sección de encabezados. Cada cuerpo de abajo tiene exactamente **5 bytes ASCII**, `hello`, **sin salto de línea final**; el salto de línea de la visualización antes del cierre de la cerca no forma parte del cuerpo.

Cliente → servidor:

```http
POST /echo HTTP/1.1
Host: example.test
Content-Type: text/plain; charset=utf-8
Content-Length: 5

hello
```

Servidor → cliente:

```http
HTTP/1.1 200 OK
Date: Mon, 14 Sep 2026 00:00:00 GMT
Content-Type: text/plain; charset=utf-8
Content-Length: 5

hello
```

| Elemento | Cómo leerlo |
|---|---|
| Línea de solicitud | `POST` es el método, `/echo` el destino de la solicitud (aquí una ruta) y `HTTP/1.1` la versión. El campo obligatorio `Host` proporciona el nombre de host de destino y el puerto opcional (autoridad). |
| Línea de estado | `HTTP/1.1` es la versión, `200` el código de estado y `OK` una frase de motivo opcional. Utilice el código para interpretar el resultado. |
| Campos de encabezado | Las líneas `Name: value` llevan metadatos; los nombres de los campos no distinguen mayúsculas de minúsculas. `Content-Type` describe el tipo de medio de la representación y, aquí, su juego de caracteres. |
| Línea en blanco | Termina la sección de encabezados. No especifica dónde termina un cuerpo posterior. |
| Cuerpo | Los bytes de contenido. Aquí, `Content-Length: 5` delimita cinco bytes, excluidas la línea inicial, los encabezados y el separador. Cuente bytes, no caracteres Unicode. |

**El significado y el framing responden preguntas diferentes.** Un método expresa la acción solicitada: GET recupera una representación, HEAD solicita los metadatos de la respuesta correspondiente sin contenido de respuesta y POST solicita al destino que procese el contenido proporcionado. Las clases de estado resumen el resultado: 1xx informativo, 2xx éxito, 3xx redirección, 4xx error del cliente y 5xx error del servidor. `Content-Type` explica cómo interpretar el contenido; no lo delimita. Consulte [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) para estas semánticas compartidas.

El framing de HTTP/1.1 determina cuántos bytes pertenecen a este mensaje en un flujo TCP reutilizable. Para un mensaje ordinario que contiene cuerpo, un `Content-Length` válido sin `Transfer-Encoding` proporciona su longitud. Con `Transfer-Encoding: chunked`, los tamaños de los chunks y el chunk final de tamaño cero, seguidos de cualquier trailer y la línea en blanco final, delimitan el cuerpo en su lugar. Un emisor no debe enviar ambos campos. Algunas respuestas utilizan el cierre de conexión como delimitador; los límites de paquetes TCP nunca delimitan mensajes HTTP.

Las reglas de método/estado son prioritarias: las respuestas a HEAD y las respuestas con estado 1xx, 204 o 304 no tienen cuerpo de mensaje, incluso si los metadatos permitidos describen una representación. Una respuesta CONNECT exitosa inicia un túnel. Una solicitud sin longitud ni codificación de transferencia no tiene cuerpo. Estas distinciones evitan leer el mensaje siguiente como contenido ([RFC 9112 §§2–6](https://www.rfc-editor.org/rfc/rfc9112.html)).

**HTTP/2 y HTTP/3 conservan el significado, pero utilizan framing binario**, incluidos frames HEADERS y DATA, en lugar de estas líneas iniciales textuales y límites CRLF. HTTP/2 utiliza TCP; HTTP/3 mapea los mensajes en flujos QUIC. Ninguno utiliza codificación de transferencia chunked de HTTP/1.1. Una herramienta puede presentar los campos decodificados como texto legible sin mostrar su codificación real en el cable ([RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html), [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html)).

Con HTTPS, TLS protege los encabezados y cuerpos HTTP en tránsito; una captura pasiva sin secretos de sesión no expone este texto sin cifrar ([RFC 8446 §5](https://www.rfc-editor.org/rfc/rfc8446.html#section-5)). QUIC también protege los datos de aplicación HTTP/3. Inspeccione los mensajes decodificados en un endpoint autorizado o punto de terminación TLS, e identifique qué tramo de conexión se está observando.

> 📎 Continúe con el [laboratorio de mensajes HTTP en Linux](../networking/07-linux-network-diagnostics.md#http-message-lab) antes de aplicar las mismas distinciones a los servicios de contenedores, Kubernetes Ingress o balanceadores de carga de AWS.

### WebSocket

**Definición:** Un protocolo de aplicación para mensajería bidireccional sobre una única conexión.

**Cómo funciona:** El handshake HTTP/1.1 utiliza `Upgrade` y una respuesta `101` exitosa. HTTP/2 y HTTP/3 usan Extended CONNECT en su lugar (RFC 8441 y 9220), cuando se admite. Una vez establecido, cualquiera de los pares puede enviar mensajes WebSocket sin sondeo HTTP repetido.

**En la práctica:** Planifique conexiones de larga duración: tráfico de heartbeat dentro del timeout de inactividad relevante, drenaje ordenado durante el Deployment y backoff de reconexión con jitter. Cada socket permanece en su instancia propietaria. El estado compartido de la aplicación o la mensajería, como Redis Pub/Sub, puede entregar eventos entre instancias, pero no transfiere sockets activos ni proporciona por sí mismo entrega duradera. Verifique el handshake utilizado por la versión HTTP negociada y la compatibilidad del proxy.

### WebRTC

**Definición:** APIs y protocolos para medios y datos en tiempo real entre endpoints compatibles, incluidos navegadores y servidores de medios.

**Cómo funciona:** NAT puede obstaculizar la accesibilidad directa, pero dos pares detrás de NAT aún pueden conectarse. ICE intercambia y prueba candidatos de host, reflexivos de servidor (obtenidos con STUN) y retransmitidos (TURN). La señalización de la aplicación transporta descripciones de sesión y candidatos. La ruta seleccionada depende de las comprobaciones de conectividad y la política. Los medios usan SRTP, habitualmente con establecimiento de claves DTLS-SRTP; los canales de datos usan SCTP sobre DTLS.

**En la práctica:** El uso del relay TURN contribuye al ancho de banda y al coste de infraestructura; la señalización, STUN y otros costes de servicio se mantienen incluso con una ruta de medios directa. El mapeo/filtrado NAT y el comportamiento del firewall influyen en la conectividad, por lo que la etiqueta «NAT simétrico» por sí sola no es una prueba universal de que el relay sea inevitable. Presupueste una alternativa TURN y pruebe redes reales. Un SFU es un diseño multiparte común que intercambia ancho de banda/cómputo del servidor por una menor carga de subida del cliente en comparación con una malla completa entre pares.

### gRPC

**Definición:** Un framework RPC cuyo transporte nativo estándar utiliza HTTP/2, comúnmente con esquemas de servicios y mensajes de Protocol Buffers.

**Cómo funciona:** Las definiciones de Protocol Buffers pueden generar código de cliente/servidor y admitir RPC unarios, server-streaming, client-streaming y bidirectional-streaming. La codificación binaria puede ser compacta, pero el tamaño y la velocidad en comparación con JSON dependen de los datos, la implementación y la compresión; no son garantías del protocolo.

**En la práctica:** gRPC nativo funciona bien para muchas APIs de servicios. Las APIs de navegador no exponen todo lo que requiere gRPC nativo, por lo que los clientes de navegador utilizan habitualmente gRPC-Web con un servidor compatible o proxy de traducción; los modos de streaming disponibles dependen de esa implementación. Utilice herramientas conscientes del esquema para la inspección y depuración.

Un canal gRPC puede utilizar **cero o más conexiones HTTP/2**, y muchas RPC pueden compartir una conexión de larga duración. El balanceo L4 selecciona un backend por conexión, por lo que un pequeño conjunto de conexiones puede concentrar el tráfico RPC; no garantiza la distribución por RPC. Considere una política adecuada del lado del cliente o un proxy L7 compatible con gRPC (que puede formar parte de una service mesh). Los flujos establecidos permanecen con su backend seleccionado. Para la evolución del esquema, reserve los números/nombres de campos eliminados de Protocol Buffers y nunca reutilice sus números.

> 📎 Para el manejo de gRPC en Istio, consulte [Istio gRPC Advanced](../service-mesh/istio/advanced/05-grpc.md).

### MQTT

**Definición:** Un protocolo ligero de mensajería publish-subscribe.

**Cómo funciona:** Los clientes se conectan a un broker y publican/se suscriben a topics. Un encabezado fijo puede tener tan solo 2 bytes, pero los paquetes reales también pueden necesitar encabezados variables, propiedades y cargas útiles. QoS 0/1/2 proporcionan entrega del protocolo como máximo una vez, al menos una vez y exactamente una vez **en el tramo relevante entre emisor y receptor**. La entrega de publicador a broker y de broker a suscriptor son independientes. Un Will configurado puede publicarse bajo condiciones especificadas de desconexión; MQTT 5 Will Delay y el comportamiento de reconexión afectan cuándo aparece.

**En la práctica:** Elija QoS según la tolerancia a pérdidas/duplicados y el coste. La entrega QoS 2 exitosa normalmente intercambia PUBLISH, PUBREC, PUBREL y PUBCOMP; no hace que los efectos secundarios de la base de datos de una aplicación ni todo un flujo de trabajo de negocio ocurran exactamente una vez. QoS 1 más deduplicación de la aplicación es una posible compensación. Planifique la disponibilidad del broker, el estado durable de sesión/mensajes y la recuperación para el producto elegido. Utilice TLS y un esquema adecuado de autenticación/autorización de dispositivos; los certificados de cliente son una opción, con requisitos de aprovisionamiento y rotación.


**Referencias principales**: [DoH](https://www.rfc-editor.org/rfc/rfc8484.html), [DNS serve-stale](https://www.rfc-editor.org/rfc/rfc8767.html), [OpenSSH](https://man.openbsd.org/ssh), [Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html), [DMARC](https://www.rfc-editor.org/rfc/rfc7489.html), [HTTP/3](https://www.rfc-editor.org/rfc/rfc9114.html), [ICE](https://www.rfc-editor.org/rfc/rfc8445.html), [gRPC performance](https://grpc.io/docs/guides/performance/), [MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
---

**Siguiente:** [Parte 4: El recorrido de una solicitud y la nube](./06-network-fundamentals-part4.md)
