# Fundamentos de redes, parte 3: diez protocolos de aplicación

> **Última actualización**: 14 de septiembre de 2026

::: tip Esta es una serie de cuatro partes
[Parte 1: El modelo de capas, las capas de enlace y de enrutamiento](./06-network-fundamentals-part1.md) ·
[Parte 2: La capa de transporte y TLS](./06-network-fundamentals-part2.md) ·
**Parte 3: Protocolos de aplicación** *(este documento)* ·
[Parte 4: El recorrido de una solicitud y la nube](./06-network-fundamentals-part4.md)
:::

Los protocolos de transporte proporcionan flujos o datagramas; los protocolos de aplicación los convierten en servicios. Esta parte abarca la resolución de nombres (DNS y DoH), el arranque (DHCP), el acceso operativo (SSH), el correo (SMTP) y HTTP/3, WebSocket, WebRTC, gRPC y MQTT.

---

## 5. Capa de aplicación: servicios reales

### DNS

**Definición:** El sistema de directorio distribuido que resuelve nombres de dominio en direcciones IP y otros registros.

**Cómo funciona:** DNS utiliza delegación jerárquica. Cuando no encuentra una respuesta en la caché, un resolvedor recursivo sigue las referencias desde la raíz hasta el TLD y los servidores de nombres autoritativos, o reenvía la consulta a otro resolvedor. Las respuestas en caché pueden evitar parte o todo ese trabajo. Los registros A/AAAA contienen direcciones, los registros CNAME son alias, los registros MX identifican servidores de correo y los registros TXT contienen texto que usan varios protocolos.

**En la práctica:** DNS está distribuido, pero un resolvedor, un proveedor o una configuración pueden convertirse en una dependencia compartida. Para la conmutación por error de DNS, tenga en cuenta la detección de fallos, las actualizaciones de registros, el TTL de las respuestas que ya están en caché, el almacenamiento en caché de la aplicación y las conexiones existentes. Reducir el TTL ahora no acorta el TTL de una respuesta antigua que ya está en caché. Algunos resolvedores también sirven respuestas antiguas en caché en condiciones de fallo definidas (RFC 8767). Mida cada etapa; un TTL corto, por sí solo, no garantiza el tiempo de conmutación por error. Los balanceadores de carga y anycast pueden complementar DNS, con sus propios límites de detección del estado y convergencia.

**Tipos de registros comunes de un vistazo:**

| Tipo | Propósito | Nota de campo |
|---|---|---|
| A / AAAA | Dominio → IPv4 / IPv6 | Lo básico |
| CNAME | Alias → nombre canónico | No puede coexistir con SOA/NS en el ápice de la zona; ALIAS/ANAME específicos del proveedor o Alias de Route 53 pueden ofrecer un mapeo del ápice de la zona a destinos compatibles |
| MX | Servidor que recibe correo | Gana el número de prioridad más bajo |
| TXT | Cadenas arbitrarias | SPF/DKIM/DMARC, verificación de propiedad del dominio |
| NS | Servidores de nombres delegados | Delegación de subzonas |
| SRV | Ubicación del servicio (host+puerto) | Descubrimiento para algunos protocolos |
| CAA | Restringir los emisores de certificados autorizados | La CA debe aplicar esta restricción; por sí sola no evita todas las emisiones indebidas |

**DNSSEC y DoH resuelven problemas distintos.** DNSSEC autentica los datos DNS firmados y su integridad mediante una cadena de confianza validada; no cifra las consultas. DoH utiliza HTTPS para autenticar el resolvedor elegido y proteger la confidencialidad e integridad en el tramo entre cliente y resolvedor. No demuestra que un resolvedor malicioso o equivocado haya devuelto datos autoritativos. Se pueden usar juntos.

![Muestra la resolución recursiva de DNS: la consulta del cliente stub de DNS pasa por el resolvedor recursivo hasta los servidores de nombres raíz, TLD y autoritativos, y la respuesta se almacena en caché durante su TTL.](../.gitbook/assets/en-basics-06-network-fundamentals-part3-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part3-0.html)

### DoH

**Definición:** Consultas DNS encapsuladas y transportadas mediante HTTPS.

**Cómo funciona:** El DNS tradicional suele usar el puerto 53 sobre UDP **y TCP** en texto sin cifrar. DoH transporta mensajes DNS mediante HTTPS, protegiéndolos de la inspección pasiva y la modificación en ese tramo. Los endpoints del resolvedor y los metadatos del tráfico aún pueden identificar el uso de DoH; el resolvedor elegido puede ver las consultas.

