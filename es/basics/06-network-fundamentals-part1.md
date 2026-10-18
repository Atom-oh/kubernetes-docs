# Fundamentos de redes, parte 1: El modelo de capas, las capas de enlace y enrutamiento

> **Última actualización**: September 14, 2026

::: tip Esta es una serie de cuatro partes
**Parte 1: El modelo de capas, las capas de enlace y enrutamiento** *(este documento)* ·
[Parte 2: La capa de transporte y TLS](./06-network-fundamentals-part2.md) ·
[Parte 3: Protocolos de aplicación](./06-network-fundamentals-part3.md) ·
[Parte 4: El recorrido de una solicitud y la nube](./06-network-fundamentals-part4.md)
:::

Una solicitud del navegador depende de varios protocolos que trabajan en conjunto. La secuencia exacta depende de las cachés, la reutilización de conexiones, la versión de IP y la versión de HTTP, así que para solucionar problemas hay que examinar algo más que HTTP.

Esta serie recorre 25 protocolos y mecanismos de redes, **capa por capa, desde abajo hacia arriba**. La razón para empezar desde abajo es sencilla: cada capa superior se diseña con la premisa de que las capas inferiores ya funcionan. Si se lee de arriba hacia abajo, uno acaba preguntándose: «Pero ¿cómo funciona *esa* parte?».

Cada entrada sigue la misma estructura: **definición en una línea → cómo funciona → problemas que causa en la práctica**.

---

## 0. El mapa de capas en una página

| Capa | Función | Protocolos que se tratan aquí |
|---|---|---|
| Aplicación | Semántica real del servicio | HTTP/3, WebSocket, WebRTC, gRPC, DNS, DoH, DHCP, MQTT, SSH, SMTP |
| Seguridad | Cifrado y autenticación (se apoya en el transporte) | TLS |
| Transporte | Entrega de datos de extremo a extremo | TCP, UDP, QUIC |
| Internet / Enrutamiento | Selección de rutas entre redes | IPv4, IPv6, ICMP, BGP, OSPF, NAT |
| Enlace | Entrega dentro de un segmento físico | Ethernet, Wi-Fi, VLAN, PPP, ARP |

Algunas entradas no respetan los límites nítidos entre capas. TLS queda encajado entre el transporte y la aplicación; QUIC se ejecuta sobre UDP, pero realiza la función de una capa de transporte; y ARP conecta IP con la capa de enlace. NAT es más una función que un protocolo. Estas «excepciones» explican la mayoría de los problemas que se diagnostican en la práctica.

---

![Muestra la ruta de las capas de enlace y enrutamiento desde una laptop, a través de un switch L2 y un router doméstico, hasta el borde del ISP, el núcleo de Internet impulsado por BGP, un router de centro de datos con OSPF y, finalmente, el servidor, con el protocolo y la MTU de cada segmento.](../.gitbook/assets/en-basics-06-network-fundamentals-part1-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part1-0.html)

---

## 1. Capa de enlace: mover bits dentro de un segmento

A la capa de enlace le importa una sola cosa: **cómo entregar bits al dispositivo que está justo al lado**. Tanto si el destino final es el rack siguiente como el otro lado del planeta, esta capa solo es responsable del siguiente salto.

### Ethernet

**Definición:** El estándar de capa de enlace que transporta tramas en redes locales cableadas.

**Cómo funciona:** Los datos se encapsulan en tramas, con las direcciones MAC de destino y origen al principio. Para el tráfico unicast conocido, un switch usa su tabla MAC para seleccionar el puerto de destino. Las tramas de difusión y las de unicast desconocido suelen inundar la VLAN; el comportamiento del tráfico multicast depende de la configuración. Las primeras versiones de Ethernet dependían de la detección de colisiones (CSMA/CD), pero en las redes conmutadas modernas de dúplex completo, las colisiones prácticamente han desaparecido.

