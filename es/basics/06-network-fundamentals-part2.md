# Fundamentos de redes, parte 2: La capa de transporte y TLS

> **Última actualización**: 11 de septiembre de 2026

::: tip Esta es una serie de cinco partes
[Parte 1: El modelo por capas, las capas de enlace y de enrutamiento](./06-network-fundamentals-part1.md) ·
**Parte 2: La capa de transporte y TLS** *(este documento)* ·
[Parte 3: Protocolos de aplicación](./06-network-fundamentals-part3.md) ·
[Parte 4: El recorrido de una solicitud y la nube](./06-network-fundamentals-part4.md) ·
[Parte 5: Dispositivos de red, LAN y WAN](./06-network-fundamentals-part5.md)
:::

La parte 1 entregó paquetes al host de destino. En esta parte se comparan los flujos fiables (TCP y QUIC) con los datagramas UDP y, luego, se explica cómo TLS protege la comunicación. UDP por sí solo no proporciona fiabilidad ni TLS; las aplicaciones eligen un protocolo de seguridad adecuado, como DTLS, o utilizan un transporte como QUIC, que integra TLS 1.3.

Una imagen resume la idea central de esta parte:

![Conexión nueva típica: TCP más un protocolo de enlace TLS 1.3 completo requieren unos 2 RTT antes de una solicitud, mientras que QUIC los combina en aproximadamente 1 RTT. La reanudación elegible puede enviar datos anticipados de 0-RTT antes de que se complete el protocolo de enlace.](../.gitbook/assets/en-basics-06-network-fundamentals-part2-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part2-0.html)

---

## 3. Capa de transporte: entrega de extremo a extremo

A partir de aquí, tu interlocutor ya no es una «red», sino un «proceso». Por eso aparecen los números de puerto.

### TCP

**Definición:** Protocolo de transporte orientado a la conexión que proporciona un flujo de bytes fiable y ordenado.

**Cómo funciona:** Un protocolo de enlace de tres vías (SYN → SYN+ACK → ACK) establece la conexión. Los números de secuencia preservan el orden, los ACK y las retransmisiones recuperan las pérdidas, las ventanas deslizantes controlan el flujo y el control de congestión se adapta a la carga de la red. Para la aplicación, TCP presenta una abstracción sencilla: un flujo ininterrumpido de bytes.

**En la práctica:** La entrega ordenada provoca **bloqueo de cabecera de línea (HOL)**: si falta un segmento TCP, se impide la entrega de los bytes que están más allá de esa interrupción. Con HTTP/2, esto puede retrasar varios flujos que comparten esa conexión; los datos que ya se entregaron y el trabajo independiente de la aplicación pueden seguir avanzando. QUIC elimina esta dependencia concreta del orden de transporte entre flujos.

En una conexión nueva típica sin optimizaciones, el establecimiento de TCP cuesta aproximadamente 1 RTT, seguido de un protocolo de enlace TLS 1.3 completo de 1 RTT (normalmente 2 RTT con TLS 1.2). La reutilización de conexiones, la reanudación, los datos anticipados y TCP Fast Open modifican los tiempos; los reintentos pueden añadir demoras. Evalúa la agrupación de conexiones teniendo en cuenta la carga de trabajo real.

**Breve historia del control de congestión:** El control de congestión influye en el rendimiento, junto con el ancho de banda, la latencia, los búferes y el comportamiento de la aplicación. **Reno**, el algoritmo clásico, reduce su ventana de congestión cuando hay pérdidas. **CUBIC**, una opción predeterminada habitual en Linux, usa una función cúbica de crecimiento de ventana para mejorar la escalabilidad en rutas de gran ancho de banda. **BBR** modela el ancho de banda del cuello de botella y el RTT de propagación para orientar el envío; el uso de pérdidas y ECN también depende de la implementación y la versión. Ningún algoritmo garantiza un mayor rendimiento en todas las rutas de larga distancia o móviles. `sysctl net.ipv4.tcp_congestion_control` solo **lee** el valor predeterminado configurado; cambiar ese valor afecta a las conexiones nuevas y requiere una configuración y medición aparte.