**En la práctica:** Un resolvedor público de DoH seleccionado de forma independiente puede eludir las políticas de filtrado y registro del resolvedor de la organización y no resolver nombres privados. El uso de DoH no desactiva las políticas por sí mismo: un resolvedor DoH administrado puede aplicar el registro de actividad y el filtrado, y las políticas del navegador o del sistema operativo pueden seleccionar resolvedores aprobados. Pruebe el DNS dividido y las políticas de los endpoints en lugar de asumir que siempre es necesario desactivar el cifrado.

### DHCP

**Definición:** El protocolo que asigna automáticamente una dirección IP y la configuración de red a los hosts.

**Cómo funciona:** Un intercambio inicial común de **DHCPv4** es DORA: Discover → Offer → Request → Acknowledge. Una difusión local o un relay DHCP localiza un servidor. La concesión puede incluir la dirección IPv4, la máscara de subred, la puerta de enlace y la configuración DNS. La renovación puede utilizar un intercambio más breve. DHCPv6 usa mensajes distintos; la información de la puerta de enlace predeterminada IPv6 suele provenir de los anuncios de los enrutadores, y SLAAC es otro mecanismo de configuración de direcciones.

**En la práctica:** En la nube, DHCP suele quedar abstraído, pero vuelve a aparecer en el conjunto de opciones DHCP de la VPC, donde se configuran los servidores DNS y los nombres de dominio. Si falla la resolución de nombres en una configuración híbrida que utiliza DNS local, este es el ajuste que debe revisar.

### SSH

**Definición:** El protocolo que proporciona acceso remoto cifrado al shell y túneles.

**Cómo funciona:** El servidor se autentica con su clave de host, un intercambio de claves deriva las claves de sesión y, después, el usuario se autentica (con una clave pública o una contraseña). Todo el tráfico posterior se cifra. Además de los shells remotos, SSH admite el reenvío de puertos, SFTP y el reenvío del agente.

**En la práctica:** Restrinja el reenvío según la política de acceso y valide las claves de host del servidor. Un host comprometido con acceso a un socket de agente reenviado puede solicitar firmas o autenticación al agente; normalmente, el reenvío no copia allí el material de la clave privada. Si no necesita el reenvío del agente, es preferible usar un host bastión (`ProxyJump`). Las claves sin más no tienen una caducidad intrínseca, pero OpenSSH admite períodos de validez de certificados y restricciones de caducidad en `authorized_keys`. Retire el acceso de los usuarios que se hayan marchado y rote o revoque las credenciales.

AWS Systems Manager Session Manager puede proporcionar acceso al shell sin puertos SSH entrantes ni distribución de claves SSH, siempre que estén configurados el nodo administrado, los permisos de IAM y la conectividad con el servicio. CloudTrail registra la actividad de la API; el registro del contenido del shell en CloudWatch Logs/S3 requiere configuración. **El registro del contenido de la sesión no está disponible para las sesiones SSH ni de reenvío de puertos de Session Manager.** El acceso basado en IAM, por sí solo, no implica que se registre cada comando.

### SMTP

**Definición:** El protocolo que retransmite mensajes entre servidores de correo.

**Cómo funciona:** Los clientes envían correo a un servidor de envío, y los servidores SMTP retransmiten y reciben mensajes; habitualmente usan búsquedas MX para el enrutamiento. IMAP y POP3 permiten a los usuarios recuperar o acceder a mensajes ya almacenados en un buzón; no sustituyen la recepción del lado del servidor de SMTP.

**En la práctica:** La autenticación SMTP y TLS protegen el envío y el transporte, pero no demuestran por sí solos cuál es el dominio del remitente visible. Hay tres mecanismos complementarios de dominio que son importantes:

- **SPF**: autoriza los hosts de envío para la identidad MAIL FROM del sobre o la identidad HELO; esto no corresponde automáticamente al encabezado From visible.
- **DKIM**: verifica una firma sobre el contenido cubierto del mensaje mediante la clave DNS del dominio firmante; el dominio firmante puede diferir del dominio From visible.
- **DMARC**: exige que el dominio From visible esté alineado con una identidad SPF **o** DKIM que haya superado la validación, y publica la política solicitada de gestión e informes.

Cuando corresponda, configure SPF, DKIM y DMARC en conjunto, supervise los informes y tenga en cuenta el comportamiento del reenvío y las listas de correo. DMARC puede superar la validación con un solo mecanismo alineado. Estos controles no garantizan la entrega ni eliminan la suplantación del nombre visible o de dominios parecidos; los destinatarios también aplican sus propias políticas.