**En la práctica:** Para el tráfico IP sobre Ethernet, una MTU de 1500 significa que hay un paquete IP de 1500 bytes dentro de la trama, sin contar el encabezado Ethernet ni el FCS. Las MTU jumbo dependen del dispositivo y de la ruta; 9001 es un valor compatible con EC2, no un tamaño Ethernet universal. En la nube, superponer una VPN o una red de superposición añade encabezados de encapsulación que reducen la MTU efectiva, y los fallos en la detección de MTU pueden crear un agujero negro que se manifiesta como «el ping funciona, pero las respuestas grandes se quedan colgadas». Es uno de los modos de fallo que más tiempo lleva diagnosticar.

**MTU frente a MSS:** La MSS limita los bytes de datos TCP, no la trama completa. Con una MTU de 1500, el cálculo con encabezados básicos da 1460 para IPv4 (1500−20−20) o 1440 para IPv6 (1500−40−20). El emisor reduce aún más los datos reales si incluye opciones de IP/TCP. TCP intercambia la MSS durante el protocolo de enlace, así que cuando los problemas de MTU se repiten a través de un túnel, el ajuste de MSS en el router (forzar una MSS de TCP más baja) es una solución alternativa muy utilizada.

### Wi-Fi

**Definición:** El estándar de capa de enlace que transporta tramas LAN a través de un segmento inalámbrico (IEEE 802.11).

**Cómo funciona:** Como el aire es un medio compartido, Wi-Fi es fundamentalmente distinto de Ethernet. Wi-Fi evita depender de la detección de colisiones durante la transmisión y usa CSMA/CA: primero comprueba que el canal esté libre, luego envía y, para el tráfico unicast normal, utiliza ACK/reintentos; el comportamiento de difusión y multicast es distinto. En otras palabras, la retransmisión ya está integrada en la capa de enlace.

**En la práctica:** Las retransmisiones de la capa de enlace, sumadas a las retransmisiones de TCP, aumentan la variación de la latencia (jitter). Los problemas de calidad en tiempo real se atribuyen a menudo al «servidor», cuando la verdadera causa es el segmento inalámbrico del cliente. El RTT del servidor por sí solo no permite localizar la causa; hay que correlacionarlo con el tiempo de procesamiento de la aplicación y las métricas de reintentos, señal y colas del cliente/AP.

### VLAN

**Definición:** Una técnica para segmentar una infraestructura de switches compartida en redes L2 lógicas (IEEE 802.1Q).

**Cómo funciona:** Una trama etiquetada con 802.1Q lleva una etiqueta VLAN de 4 bytes. Los puertos de acceso pueden transportar tramas sin etiquetar, que el switch asigna a una VLAN. Las difusiones solo llegan a los hosts de la misma VLAN, por lo que se puede segmentar una red sin tocar el cableado. El tráfico entre VLAN debe pasar por un dispositivo L3 (un router o un switch L3).

**En la práctica:** Las VLAN proporcionan segmentación lógica L2, no aislamiento físico ni criptográfico. Los controles de enrutamiento y firewall determinan qué tráfico entre segmentos está permitido. Las VPC, las subredes y los grupos de seguridad cumplen funciones distintas en las redes en la nube; no son sustitutos equivalentes uno a uno de las VLAN.

> 📎 Para saber cómo EKS estructura su VPC, consulta [Fundamentos de redes de EKS](../eks/03-eks-networking-part1.md).

### PPP

**Definición:** Un protocolo que transporta paquetes por un enlace punto a punto que conecta exactamente dos nodos.

**Cómo funciona:** A diferencia de Ethernet, no se necesita direccionamiento: solo hay un nodo en cada extremo del enlace. En cambio, PPP proporciona establecimiento del enlace, autenticación opcional y negociación de protocolos de capas superiores (LCP/NCP).

**En la práctica:** Parece una reliquia de la época del acceso telefónico, pero sigue presente como PPPoE en una gran parte de las conexiones residenciales a Internet. Con cargas útiles Ethernet estándar de 1500 bytes, el encabezado PPPoE habitual de 6 bytes más el campo de protocolo PPP de 2 bytes dejan 1492 bytes para IP; las capas subyacentes negociadas con mayor capacidad pueden conservar los 1500. Una reducción a 1492 que no se haya tenido en cuenta puede causar los problemas de MTU descritos anteriormente.

