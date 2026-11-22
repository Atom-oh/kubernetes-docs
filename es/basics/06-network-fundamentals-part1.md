# Fundamentos de redes, parte 1: el modelo por capas, las capas de enlace y enrutamiento

> **Última actualización**: 14 de septiembre de 2026

::: tip Esta es una serie de cinco partes
**Parte 1: El modelo por capas, las capas de enlace y enrutamiento** *(este documento)* ·
[Parte 2: La capa de transporte y TLS](./06-network-fundamentals-part2.md) ·
[Parte 3: Protocolos de aplicación](./06-network-fundamentals-part3.md) ·
[Parte 4: El recorrido de una solicitud y la nube](./06-network-fundamentals-part4.md) ·
[Parte 5: Dispositivos de red, LAN y WAN](./06-network-fundamentals-part5.md)
:::

Una solicitud del navegador depende de varios protocolos que cooperan entre sí. La secuencia exacta depende de las cachés, la reutilización de conexiones, la versión de IP y la versión de HTTP, así que para solucionar problemas hay que examinar algo más que HTTP.

Esta serie recorre 25 protocolos y mecanismos de red, **capa por capa, de abajo arriba**. La razón para empezar desde abajo es sencilla: cada capa superior está diseñada bajo el supuesto de que las capas inferiores ya funcionan. Si se lee de arriba abajo, siempre se acaba preguntando: «pero ¿cómo funciona *esa* parte?».

Cada entrada sigue la misma estructura: **definición en una línea → cómo funciona → en qué casos causa problemas en la práctica**.

---

## 0. El mapa de capas en una página

| Capa | Función | Protocolos tratados aquí |
|---|---|---|
| Aplicación | Semántica real de los servicios | HTTP/3, WebSocket, WebRTC, gRPC, DNS, DoH, DHCP, MQTT, SSH, SMTP |
| Seguridad | Cifrado y autenticación (se apoya en el transporte) | TLS |
| Transporte | Entrega de datos de extremo a extremo | TCP, UDP, QUIC |
| Internet / Enrutamiento | Elegir rutas entre redes | IPv4, IPv6, ICMP, BGP, OSPF, NAT |
| Enlace | Entrega dentro de un segmento físico | Ethernet, Wi-Fi, VLAN, PPP, ARP |

Algunas entradas no respetan los límites bien definidos entre capas. TLS queda encajado entre el transporte y la aplicación, QUIC se ejecuta sobre UDP mientras realiza la función de una capa de transporte, y ARP conecta IP con la capa de enlace. NAT es más una función que un protocolo. Estas «excepciones» explican la mayoría de los problemas reales de redes.

---

![Muestra la ruta de las capas de enlace y enrutamiento, desde una laptop que pasa por un switch L2 y un router doméstico hasta el borde del ISP, el núcleo de internet impulsado por BGP, un router de centro de datos con OSPF y, finalmente, el servidor; se indican el protocolo y la MTU de cada segmento.](../.gitbook/assets/en-basics-06-network-fundamentals-part1-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-basics-06-network-fundamentals-part1-0.html)

---

## 1. Capa de enlace: mover bits dentro de un segmento

A la capa de enlace le importa una sola cosa: **cómo entregar bits al dispositivo que está justo al lado**. Tanto si el destino final está en el siguiente rack como en el otro extremo del planeta, esta capa solo es responsable del siguiente salto.

### Ethernet

**Definición:** El estándar de capa de enlace que transporta tramas en redes locales cableadas.

**Cómo funciona:** Los datos se encapsulan en tramas, con las direcciones MAC de destino y de origen al principio. Para el tráfico unicast conocido, un switch usa su tabla MAC para seleccionar el puerto de destino. Las tramas de difusión y unicast desconocido suelen inundar la VLAN; el comportamiento de multicast depende de la configuración. Las primeras versiones de Ethernet se basaban en la detección de colisiones (CSMA/CD), pero en las redes conmutadas modernas y dúplex completo, las colisiones prácticamente han desaparecido.