### HTTP/3

**Definición:** La tercera versión principal de HTTP, que se ejecuta sobre QUIC.

**Cómo funciona:** La semántica de HTTP es compartida entre versiones, pero HTTP/3 utiliza flujos QUIC y su propio encuadre y mapeo. Elimina la dependencia del orden entre flujos de TCP; las pérdidas dentro de un flujo, las dependencias de QPACK y el control de congestión compartido aún pueden retrasar el trabajo. Un protocolo de enlace completo típico tarda aproximadamente 1 RTT, y la migración admitida puede mantener una conexión ante un cambio de dirección. QPACK reemplaza a HPACK para permitir la entrega independiente de flujos.

**En la práctica:** Los clientes pueden descubrir HTTP/3 mediante `Alt-Svc`, conocimiento previo o registros DNS HTTPS que anuncien un protocolo compatible. `Alt-Svc` puede conocerse mediante una conexión TCP anterior; un cliente compatible con el registro HTTPS puede descubrir HTTP/3 antes de ese intercambio. Ninguno de los métodos garantiza la accesibilidad ni una reducción específica de la latencia.

La entrega independiente y los protocolos de enlace integrados pueden ayudar en rutas con pérdida o alta latencia. La latencia, el rendimiento y el costo de CPU reales dependen de la implementación, las descargas, la carga de trabajo y las condiciones de red. Mida el tráfico representativo de redes móviles y centros de datos en lugar de asumir que siempre habrá una mejora o una pérdida.

**Las tres generaciones, una al lado de la otra:**

| | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| Transporte | TCP | TCP | QUIC (UDP) |
| Solicitudes por conexión | Secuenciales o canalizadas con respuestas ordenadas | Multiplexadas | Multiplexadas |
| Bloqueo HOL | Respuestas ordenadas y entrega TCP | Orden de TCP entre flujos | Sin orden de TCP entre flujos; persisten otros bloqueos |
| Compresión de encabezados | Ninguna | HPACK | QPACK |
| Cifrado | Opcional (HTTPS) | TLS para HTTPS; también existe HTTP/2 en texto sin cifrar | TLS 1.3 integrado en QUIC |

La multiplexación cambia dónde surgen las dependencias de orden; HTTP/3 reduce una fuente de bloqueo sin eliminar todas las dependencias de planificación, control de flujo o aplicación.

#### Lectura de solicitudes y respuestas HTTP/1.1 {#http11-message-structure}

Las versiones de HTTP comparten métodos, códigos de estado y semántica de campos. HTTP/1.1 hace visibles esos conceptos como **línea inicial → líneas de campos de encabezado → línea en blanco → cuerpo opcional**. Un cuerpo puede contener texto o datos binarios; “HTTP/1.1 textual” describe su línea inicial y sus encabezados, no todas las cargas útiles.

Estos son **mensajes HTTP/1.1 ilustrativos, no una salida capturada ni una receta de comandos**. Para facilitar la lectura, la representación usa saltos de línea LF. En el cable, la línea inicial y cada línea de encabezado terminan en **CRLF (`\r\n`)**, y un CRLF adicional termina la sección de encabezados. Cada cuerpo a continuación tiene exactamente **5 bytes ASCII**, `hello`, **sin salto de línea final**; el salto de línea de la representación antes de la cerca de cierre no forma parte del cuerpo.

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

| Elemento | Cómo interpretarlo |
|---|---|
| Línea de solicitud | `POST` es el método, `/echo` es el destino de la solicitud (en este caso, una ruta) y `HTTP/1.1` es la versión. El campo `Host`, obligatorio, proporciona el nombre de host de destino y el puerto opcional (la autoridad). |
| Línea de estado | `HTTP/1.1` es la versión, `200` es el código de estado y `OK` una frase de motivo opcional. Use el código para interpretar el resultado. |
| Campos de encabezado | Las líneas `Name: value` llevan metadatos; los nombres de campo no distinguen mayúsculas de minúsculas. `Content-Type` describe el tipo de medio de la representación y, en este caso, su juego de caracteres. |
| Línea en blanco | Termina la sección de encabezados. No especifica dónde termina el cuerpo siguiente. |
| Cuerpo | Los bytes del contenido. En este caso, `Content-Length: 5` delimita cinco bytes, sin incluir la línea inicial, los encabezados ni el separador. Cuente los bytes, no los caracteres Unicode. |