### ARP

**Definición:** El protocolo que resuelve la dirección IPv4 del siguiente salto en el enlace a una dirección MAC.

**Cómo funciona:** La capa IP dice «envía esto a 10.0.1.5», pero Ethernet solo entiende direcciones MAC. Así que el host difunde «¿quién tiene 10.0.1.5?» y el host que la posee responde. El resultado se almacena en caché con estados y tiempos de espera de vecinos específicos del sistema operativo. Para un destino fuera del enlace, el host resuelve la dirección MAC de su gateway, no la del host remoto.

**En la práctica:** ARP no tiene autenticación. Cualquiera puede responder «esa IP es mía», y eso es precisamente lo que permite la suplantación de ARP. Esa misma característica también se usa de forma legítima: durante una conmutación por error, el nuevo nodo activo difunde un ARP gratuito para anunciar a los vecinos la asignación de VIP a MAC; los switches también aprenden la ubicación de la MAC de origen a partir de la trama. Cuando una configuración de alta disponibilidad basada en VIP tarda en conmutar, la actualización retrasada de la caché es una de las principales sospechas.

> 📎 Para saber cómo Cilium integra el comportamiento L2 y de enrutamiento con eBPF, consulta [Redes de Cilium](../networking/cilium/03-networking.md).

---

## 2. Capa de Internet y enrutamiento: atravesar redes

Si la capa de enlace te lleva «a la puerta de al lado», esta capa te lleva «al otro lado del planeta». La pregunta central es: **¿adónde debe ir este paquete ahora?**

### IPv4

**Definición:** El protocolo de la capa de Internet basado en direcciones de 32 bits.

**Cómo funciona:** Cada paquete contiene las IP de origen y destino; cada router busca la ruta más específica (coincidencia de prefijo más largo) en su tabla de enrutamiento y reenvía el paquete al siguiente salto. La entrega es del mejor esfuerzo: no hay garantías ni orden. Esas garantías son responsabilidad de la capa superior (TCP).

**En la práctica:** IPv4 tiene unos 4.300 millones de direcciones posibles, y la escasez hizo que NAT se usara ampliamente y convirtió los rangos privados (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) en el estándar para redes internas. El primer obstáculo con el que se encuentran las grandes organizaciones al migrar a la nube es la superposición de estos rangos privados: los CIDR superpuestos de las instalaciones locales y la VPC impiden el enrutamiento directo por VPN o Direct Connect si no se diseña una solución de renumeración, traducción o proxy. El diseño de las direcciones IP debe definirse al inicio del proyecto.

#### IPv4, CIDR y un ejemplo de subred {#ipv4-cidr-subnet}

IPv4 tiene cuatro octetos de 8 bits. En la notación CIDR, `/26` fija los primeros 26 bits como prefijo de red y deja `32 − 26 = 6` bits de host. Las direcciones siguientes son ejemplos para documentación de [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html), no puntos de prueba públicos.

Para una dirección de interfaz **`192.0.2.130/26`**:

| Paso | Cálculo o resultado |
|---|---|
| Máscara de subred | `255.255.255.192`; el último octeto es `11000000` en binario |
| Direcciones por bloque | `2^6 = 64`; los bloques del último octeto empiezan en `0`, `64`, `128`, `192` |
| Dirección de red | `130 AND 192 = 128` (`10000010 AND 11000000 = 10000000`), por lo que es `192.0.2.128/26` |
| Dirección de difusión | Se establecen en 1 los seis bits de host: `192.0.2.191` |
| Rango de hosts normales | `192.0.2.129`–`192.0.2.190`: 62 direcciones |

La interfaz usa `.130`; `.128/26` identifica su subred. En una subred de difusión común, las partes de host compuestas solo por ceros o solo por unos identifican las direcciones de red y de difusión. Si se configura un gateway, este utiliza una dirección del rango de hosts; CIDR no exige que sea la primera dirección de host.