**En la práctica:** Para el tráfico IP de Ethernet, una MTU de 1500 significa que hay un paquete IP de 1500 bytes dentro de la trama, sin contar el encabezado Ethernet ni el FCS. Las MTU jumbo dependen del dispositivo y de la ruta; 9001 es un valor compatible con EC2, no un tamaño universal de Ethernet. En la nube, añadir una VPN o una red superpuesta reduce la MTU efectiva debido a los encabezados de encapsulación, y una detección de MTU fallida puede crear un agujero negro que se manifiesta como «el ping funciona, pero las respuestas grandes se quedan bloqueadas». Es uno de los modos de fallo que más tiempo lleva diagnosticar.

**MTU frente a MSS:** La MSS limita los bytes de datos TCP, no la trama completa. Con una MTU de 1500, el cálculo con encabezados básicos da 1460 para IPv4 (1500−20−20) o 1440 para IPv6 (1500−40−20). El emisor reduce aún más los datos reales según las opciones IP/TCP que incluya. TCP intercambia la MSS durante el handshake, así que, cuando los problemas de MTU se repiten en un túnel, limitar la MSS en el router (forzar una MSS TCP menor) es una solución alternativa muy utilizada.

### Wi-Fi

**Definición:** El estándar de capa de enlace que transporta tramas LAN por un segmento inalámbrico (IEEE 802.11).

**Cómo funciona:** Como el aire es un medio compartido, Wi-Fi es fundamentalmente distinto de Ethernet. Wi-Fi evita depender de la detección de colisiones durante la transmisión y usa CSMA/CA: comprueba que el canal esté libre antes de enviar y, luego, usa ACK/reintentos para el tráfico unicast habitual; el comportamiento de difusión/multicast es diferente. En otras palabras, la retransmisión ya está integrada en la capa de enlace.

**En la práctica:** La retransmisión de la capa de enlace, sumada a la retransmisión de TCP, aumenta la variación de la latencia (jitter). Los problemas de calidad en tiempo real se atribuyen al «servidor» cuando el verdadero culpable es el segmento inalámbrico del cliente. El RTT del servidor por sí solo no permite localizar la causa; hay que correlacionarlo con el tiempo de procesamiento de la aplicación y con las métricas de reintentos, señal y colas del cliente/AP.

### VLAN

**Definición:** Técnica para segmentar una infraestructura de switches compartida en redes L2 lógicas (IEEE 802.1Q).

**Cómo funciona:** Una trama etiquetada con 802.1Q lleva una etiqueta VLAN de 4 bytes. Los puertos de acceso pueden transportar tramas sin etiqueta que el switch asigna a una VLAN. Las difusiones solo llegan a los hosts de la misma VLAN, por lo que se puede segmentar una red sin tocar el cableado. El tráfico entre VLAN debe pasar por un dispositivo L3 (un router o un switch L3).

**En la práctica:** Las VLAN proporcionan segmentación L2 lógica, no aislamiento físico ni criptográfico. Los controles de enrutamiento y firewall determinan qué tráfico entre segmentos está permitido. Las VPC, las subredes y los grupos de seguridad cumplen funciones distintas en las redes de la nube; no son sustitutos equivalentes de las VLAN.

> 📎 Para saber cómo EKS estructura su VPC, consulta [Fundamentos de redes de EKS](../eks/03-eks-networking-part1.md).

### PPP

**Definición:** Protocolo que transporta paquetes por un enlace punto a punto que conecta exactamente dos nodos.

**Cómo funciona:** A diferencia de Ethernet, no se necesita direccionamiento; hay un solo nodo en cada extremo del enlace. En cambio, PPP proporciona el establecimiento del enlace, autenticación opcional y negociación de protocolos superiores (LCP/NCP).