**El significado y el encuadre responden preguntas distintas.** Un método expresa la acción solicitada: GET recupera una representación, HEAD solicita los metadatos que corresponderían a una respuesta, pero no devuelve su contenido; POST pide al destino que procese el contenido proporcionado. Las clases de estado resumen el resultado: 1xx informativo, 2xx éxito, 3xx redirección, 4xx error del cliente y 5xx error del servidor. `Content-Type` explica cómo interpretar el contenido; no lo delimita. Consulte [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) para conocer esta semántica compartida.

El encuadre de HTTP/1.1 determina cuántos bytes pertenecen a este mensaje en un flujo TCP reutilizable. Para un mensaje ordinario con cuerpo, un `Content-Length` válido sin `Transfer-Encoding` indica su longitud. Con `Transfer-Encoding: chunked`, el tamaño de los fragmentos y el fragmento de tamaño cero que marca el final, seguidos de los tráileres que haya y la línea en blanco final, delimitan el cuerpo. El emisor no debe enviar ambos campos. Algunas respuestas usan el cierre de la conexión como delimitador; los límites de los paquetes TCP nunca delimitan mensajes HTTP.

Las reglas de métodos y estados son prioritarias: las respuestas a HEAD y las respuestas con estado 1xx, 204 o 304 no tienen cuerpo del mensaje, aunque los metadatos permitidos describan una representación. Una respuesta satisfactoria a CONNECT inicia un túnel. Una solicitud sin longitud ni codificación de transferencia no tiene cuerpo. Estas distinciones evitan leer el siguiente mensaje como si fuera contenido ([RFC 9112 §§2–6](https://www.rfc-editor.org/rfc/rfc9112.html)).

**HTTP/2 y HTTP/3 conservan el significado, pero usan encuadre binario**, incluidas las tramas HEADERS y DATA, en lugar de estas líneas iniciales textuales y los límites CRLF. HTTP/2 usa TCP; HTTP/3 mapea los mensajes en flujos QUIC. Ninguno usa la codificación de transferencia fragmentada de HTTP/1.1. Una herramienta puede presentar los campos decodificados como texto legible sin mostrar su codificación real en la transmisión ([RFC 9113](https://www.rfc-editor.org/rfc/rfc9113.html), [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114.html)).

Con HTTPS, TLS protege los encabezados y cuerpos HTTP durante el tránsito; una captura pasiva sin secretos de sesión no revela este texto sin cifrar ([RFC 8446 §5](https://www.rfc-editor.org/rfc/rfc8446.html#section-5)). QUIC también protege los datos de aplicación de HTTP/3. Inspeccione los mensajes decodificados en un endpoint autorizado o en un punto de terminación TLS, e identifique qué tramo de la conexión se está observando.

> 📎 Continúe con el [laboratorio de mensajes HTTP en Linux](../networking/07-linux-network-diagnostics.md#http-message-lab) antes de aplicar las mismas distinciones a servicios de contenedores, Ingress de Kubernetes o balanceadores de carga de AWS.

### WebSocket

**Definición:** Un protocolo de aplicación para intercambiar mensajes en ambas direcciones a través de una sola conexión.

**Cómo funciona:** El protocolo de enlace de HTTP/1.1 usa `Upgrade` y una respuesta `101` satisfactoria. HTTP/2 y HTTP/3 usan Extended CONNECT en su lugar (RFC 8441 y 9220), cuando es compatible. Una vez establecida, cualquiera de los pares puede enviar mensajes WebSocket sin repetir sondeos HTTP.

**En la práctica:** Planifique las conexiones de larga duración: tráfico de latido dentro del tiempo de inactividad pertinente, drenaje ordenado durante la implementación y reintentos de conexión con espera y variación aleatoria (jitter). Cada socket permanece en la instancia que lo aloja. El estado compartido de la aplicación o la mensajería, como Redis Pub/Sub, puede entregar eventos entre instancias, pero no transfiere sockets activos ni proporciona entrega duradera por sí solo. Verifique el protocolo de enlace utilizado por la versión HTTP negociada y la compatibilidad del proxy.

### WebRTC

**Definición:** API y protocolos para medios y datos en tiempo real entre endpoints compatibles, incluidos navegadores y servidores de medios.

**Cómo funciona:** NAT puede dificultar las conexiones directas, pero dos pares detrás de NAT aún pueden conectarse. ICE intercambia y comprueba candidatos host, server-reflexive (detectados mediante STUN) y relayed (TURN). La señalización de la aplicación transporta las descripciones de sesión y los candidatos. La ruta seleccionada depende de las comprobaciones de conectividad y de la política. Los medios usan SRTP, habitualmente con establecimiento de claves DTLS-SRTP; los canales de datos usan SCTP sobre DTLS.

**En la práctica:** El uso de retransmisión TURN contribuye al costo del ancho de banda y la infraestructura; la señalización, STUN y otros servicios también tienen costos incluso cuando la ruta de medios es directa. El mapeo y filtrado de NAT, así como el comportamiento del firewall, influyen en la conectividad, por lo que la etiqueta «NAT simétrico» no demuestra universalmente, por sí sola, que la retransmisión sea inevitable. Prevea una alternativa TURN y pruebe redes reales. Un SFU es un diseño multiparte habitual que intercambia ancho de banda y cómputo del servidor por una menor carga de subida del cliente en comparación con una malla completa de pares.

### gRPC

**Definición:** Un marco de RPC cuyo transporte nativo estándar usa HTTP/2, habitualmente con esquemas de servicios y mensajes de Protocol Buffers.

**Cómo funciona:** Las definiciones de Protocol Buffers pueden generar código de cliente y servidor y admitir llamadas RPC unarias, de flujo del servidor, de flujo del cliente y de flujo bidireccional. La codificación binaria puede ser compacta, pero el tamaño y la velocidad frente a JSON dependen de los datos, la implementación y la compresión; no son garantías del protocolo.

**En la práctica:** gRPC nativo funciona bien para muchas API de servicios. Las API de los navegadores no exponen todo lo que requiere gRPC nativo, por lo que los clientes de navegador suelen usar gRPC-Web con un servidor compatible o un proxy de traducción; los modos de transmisión disponibles dependen de esa implementación. Use herramientas que reconozcan esquemas para la inspección y depuración.

Un canal gRPC puede usar **cero o más conexiones HTTP/2**, y muchas RPC pueden compartir una conexión de larga duración. El balanceo L4 selecciona un backend por conexión, por lo que un grupo pequeño de conexiones puede concentrar el tráfico RPC; no garantiza una distribución por RPC. Considere una política adecuada del lado del cliente o un proxy L7 compatible con gRPC (que puede formar parte de una malla de servicios). Los flujos establecidos siguen vinculados al backend que se les asignó. Para la evolución del esquema, reserve los números y nombres de campo de Protocol Buffers eliminados y nunca reutilice sus números.

> 📎 Para la gestión de gRPC en Istio, consulte [gRPC avanzado de Istio](../service-mesh/istio/advanced/05-grpc.md).

### MQTT

**Definición:** Un protocolo ligero de mensajería de publicación-suscripción.

**Cómo funciona:** Los clientes se conectan a un broker y publican o se suscriben a temas. Un encabezado fijo puede tener tan solo 2 bytes, pero los paquetes reales también pueden necesitar encabezados variables, propiedades y cargas útiles. QoS 0/1/2 ofrecen, respectivamente, entrega a nivel de protocolo como máximo una vez, al menos una vez y exactamente una vez **en el tramo pertinente entre emisor y receptor**. La entrega del publicador al broker y del broker al suscriptor son independientes. Un mensaje Will configurado puede publicarse en determinadas condiciones de desconexión; Will Delay de MQTT 5 y el comportamiento de reconexión afectan cuándo aparece.

**En la práctica:** Elija QoS según la tolerancia a pérdidas y duplicados, y el costo. Una entrega correcta de QoS 2 normalmente intercambia PUBLISH, PUBREC, PUBREL y PUBCOMP; no hace que los efectos secundarios de la base de datos de una aplicación ni un flujo de trabajo empresarial completo se ejecuten exactamente una vez. QoS 1 junto con la deduplicación de la aplicación es una posible alternativa. Planifique la disponibilidad del broker, el estado duradero de las sesiones y los mensajes, y la recuperación para el producto elegido. Use TLS y un esquema adecuado de autenticación y autorización de dispositivos; los certificados de cliente son una opción, con requisitos de aprovisionamiento y rotación.


**Referencias principales**: [DoH](https://www.rfc-editor.org/rfc/rfc8484.html), [DNS serve-stale](https://www.rfc-editor.org/rfc/rfc8767.html), [OpenSSH](https://man.openbsd.org/ssh), [Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html), [DMARC](https://www.rfc-editor.org/rfc/rfc7489.html), [HTTP/3](https://www.rfc-editor.org/rfc/rfc9114.html), [ICE](https://www.rfc-editor.org/rfc/rfc8445.html), [rendimiento de gRPC](https://grpc.io/docs/guides/performance/), [MQTT 5.0](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html).
---

**Siguiente:** [Parte 4: El recorrido de una solicitud y la nube](./06-network-fundamentals-part4.md)
