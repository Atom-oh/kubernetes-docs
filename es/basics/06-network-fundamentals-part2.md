# Fundamentos de redes, parte 2: la capa de transporte y TLS

> **Última actualización**: September 11, 2026

::: tip Esta es una serie de cuatro partes
[Parte 1: El modelo de capas, las capas de enlace y de enrutamiento](./06-network-fundamentals-part1.md) ·
**Parte 2: La capa de transporte y TLS** *(este documento)* ·
[Parte 3: Protocolos de aplicación](./06-network-fundamentals-part3.md) ·
[Parte 4: El recorrido de una solicitud y la nube](./06-network-fundamentals-part4.md)
:::

En la parte 1, los paquetes llegaron al host de destino. En esta parte se comparan los flujos fiables (TCP y QUIC) con los datagramas UDP y, a continuación, se explica cómo TLS protege las comunicaciones. UDP no proporciona fiabilidad ni TLS por sí mismo; las aplicaciones eligen un protocolo de seguridad adecuado, como DTLS, o usan un transporte como QUIC, que integra TLS 1.3.

Una imagen resume la idea central de esta parte:

![Conexión nueva típica: TCP más un handshake completo de TLS 1.3 tardan aproximadamente 2 RTT antes de una solicitud, mientras que QUIC combina ambos en aproximadamente 1 RTT. La reanudación apta puede enviar datos tempranos 0-RTT antes de que se complete el handshake.](../.gitbook/assets/en-basics-06-network-fundamentals-part2-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part2-0.html)

---

## 3. Capa de transporte: entrega de extremo a extremo

A partir de aquí, tu interlocutor no es una «red», sino un «proceso». Por eso aparecen los números de puerto.

### TCP

**Definición:** Un protocolo de transporte orientado a la conexión que proporciona un flujo de bytes fiable y ordenado.

**Cómo funciona:** Un handshake de 3 vías (SYN → SYN+ACK → ACK) establece la conexión. Los números de secuencia conservan el orden; los ACK y las retransmisiones recuperan los datos perdidos; las ventanas deslizantes controlan el flujo, y el control de congestión se adapta a la carga de la red. Para la aplicación, TCP ofrece una abstracción sencilla: un flujo de bytes sin interrupciones.

**En la práctica:** La entrega ordenada provoca **bloqueo de cabecera de línea (HOL)**: un segmento TCP que falta impide entregar los bytes posteriores a la brecha. Con HTTP/2, esto puede retrasar varios flujos que comparten esa conexión; los datos ya entregados y el trabajo independiente de la aplicación aún pueden avanzar. QUIC elimina esta dependencia específica del orden de transporte entre flujos.

En una conexión nueva típica, sin optimizaciones, establecer TCP cuesta aproximadamente 1 RTT, seguido de un handshake completo de TLS 1.3 de 1 RTT (normalmente 2 RTT con TLS 1.2). La reutilización de conexiones, la reanudación, los datos tempranos y TCP Fast Open modifican los tiempos; los reintentos pueden añadir demora. Evalúa el agrupamiento de conexiones en función de la carga de trabajo real.

**Breve evolución del control de congestión:** El control de congestión influye en el caudal junto con el ancho de banda, la latencia, los búferes y el comportamiento de la aplicación. **Reno**, el algoritmo clásico, reduce su ventana de congestión cuando se pierden datos. **CUBIC**, un valor predeterminado común en Linux, utiliza una función cúbica de crecimiento de la ventana para mejorar la escalabilidad en rutas de gran ancho de banda. **BBR** modela el ancho de banda del cuello de botella y el RTT de propagación para guiar el envío; el uso de pérdidas y ECN también depende de la implementación y la versión. Ningún algoritmo garantiza un caudal mayor en todas las rutas de larga distancia o móviles. `sysctl net.ipv4.tcp_congestion_control` solo **lee** el valor predeterminado configurado; cambiarlo afecta a las conexiones nuevas y requiere una configuración y mediciones independientes.