**TIME_WAIT y agotamiento de puertos:** En un cierre ordenado normal, el extremo que inicia el cierre suele entrar en TIME_WAIT; si ambos extremos cierran simultáneamente, los dos pueden quedar en ese estado. Una alta rotación de conexiones puede contribuir al agotamiento de las tuplas de conexión disponibles, los puertos efímeros o las asignaciones NAT, según la implementación y el patrón de destinos. Una entrada TIME_WAIT no reserva ese puerto universalmente para todos los extremos remotos. Diagnostica el límite real y considera reutilizar las conexiones antes de cambiar la configuración del kernel; TIME_WAIT también protege contra paquetes demorados de una conexión antigua.

### UDP

**Definición:** Protocolo de transporte mínimo que envía datagramas sin establecer una conexión.

**Cómo funciona:** El encabezado de 8 bytes solo contiene el puerto de origen, el puerto de destino, la longitud y la suma de comprobación. No hay protocolo de enlace, retransmisiones, ordenamiento ni control de congestión. En esencia, es «IP con números de puerto».

**En la práctica:** Las aplicaciones en tiempo real pueden preferir la entrega oportuna a retransmitir datos obsoletos, y DNS suele usar UDP para intercambios pequeños. Las aplicaciones deben implementar por su cuenta cualquier fiabilidad necesaria y un control de congestión adecuado, o usar un protocolo como QUIC que los proporcione.

La salvedad: al ser sin estado, UDP es fácil de explotar para ataques de suplantación y amplificación. Al exponer servicios UDP externamente, planifica límites para el tamaño de las respuestas y controles de la tasa de solicitudes.

### QUIC

**Definición:** Protocolo de transporte seguro y multiplexado que se implementa sobre UDP.

**Cómo funciona:** QUIC rediseña desde cero, sobre UDP, todo lo que antes hacía TCP+TLS. Tiene cuatro propiedades clave:

1. **Entrega independiente por flujo**: cada flujo tiene su propio orden de bytes, por lo que una pérdida en un flujo no necesariamente impide la entrega de los datos disponibles de otro. La recuperación de paquetes y el control de congestión siguen operando en toda la conexión o ruta; un flujo puede bloquearse por sus propios bytes faltantes, y las dependencias de la aplicación o de QPACK en HTTP/3 también pueden causar bloqueos.
2. **Cifrado integrado**: QUIC integra el protocolo de enlace TLS 1.3 y usa su propia protección de paquetes, en lugar de registros TLS. Un protocolo de enlace completo normal tarda aproximadamente 1 RTT. Una reanudación elegible y aceptada puede incluir **datos anticipados de 0-RTT**, pero el protocolo de enlace se completa más tarde; Retry u otros intercambios adicionales del protocolo de enlace pueden aumentar la latencia.
3. **Identificadores de conexión**: permiten mantener la continuidad de la conexión cuando cambia la dirección, con validación de ruta y compatibilidad de los extremos. Las restricciones de migración o la falta de rutas disponibles aún pueden interrumpir la transición de Wi-Fi a la red celular; la continuidad no está garantizada.
4. **Flexibilidad de implementación**: QUIC suele implementarse en el espacio de usuario, lo que permite distribuir cambios de transporte junto con una aplicación o biblioteca. Implementarlo en el espacio de usuario no es un requisito del protocolo.

**En la práctica:** HTTP/3 suele usar UDP 443. Si esa ruta está bloqueada, un cliente HTTP puede probar HTTP/2 o HTTP/1.1 sobre TCP, si el servidor los admite; QUIC no se convierte en TCP. Antes de atribuir un resultado de rendimiento a QUIC, comprueba la accesibilidad, el protocolo negociado y el comportamiento de la implementación o de las descargas de trabajo. El costo de CPU depende de la implementación y de la carga de trabajo.

Una salvedad de seguridad: **los datos de 0-RTT se pueden reproducir.** La reproducción de un intercambio de datos anticipados puede hacer que una aplicación procese una solicitud más de una vez; la deduplicación de paquetes de transporte por sí sola no proporciona protección contra la reproducción en la capa de aplicación. Permite únicamente las operaciones que la aplicación haya evaluado explícitamente como seguras frente a la reproducción. Que una operación se llame GET o se afirme que es idempotente no basta. Los servidores pueden rechazar los datos anticipados; los servidores HTTP pueden usar `425 Too Early` para que el cliente reintente después del protocolo de enlace. Configura esta política en el cliente, la CDN y el origen.