**En la práctica:** Parece una reliquia de la era del acceso telefónico, pero sigue existiendo como PPPoE en una gran parte de las conexiones residenciales a internet. Con cargas útiles Ethernet estándar de 1500 bytes, el encabezado PPPoE habitual de 6 bytes más el campo de protocolo PPP de 2 bytes dejan 1492 bytes para IP; una infraestructura subyacente negociada con un tamaño mayor puede conservar los 1500. Una reducción a 1492 que no se tenga en cuenta puede causar los problemas de MTU descritos antes.

### ARP

**Definición:** Protocolo que resuelve la dirección IPv4 del siguiente salto en el enlace y la convierte en una dirección MAC.

**Cómo funciona:** La capa IP dice «envía esto a 10.0.1.5», pero Ethernet solo entiende direcciones MAC. Así que el host difunde «¿quién tiene 10.0.1.5?» y responde el host propietario. El resultado se almacena en caché con estados y tiempos de espera de vecinos específicos del sistema operativo. Si el destino no está en el enlace, el host resuelve la dirección MAC de su gateway, no la del host remoto.

**En la práctica:** ARP no tiene autenticación. Cualquiera puede responder «esa IP es mía», y eso es precisamente lo que hace posible la suplantación de ARP. Esta misma característica también se usa legítimamente: durante una conmutación por error, el nuevo nodo activo envía un ARP gratuito para anunciar a los vecinos la asignación VIP-MAC; los switches también aprenden la ubicación de la MAC de origen a partir de la trama. Si una configuración de alta disponibilidad basada en VIP tarda en completar la conmutación por error, una causa probable es el retraso en la actualización de la caché.

> 📎 Para saber cómo Cilium integra el comportamiento L2 y de enrutamiento con eBPF, consulta [Redes con Cilium](../networking/cilium/03-networking.md).

---

## 2. Capa de Internet y enrutamiento: cruzar redes

Si la capa de enlace te lleva «a la puerta de al lado», esta capa te lleva «al otro extremo del planeta». La pregunta central es: **¿adónde debe ir este paquete ahora?**

### IPv4

**Definición:** Protocolo de capa de Internet basado en direcciones de 32 bits.

**Cómo funciona:** Cada paquete lleva direcciones IP de origen y destino; cada router busca la ruta más específica (coincidencia de prefijo más largo) en su tabla de enrutamiento y lo reenvía al siguiente salto. La entrega es de mejor esfuerzo: no hay garantías ni orden. Esas garantías son responsabilidad de la capa superior (TCP).

**En la práctica:** IPv4 tiene unos 4.300 millones de direcciones posibles, y su escasez hizo que NAT se usara ampliamente y convirtió los rangos privados (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) en el estándar para redes internas. El primer obstáculo que encuentran las grandes organizaciones al migrar a la nube es la superposición de estos rangos privados: los CIDR superpuestos de las redes locales y las VPC impiden el enrutamiento directo por VPN o Direct Connect, salvo que se diseñe una solución de renumeración, traducción o proxy. El diseño de direcciones IP es algo que debe definirse al inicio del proyecto.

#### IPv4, CIDR y un ejemplo de subred {#ipv4-cidr-subnet}