**TIME_WAIT y agotamiento de puertos:** En un cierre normal y ordenado, el lado que inicia el cierre suele entrar en TIME_WAIT; si ambos lados cierran simultáneamente, los dos pueden llegar a ese estado. Una alta rotación de conexiones puede contribuir al agotamiento de las tuplas de conexión disponibles, los puertos efímeros o las asignaciones de NAT, según la implementación y el patrón de destinos. Una entrada TIME_WAIT no reserva universalmente ese puerto frente a todos los endpoints remotos. Diagnostica el límite real y considera reutilizar las conexiones antes de cambiar la configuración del kernel; TIME_WAIT también protege frente a paquetes retrasados de una conexión anterior.

### UDP

**Definición:** Un protocolo de transporte mínimo que envía datagramas sin establecer una conexión.

**Cómo funciona:** El encabezado de 8 bytes contiene solo el puerto de origen, el puerto de destino, la longitud y la suma de comprobación. No hay handshake, retransmisiones, ordenamiento ni control de congestión. En esencia, es «IP con números de puerto».

**En la práctica:** Las aplicaciones en tiempo real pueden preferir la entrega oportuna a retransmitir datos obsoletos, y DNS suele utilizar UDP para intercambios pequeños. Las aplicaciones deben implementar por sí mismas cualquier fiabilidad necesaria y un control de congestión adecuado, o usar un protocolo como QUIC que los proporcione.

La salvedad: al ser un protocolo sin estado, UDP puede facilitar los ataques de suplantación y amplificación. Cuando expongas servicios UDP externamente, planifica límites al tamaño de las respuestas y controles de la tasa de solicitudes.

### QUIC

**Definición:** Un protocolo de transporte seguro y multiplexado implementado sobre UDP.

**Cómo funciona:** QUIC rediseña desde cero sobre UDP todo lo que antes hacían TCP+TLS. Tiene cuatro propiedades clave:

1. **Entrega independiente de los flujos**: cada flujo tiene su propio orden de bytes, por lo que la pérdida en un flujo no necesariamente impide entregar los datos disponibles de otro. La recuperación de paquetes y el control de congestión siguen operando en toda la conexión/ruta; un flujo puede bloquearse por sus propios bytes faltantes, y las dependencias de la aplicación o de QPACK en HTTP/3 también pueden causar bloqueos.
2. **Cifrado integrado**: QUIC integra el handshake de TLS 1.3 y utiliza su propia protección de paquetes, en lugar de registros TLS. Un handshake completo normal tarda aproximadamente 1 RTT. La reanudación apta y aceptada puede incluir **datos tempranos 0-RTT**, pero el handshake se completa después; Retry u otros intercambios adicionales del handshake pueden aumentar la latencia.
3. **Identificadores de conexión**: permiten mantener la continuidad de la conexión cuando cambia la dirección, con validación de ruta y compatibilidad del endpoint. Las restricciones de migración o la falta de rutas disponibles aún pueden interrumpir la transición de Wi-Fi a la red celular; la continuidad no está garantizada.
4. **Flexibilidad de implementación**: QUIC suele implementarse en espacio de usuario, lo que permite distribuir cambios de transporte junto con una aplicación o biblioteca. La implementación en espacio de usuario no es un requisito del protocolo.

**En la práctica:** HTTP/3 suele usar UDP 443. Si esa ruta está bloqueada, un cliente HTTP puede probar HTTP/2 o HTTP/1.1 sobre TCP, si el servidor los admite; QUIC no se convierte en TCP. Comprueba la conectividad, el protocolo negociado y el comportamiento de la implementación y la descarga de procesamiento antes de atribuir un resultado de rendimiento a QUIC. El costo de CPU depende de la implementación y de la carga de trabajo.

Una salvedad de seguridad: **los datos 0-RTT se pueden reproducir**. Reproducir un intercambio de datos tempranos puede hacer que una aplicación procese una solicitud más de una vez; la deduplicación de paquetes de transporte por sí sola no proporciona protección frente a la reproducción a nivel de aplicación. Permite solo las operaciones que la aplicación haya evaluado explícitamente como seguras frente a la reproducción. Que el método se llame GET o que se afirme que una operación es idempotente no basta. Los servidores pueden rechazar los datos tempranos; los servidores HTTP pueden usar `425 Too Early` para que el cliente vuelva a intentarlo después del handshake. Configura esta política en el cliente, la CDN y el origen.