No apliques «restar dos» a todos los prefijos. [RFC 3021](https://www.rfc-editor.org/rfc/rfc3021.html) permite usar ambas direcciones de un `/31` en un enlace punto a punto compatible. Un `/32` identifica una dirección, a menudo como ruta de host; no implica que exista un par Ethernet conectado directamente. Las reglas de asignación en la nube son distintas: las subredes IPv4 estándar de una VPC de AWS reservan las primeras cuatro direcciones y la última, y dejan **59 direcciones asignables en un `/26`**, salvo excepciones como BYOIP. Consulta las [reglas de subredes de VPC](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html) para conocer el modo de asignación.

#### Prefijo más largo, siguiente salto y ARP {#longest-prefix-next-hop}

La búsqueda de rutas ocurre **antes** de la resolución de vecinos. Considera esta tabla de enrutamiento ilustrativa en un host Linux con `192.0.2.130/26` en `eth0`:

| Prefijo de destino | Siguiente salto / interfaz |
|---|---|
| `192.0.2.128/26` | Directamente en `eth0` (en el enlace) |
| `198.51.100.0/24` | A través de `192.0.2.129` en `eth0` |
| `198.51.100.128/25` | A través de `192.0.2.190` en `eth0` |
| `0.0.0.0/0` | Ruta predeterminada a través de `192.0.2.129` en `eth0` |

Dentro de la tabla seleccionada, elige la ruta coincidente con el **prefijo más largo** ([RFC 1812 §5.2.4.3](https://www.rfc-editor.org/rfc/rfc1812.html#section-5.2.4.3)):

- Para `192.0.2.150`, la ruta `/26` está en el enlace: si falta la entrada del vecino, resuelve **`.150` directamente** mediante ARP.
- Para `198.51.100.140`, coinciden `/24`, `/25` y `/0`; gana `/25`. Resuelve mediante ARP el gateway **`192.0.2.190`**, no el destino remoto.
- Para `203.0.113.10`, solo coincide `/0`: usa el gateway **`192.0.2.129`**.

En un paquete enrutado, el destino Ethernet es la MAC del gateway, mientras que el destino IP sigue siendo el host remoto (si no hay NAT). Una métrica más baja en la ruta predeterminada no prevalece sobre un `/25` coincidente. Las reglas de políticas de Linux pueden seleccionar tablas distintas; inspecciona la búsqueda real con `ip route get` en el espacio de nombres de red correspondiente, como se explica en el [manual ip-route(8)](https://man7.org/linux/man-pages/man8/ip-route.8.html). El host y un contenedor pueden tener rutas y tablas de vecinos diferentes.

### IPv6

**Definición:** El protocolo de próxima generación de la capa de Internet, con direcciones de 128 bits.

**Cómo funciona:** Con direcciones de 128 bits, el agotamiento no es un problema. El encabezado base tiene un formato fijo de 40 bytes y no lleva suma de comprobación del encabezado; los routers no fragmentan paquetes IPv6. SLAAC permite que los hosts configuren sus propias direcciones sin DHCP, y NDP (Neighbor Discovery Protocol) sustituye a ARP.

**En la práctica:** IPv6 no es compatible con versiones anteriores de IPv4, por lo que las implementaciones reales usan doble pila, lo que implica mantener dos conjuntos de reglas de firewall y políticas de seguridad. La ausencia de reglas en la ruta IPv6 es una brecha de seguridad habitual. Una dirección IPv6 global no hace que una carga de trabajo sea accesible desde Internet por sí sola. AWS sigue requiriendo enrutamiento y tráfico permitido por los grupos de seguridad/NACL; un gateway de Internet de solo salida puede permitir el tráfico IPv6 saliente sin conexiones entrantes no solicitadas.

**Mecanismos de transición:** Hay tres formas prácticas de coexistir con IPv4: **doble pila** (ejecutar ambas en paralelo; la opción más común, a costa de duplicar las políticas), **túneles** (encapsular paquetes IPv6 en IPv4 para cruzar segmentos que solo admiten v4) y **NAT64/DNS64** (traducir para que los clientes que solo admiten IPv6 puedan llegar a servidores IPv4; los operadores móviles lo usan a gran escala como 464XLAT). Kubernetes también admite Services de doble pila, así que el diseño del CIDR del clúster puede incluir un rango IPv6 desde el principio.

### ICMP

**Definición:** El protocolo de control que informa sobre errores y estados de la red.

**Cómo funciona:** ICMP transporta información de control y puede incluir cargas útiles Echo o datos citados del paquete original: destino inaccesible, TTL excedido, se requiere fragmentación, etc. `ping` usa Echo Request/Reply; `traceroute` incrementa el TTL (o el Hop Limit de IPv6) salto a salto y recibe los mensajes Time Exceeded de respuesta.

**En la práctica:** Bloquear todo ICMP «por seguridad» es habitual y es la causa directa del agujero negro de MTU mencionado antes. PMTUD clásico de IPv4 usa ICMP Type 3 Code 4, mientras que IPv6 usa ICMPv6 Packet Too Big Type 2. El bloqueo de mensajes necesarios puede causar agujeros negros; PLPMTUD puede probar tamaños de paquetes sin depender de ICMP. Permite el tráfico de error y detección necesario según la versión de IP y la política.

> 📎 Para ver cómo se manifiesta este fallo en EKS, consulta [Análisis detallado de redes de EKS](../eks/03-eks-networking-part3.md).

#### Interpretar las evidencias de ICMP y traceroute {#icmp-traceroute-interpretation}

En el reenvío IPv4, un router reduce el TTL del paquete; si este llega a cero, el router descarta esa sonda y normalmente devuelve **ICMP Time Exceeded (Type 11, Code 0)**. Es lo esperado cuando se envía deliberadamente una sonda con TTL corto, no una prueba de que fallen los paquetes normales de la aplicación. El mensaje de error cita una parte del paquete original para que el emisor pueda asociar la respuesta con su sonda ([RFC 792](https://www.rfc-editor.org/rfc/rfc792.html)).

Mantén separadas la **sonda saliente** y la **respuesta recibida**. Todos estos métodos habituales de traceroute pueden recibir ICMP Time Exceeded de routers intermedios:

| Sonda enviada | Respuesta habitual al llegar al destino |
|---|---|
| UDP a un puerto de destino sin usar | ICMP Destination Unreachable, Port Unreachable (IPv4 Type 3, Code 3) |
| ICMP Echo Request | ICMP Echo Reply |
| TCP SYN a un puerto elegido | TCP SYN/ACK para un puerto a la escucha, o RST para uno cerrado |

Los valores predeterminados y las opciones varían según la implementación; el [manual Linux traceroute(8)](https://man7.org/linux/man-pages/man8/traceroute.8.html) documenta los métodos UDP, ICMP y TCP. Una sonda TCP comprueba cómo se gestiona ese puerto, pero ni siquiera un SYN/ACK demuestra que TLS o HTTP funcionen.

Un `*` significa que **no llegó ninguna respuesta coincidente antes de que venciera el tiempo de espera**. Es posible que la sonda se haya filtrado, que el router suprima o limite la frecuencia de sus respuestas, o que la respuesta se haya perdido en la ruta de regreso. Un salto silencioso, si otros posteriores responden, no demuestra que haya pérdidas de extremo a extremo. Cada RTT mostrado incluye una ruta de regreso que puede diferir de la ruta de ida; además, el balanceo de carga puede mostrar distintos routers entre sondas. Compara observaciones repetidas con los resultados del destino y de la aplicación antes de localizar el fallo.

Traceroute explora principalmente los saltos; las sondas pequeñas que tienen éxito no validan la MTU de la ruta. Un paquete IPv4 más grande con DF activado quizá aún necesite **Fragmentation Needed (Type 3, Code 4)** para detectar una MTU menor. Distingue ese mensaje de Time Exceeded y Port Unreachable; mantén también las distinciones anteriores entre IPv6 y PLPMTUD.

> 📎 Aplica el razonamiento sobre rutas y sondas en el [laboratorio de enrutamiento e ICMP de Linux](../networking/07-linux-network-diagnostics.md#routing-icmp-lab) y luego úsalo para diagnosticar problemas en contenedores y Kubernetes.

### OSPF

**Definición:** Un protocolo de enrutamiento de estado de enlace que calcula rutas óptimas dentro de un único sistema autónomo.

**Cómo funciona:** Cada router inunda el área con su estado de enlace, de modo que los routers de una misma área convergen en información coherente sobre el estado de los enlaces; luego, cada uno ejecuta el algoritmo de Dijkstra para calcular las rutas más cortas. Los costos de las interfaces se configuran (a menudo se derivan del ancho de banda) y las redes se dividen en áreas para poder escalar.

**En la práctica:** OSPF es un IGP (para redes internas). La convergencia es rápida y las rutas se encuentran automáticamente, pero cada router mantiene información del estado de enlace de las áreas a las que está conectado, así que, a gran escala, el diseño de áreas determina el rendimiento.

### BGP

**Definición:** Un protocolo de enrutamiento por vector de rutas que intercambia información de accesibilidad entre sistemas autónomos (AS).

**Cómo funciona:** El objetivo de BGP es distinto del de OSPF: no elige «la ruta más rápida», sino «la ruta que prefieren las políticas». Cada AS anuncia los prefijos a los que puede llegar junto con la ruta de AS; quienes reciben esos anuncios ordenan las rutas según atributos como la longitud de AS_PATH, Local Preference y MED. El enrutamiento de todo Internet depende de esto.

**En la práctica:** BGP confía en los anuncios de forma predeterminada, por lo que los anuncios incorrectos de prefijos pueden provocar interrupciones generalizadas. La validación de origen RPKI comprueba si el origen del prefijo está autorizado; no valida toda la ruta de AS ni detiene todas las fugas de rutas. En la nube, Direct Connect usa BGP; Site-to-Site VPN puede usar BGP o enrutamiento estático compatible, por lo que los números de AS, el diseño de los prefijos anunciados y la preferencia de rutas para la redundancia (AS_PATH prepending y técnicas similares) se convierten en aspectos concretos del diseño.

> 📎 Para saber cómo Calico usa BGP dentro de un clúster, consulta [Análisis detallado de BGP en Calico](../networking/calico/04-bgp-deep-dive.md).

### NAT

**Definición:** Una función que traduce direcciones IP y, en el caso de NAPT/PAT, puertos de transporte.

**Cómo funciona:** Un caso común es que muchos hosts privados compartan una dirección pública mediante PAT/NAPT. La traducción también puede ser de una dirección privada a otra; no siempre consiste en compartir una dirección para acceder a Internet pública. Una tabla de traducción mantiene asignaciones por sesión para que los paquetes de respuesta vuelvan al host interno correcto.

**En la práctica:** NAT es el ejemplo emblemático de una infracción de las capas: un dispositivo L3 que reescribe puertos L4 y rompe la conectividad de extremo a extremo, la premisa original de Internet. Como resultado, las conexiones P2P se vuelven difíciles y hacen falta soluciones alternativas como STUN/TURN (consulta WebRTC más adelante). En la nube, los problemas prácticos son el agotamiento de puertos de NAT Gateway y los cargos por procesamiento de datos. Para cargas de trabajo con mucho tráfico saliente, los endpoints de VPC pueden reducir el procesamiento de NAT para los servicios de AWS compatibles; compara sus cargos por hora y por datos y la ruta del tráfico antes de dar por sentado que habrá ahorro.

---

**Siguiente:** [Parte 2: La capa de transporte y TLS](./06-network-fundamentals-part2.md)

## Referencias de verificación

- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/network_mtu.html
- https://www.rfc-editor.org/rfc/rfc894
- https://www.rfc-editor.org/rfc/rfc6691
- https://www.rfc-editor.org/rfc/rfc4638
- https://www.rfc-editor.org/rfc/rfc5227
- https://www.rfc-editor.org/rfc/rfc792
- https://www.rfc-editor.org/rfc/rfc8899
- https://www.rfc-editor.org/rfc/rfc2328
- https://www.rfc-editor.org/rfc/rfc6811
- https://docs.kernel.org/networking/bridge.html
- https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html
- https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html
- https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html
- https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-scenarios.html
- https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-pricing.html