---

## 4. Seguridad: TLS

### TLS

**Definición:** Protocolo que proporciona confidencialidad, integridad y autenticación para los datos en tránsito.

**Cómo funciona:** TLS negocia los parámetros criptográficos y establece claves durante un protocolo de enlace. Los protocolos de enlace basados en certificados autentican el servidor mediante un certificado y una prueba de posesión de la clave; los protocolos de enlace basados en PSK pueden autenticar mediante una clave establecida previamente o aprovisionada externamente. Los registros TLS protegen los datos de la aplicación. TLS 1.3 usa cifrado autenticado (AEAD) para proporcionar confidencialidad e integridad.

Un protocolo de enlace TLS 1.3 completo normal tarda aproximadamente 1 RTT; la reanudación permite datos anticipados opcionales bajo condiciones adicionales. TLS 1.3 eliminó el intercambio de claves RSA estático y las suites de cifrado heredadas, pero sigue admitiendo firmas RSA en certificados. El intercambio de claves efímero (EC)DHE proporciona confidencialidad directa, incluso cuando se combina con una PSK. **El intercambio de claves solo con PSK y los datos de 0-RTT no ofrecen la misma garantía de confidencialidad directa.**

**En la práctica:** Hay tres problemas que se repiten una y otra vez.

- **Vencimiento del certificado**: automatiza la renovación y supervisa por separado el vencimiento y la implementación correcta del certificado.
- **Exposición de SNI**: TLS 1.3 por sí solo deja visible el SNI del ClientHello. ECH (Encrypted Client Hello, RFC 9849) puede proteger el ClientHello interno si ambos extremos lo admiten y está configurado en ellos. Las claves de los paquetes Initial de QUIC se pueden derivar públicamente, así que el cifrado de Initial por sí solo no oculta SNI. ECH tampoco oculta la IP de destino ni todos los metadatos del tráfico.
- **Diseño del punto de terminación**: documenta cada salto: del cliente al balanceador de carga, del balanceador de carga a la aplicación y cualquier conexión entre servicios. La terminación de TLS no cifra automáticamente el siguiente salto. Usa TLS allí cuando sea necesario; usa mTLS cuando ambos pares deban autenticarse con certificados. Una malla de servicios puede automatizarlo, pero no es necesaria en todos los diseños.

**Cadenas de certificados y grapado OCSP:** La validación X.509 habitual construye una ruta desde el certificado hoja, pasando por los certificados intermedios necesarios, hasta un ancla de confianza configurada. El servidor debe enviar los certificados intermedios necesarios; normalmente, el cliente ya confía en el certificado raíz. La falta de certificados intermedios puede causar errores que dependen del cliente, aunque no todas las cadenas válidas contienen un certificado intermedio. La gestión de revocaciones depende del emisor y del cliente. Cuando se admite OCSP, el grapado permite que el servidor adjunte una respuesta de estado firmada y puede reducir las consultas directas de los clientes. No es universal: Let’s Encrypt puso fin al servicio OCSP en agosto de 2025 y usa CRL. Adapta la configuración de certificados y revocaciones a la CA y los clientes reales.

> 📎 Para saber cómo lo automatiza Istio, consulta [mTLS de Istio](../service-mesh/istio/security/01-mtls.md).


**Referencias principales**: [TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446.html), [transporte QUIC](https://www.rfc-editor.org/rfc/rfc9000.html), [QUIC/TLS](https://www.rfc-editor.org/rfc/rfc9001.html), [datos anticipados HTTP](https://www.rfc-editor.org/rfc/rfc8470.html), [ECH](https://www.rfc-editor.org/rfc/rfc9849.html), [configuración de TCP en Linux](https://docs.kernel.org/networking/ip-sysctl.html), [retiro de OCSP por parte de Let’s Encrypt](https://letsencrypt.org/2025/08/06/ocsp-service-has-reached-end-of-life/).
---

**Siguiente:** [Parte 3: Protocolos de aplicación](./06-network-fundamentals-part3.md)