---

## 4. Seguridad: TLS

### TLS

**Definición:** El protocolo que proporciona confidencialidad, integridad y autenticación para los datos en tránsito.

**Cómo funciona:** TLS negocia los parámetros criptográficos y establece claves durante un handshake. Los handshakes basados en certificados autentican el servidor mediante un certificado y una prueba de posesión de la clave; los handshakes basados en PSK pueden autenticar usando una clave establecida previamente o aprovisionada externamente. Los registros TLS protegen los datos de la aplicación. TLS 1.3 usa cifrado autenticado (AEAD) para proporcionar confidencialidad e integridad.

Un handshake completo normal de TLS 1.3 tarda aproximadamente 1 RTT; la reanudación permite, opcionalmente, enviar datos tempranos bajo condiciones adicionales. TLS 1.3 eliminó el intercambio de claves RSA estático y las suites de cifrado heredadas, pero sigue admitiendo las firmas RSA en certificados. El intercambio de claves efímero (EC)DHE proporciona secreto hacia adelante, incluso cuando se combina con una PSK. **El intercambio de claves solo con PSK y los datos 0-RTT no proporcionan la misma garantía de secreto hacia adelante.**

**En la práctica:** Hay tres problemas recurrentes.

- **Vencimiento de certificados**: automatiza la renovación y supervisa por separado el vencimiento y la implementación correcta de los certificados.
- **Exposición de SNI**: TLS 1.3 por sí solo deja visible el SNI del ClientHello. ECH (Encrypted Client Hello, RFC 9849) puede proteger el ClientHello interno cuando ambos endpoints lo admiten y configuran. Las claves de los paquetes Initial de QUIC se pueden derivar públicamente, por lo que el cifrado de Initial por sí solo no oculta el SNI. ECH tampoco oculta la IP de destino ni todos los metadatos del tráfico.
- **Diseño del punto de terminación**: documenta cada salto: del cliente al balanceador de carga, del balanceador de carga a la aplicación y cualquier conexión entre servicios. La terminación de TLS no cifra automáticamente el siguiente salto. Usa TLS en ese salto cuando sea necesario; usa mTLS cuando ambos pares deban autenticarse con certificados. Una malla de servicios puede automatizarlo, pero no es necesaria para todos los diseños.

**Cadenas de certificados y grapado OCSP:** La validación típica de X.509 construye una ruta desde el certificado final, pasando por los intermediarios necesarios, hasta un ancla de confianza configurada. El servidor debe enviar los certificados intermedios necesarios; normalmente, el cliente ya confía en el certificado raíz. La falta de certificados intermedios puede provocar errores que dependen del cliente, aunque no todas las cadenas válidas contienen un intermediario. La gestión de revocaciones depende de la entidad emisora y del cliente. Cuando se admite OCSP, el grapado permite que el servidor adjunte una respuesta de estado firmada y puede reducir las consultas directas del cliente. No es universal: Let’s Encrypt finalizó el servicio OCSP en agosto de 2025 y utiliza CRL. Ajusta la configuración de certificados y revocaciones a la CA y los clientes reales.

> 📎 Para saber cómo Istio automatiza esto, consulta [mTLS de Istio](../service-mesh/istio/security/01-mtls.md).


**Referencias principales**: [TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446.html), [transporte QUIC](https://www.rfc-editor.org/rfc/rfc9000.html), [QUIC/TLS](https://www.rfc-editor.org/rfc/rfc9001.html), [datos tempranos HTTP](https://www.rfc-editor.org/rfc/rfc8470.html), [ECH](https://www.rfc-editor.org/rfc/rfc9849.html), [configuración de TCP en Linux](https://docs.kernel.org/networking/ip-sysctl.html), [fin del servicio OCSP de Let’s Encrypt](https://letsencrypt.org/2025/08/06/ocsp-service-has-reached-end-of-life/).
---

**Siguiente:** [Parte 3: Protocolos de aplicación](./06-network-fundamentals-part3.md)