IPv4 tiene cuatro octetos de 8 bits. En la notación CIDR, `/26` fija los primeros 26 bits como prefijo de red y deja `32 − 26 = 6` bits para hosts. Las direcciones que aparecen a continuación son ejemplos para documentación de [RFC 5737](https://www.rfc-editor.org/rfc/rfc5737.html), no puntos de conexión de prueba públicos.

Para una dirección de interfaz **`192.0.2.130/26`**:

| Paso | Cálculo o resultado |
|---|---|
| Máscara de subred | `255.255.255.192`; último octeto `11000000` en binario |
| Direcciones por bloque | `2^6 = 64`; los bloques del último octeto empiezan en `0`, `64`, `128`, `192` |
| Dirección de red | `130 AND 192 = 128` (`10000010 AND 11000000 = 10000000`), por lo que `192.0.2.128/26` |
| Dirección de difusión | Establece en 1 los seis bits de host: `192.0.2.191` |
| Rango de hosts ordinarios | `192.0.2.129`–`192.0.2.190`: 62 direcciones |

La interfaz es propietaria de `.130`; `.128/26` identifica su subred. En una subred de difusión ordinaria, las porciones de host formadas solo por ceros o solo por unos identifican las direcciones de red y de difusión. Si se configura un gateway, este consume una dirección del rango de hosts; CIDR no exige que sea la primera dirección de host.

No apliques «restar dos» a todos los prefijos. [RFC 3021](https://www.rfc-editor.org/rfc/rfc3021.html) permite usar ambas direcciones de un `/31` en un enlace punto a punto compatible. Un `/32` identifica una dirección, a menudo como ruta de host; no implica que haya un par Ethernet conectado directamente. Las reglas de asignación de la nube son independientes: las subredes IPv4 estándar de AWS VPC reservan las primeras cuatro direcciones y la última, por lo que quedan **59 direcciones asignables en un `/26`**, salvo excepciones como BYOIP. Consulta las [reglas de subredes de VPC](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html) para ver el modo de asignación.

#### Prefijo más largo, siguiente salto y ARP {#longest-prefix-next-hop}

La búsqueda de rutas se realiza **antes** de resolver los vecinos. Considera esta tabla de enrutamiento ilustrativa en un host Linux con `192.0.2.130/26` en `eth0`:

| Prefijo de destino | Siguiente salto / interfaz |
|---|---|
| `192.0.2.128/26` | Directamente en `eth0` (en el enlace) |
| `198.51.100.0/24` | A través de `192.0.2.129` en `eth0` |
| `198.51.100.128/25` | A través de `192.0.2.190` en `eth0` |
| `0.0.0.0/0` | Ruta predeterminada a través de `192.0.2.129` en `eth0` |

Dentro de la tabla seleccionada, elige la ruta coincidente con el **prefijo más largo** ([RFC 1812 §5.2.4.3](https://www.rfc-editor.org/rfc/rfc1812.html#section-5.2.4.3)):

- Para `192.0.2.150`, la ruta `/26` está en el enlace: si falta la entrada del vecino, resuelve con ARP **el propio `.150`**.
- Para `198.51.100.140`, coinciden `/24`, `/25` y `/0`; gana `/25`. Resuelve con ARP el gateway **`192.0.2.190`**, no el destino remoto.
- Para `203.0.113.10`, solo coincide `/0`: usa el gateway **`192.0.2.129`**.

Para un paquete enrutado, el destino Ethernet es la MAC del gateway, mientras que el destino IP sigue siendo el host remoto (si no hay NAT). Una métrica menor en la ruta predeterminada no prevalece sobre una ruta `/25` coincidente. Las reglas de política de Linux pueden seleccionar tablas distintas; inspecciona la búsqueda real con `ip route get` en el espacio de nombres de red correspondiente, como se describe en el [manual de ip-route(8)](https://man7.org/linux/man-pages/man8/ip-route.8.html). El host y un contenedor pueden tener rutas y tablas de vecinos distintas.

### IPv6

**Definición:** Protocolo de nueva generación de la capa de Internet con direcciones de 128 bits.

**Cómo funciona:** Con direcciones de 128 bits, el agotamiento deja de ser un problema. El encabezado base tiene una estructura fija de 40 bytes y no incluye suma de comprobación; los routers no fragmentan paquetes IPv6. SLAAC permite que los hosts configuren sus propias direcciones sin DHCP, y NDP (Neighbor Discovery Protocol) sustituye a ARP.

**En la práctica:** IPv6 no es compatible con versiones anteriores de IPv4, así que las implementaciones reales funcionan en modo de doble pila, lo que implica mantener dos conjuntos de reglas de firewall y políticas de seguridad. La falta de reglas en la ruta IPv6 es una brecha de seguridad común. Una dirección IPv6 global no hace que una carga de trabajo sea accesible desde internet por sí sola. AWS sigue exigiendo enrutamiento y tráfico permitido en los grupos de seguridad y las NACL; un gateway de internet de solo salida puede permitir tráfico IPv6 saliente sin conexiones entrantes no solicitadas.

**Mecanismos de transición:** Hay tres formas prácticas de coexistir con IPv4: **doble pila** (ejecutar ambos protocolos en paralelo; es la opción más común, aunque duplica las políticas), **túneles** (encapsular paquetes IPv6 en IPv4 para cruzar segmentos que solo admiten v4) y **NAT64/DNS64** (traducir para que los clientes que solo usan IPv6 puedan acceder a servidores IPv4; los operadores móviles lo usan a gran escala como 464XLAT). Kubernetes también admite Services de doble pila, por lo que el diseño del CIDR del clúster puede contemplar un rango IPv6 desde el principio.

### ICMP

**Definición:** Protocolo de control que informa de errores y estados de la red.

**Cómo funciona:** ICMP transporta información de control y puede incluir cargas útiles Echo o datos citados del paquete original: destino inaccesible, TTL agotado, fragmentación necesaria, etc. `ping` usa Echo Request/Reply; `traceroute` incrementa el TTL (o el límite de saltos IPv6) un salto cada vez y lee los mensajes Time Exceeded que regresan.

**En la práctica:** Es habitual bloquear ICMP por completo «por seguridad», y eso causa directamente el agujero negro de MTU mencionado antes. PMTUD clásico en IPv4 usa ICMP Tipo 3 Código 4, mientras que IPv6 usa ICMPv6 Packet Too Big Tipo 2. Bloquear los mensajes necesarios puede crear agujeros negros; PLPMTUD, en cambio, puede sondear tamaños de paquete sin depender de ICMP. Permite el tráfico de error y detección necesario según la versión de IP y la política.

> 📎 Para ver cómo se manifiesta este fallo en EKS, consulta [Análisis detallado de redes de EKS](../eks/03-eks-networking-part3.md).

#### Interpretar las evidencias de ICMP y traceroute {#icmp-traceroute-interpretation}

En el reenvío IPv4, un router reduce el TTL del paquete; si este se agota, el router descarta el sondeo y normalmente devuelve **ICMP Time Exceeded (Tipo 11, Código 0)**. Es lo esperado en un sondeo con TTL deliberadamente bajo, no una prueba de que fallen los paquetes normales de la aplicación. El error cita parte del paquete original para que el emisor pueda asociar la respuesta con su sondeo ([RFC 792](https://www.rfc-editor.org/rfc/rfc792.html)).

Mantén separada la **sonda saliente** de la **respuesta que regresa**. Todos estos métodos comunes de traceroute pueden recibir ICMP Time Exceeded de routers intermedios:

| Sonda enviada | Respuesta habitual al llegar al destino |
|---|---|
| UDP a un puerto de destino sin usar | ICMP Destination Unreachable, Port Unreachable (IPv4 Tipo 3, Código 3) |
| ICMP Echo Request | ICMP Echo Reply |
| TCP SYN a un puerto elegido | TCP SYN/ACK si el puerto está escuchando, o RST si está cerrado |

Los valores predeterminados y las opciones varían según la implementación; el [manual de Linux traceroute(8)](https://man7.org/linux/man-pages/man8/traceroute.8.html) documenta los métodos UDP, ICMP y TCP. Una sonda TCP comprueba el tratamiento de ese puerto, pero ni siquiera un SYN/ACK demuestra que TLS o HTTP funcionen.

Un `*` significa que **no llegó ninguna respuesta coincidente antes de que expirara la espera**. Es posible que la sonda se haya filtrado, que el router suprima o limite la frecuencia de sus respuestas, o que la respuesta se haya perdido en la ruta de regreso. Un salto silencioso con respuestas de saltos posteriores no demuestra que haya pérdidas de extremo a extremo. Cada RTT mostrado incluye una ruta de regreso que puede ser distinta de la ruta de ida; el balanceo de carga también puede revelar routers distintos en cada sondeo. Compara observaciones repetidas con los resultados del destino y de la aplicación antes de localizar el fallo.

Traceroute explora principalmente los saltos; que los sondeos pequeños tengan éxito no valida la MTU de la ruta. Puede que un paquete IPv4 más grande con DF activado necesite igualmente **Fragmentation Needed (Tipo 3, Código 4)** para descubrir una MTU menor. Distingue ese mensaje de Time Exceeded y Port Unreachable; mantén las distinciones de IPv6 y PLPMTUD descritas antes.

> 📎 Aplica el razonamiento sobre rutas y sondeos en el [laboratorio de enrutamiento e ICMP en Linux](../networking/07-linux-network-diagnostics.md#routing-icmp-lab) y, después, úsalo para solucionar problemas de contenedores y Kubernetes.

### OSPF

**Definición:** Protocolo de enrutamiento de estado de enlace que calcula rutas óptimas dentro de un único sistema autónomo.

**Cómo funciona:** Cada router difunde el estado de sus enlaces por toda el área, de modo que los routers de una misma área convergen en información de estado de enlace coherente; luego, cada uno ejecuta el algoritmo de Dijkstra para calcular las rutas más cortas. Los costos de las interfaces se configuran (a menudo se derivan del ancho de banda) y las redes se dividen en áreas para escalar.

**En la práctica:** OSPF es un IGP (para redes internas). La convergencia es rápida y las rutas se encuentran automáticamente, pero cada router mantiene información de estado de enlace para las áreas a las que está conectado, así que, a gran escala, el diseño de las áreas determina el rendimiento.

### BGP

**Definición:** Protocolo de enrutamiento de vector de rutas que intercambia información de alcanzabilidad entre sistemas autónomos (AS).

**Cómo funciona:** El objetivo de BGP es distinto del de OSPF: no elige «la ruta más rápida», sino «la ruta que prefiere la política». Cada AS anuncia los prefijos a los que puede llegar junto con la ruta de AS; los receptores clasifican las rutas según atributos como la longitud de AS_PATH, Local Preference y MED. El enrutamiento de todo internet depende de esto.

**En la práctica:** BGP confía de forma predeterminada en los anuncios, por lo que los anuncios de prefijos incorrectos pueden causar interrupciones generalizadas. La validación de origen RPKI comprueba si el origen del prefijo está autorizado; no valida toda la ruta de AS ni detiene todas las fugas de rutas. Desde la perspectiva de la nube, Direct Connect usa BGP; Site-to-Site VPN puede usar BGP o enrutamiento estático compatible, así que los números de AS, el diseño de los prefijos anunciados y la preferencia de rutas para la redundancia (AS_PATH prepending y métodos relacionados) son aspectos reales del diseño.

> 📎 Para saber cómo Calico usa BGP dentro de un clúster, consulta [Análisis detallado de BGP en Calico](../networking/calico/04-bgp-deep-dive.md).

### NAT

**Definición:** Función que traduce direcciones IP y, en el caso de NAPT/PAT, puertos de transporte.

**Cómo funciona:** Un caso común es que muchos hosts privados compartan una dirección pública mediante PAT/NAPT. La traducción también puede ser de privado a privado; no siempre consiste en compartir una dirección para acceder a internet pública. Una tabla de traducción conserva las asignaciones por sesión para que los paquetes de respuesta encuentren el host interno correcto.

**En la práctica:** NAT es el ejemplo más claro de una infracción de capas: un dispositivo L3 que reescribe puertos L4 y rompe la conectividad de extremo a extremo, que era la premisa original de internet. Como resultado, las conexiones P2P se complican y hacen falta soluciones alternativas como STUN/TURN (consulta WebRTC más adelante). En la nube, los problemas prácticos son el agotamiento de puertos del NAT Gateway y los cargos por procesamiento de datos. Para las cargas de trabajo con mucho tráfico saliente, los puntos de conexión de VPC pueden reducir el procesamiento de NAT para los servicios de AWS compatibles; compara sus cargos por hora y por datos, así como la ruta del tráfico, antes de dar por hecho que ahorrarás.

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
