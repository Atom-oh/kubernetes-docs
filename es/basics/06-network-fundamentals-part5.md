# Fundamentos de redes, parte 5: dispositivos de red, conceptos básicos de LAN y WAN

> **Última actualización**: 19 de noviembre de 2026

::: tip Esta es una serie de cinco partes
[Parte 1: El modelo por capas, las capas de enlace y de enrutamiento](./06-network-fundamentals-part1.md) ·
[Parte 2: La capa de transporte y TLS](./06-network-fundamentals-part2.md) ·
[Parte 3: Protocolos de aplicación](./06-network-fundamentals-part3.md) ·
[Parte 4: El recorrido de una solicitud y la nube](./06-network-fundamentals-part4.md) ·
**Parte 5: Dispositivos de red, LAN y WAN** *(este documento)*
:::

En las partes 1 a 4 recorrimos los protocolos capa por capa. Esta parte trata los **dispositivos** que procesan esos protocolos y los **diseños de LAN y WAN** que los conectan. Las tramas Ethernet, ARP, la coincidencia del prefijo más largo y la definición básica de NAT ya se explican en la [parte 1](./06-network-fundamentals-part1.md), así que no se repiten aquí. En cambio, esta parte se centra en qué examina cada dispositivo, qué decisión toma y dónde fallan la redundancia y la traducción de direcciones.

El alcance corresponde a las áreas de Fundamentos de redes, Acceso a redes y Servicios IP de CCNA (200-301), y al dominio 1 de CompTIA Network+ (N10-009). Los temarios de los exámenes solo sirvieron para dar forma al índice. Los números y el comportamiento de los protocolos se verificaron con los estándares y los documentos de proveedores y AWS que aparecen en Referencias al final; el comportamiento básico de dispositivos como los hubs y los AP se presenta como una definición general.

Al igual que en la parte 1, cada tema sigue el orden **definición → funcionamiento → problemas que presenta en la práctica**.

---

<a id="device-roles"></a>

## 1. Funciones de los dispositivos: quién examina qué

La forma más clara de distinguir los dispositivos es preguntarse **qué tabla consulta el dispositivo** para decidir adónde enviar lo que recibió por un puerto.

| Dispositivo | Entrada principal | Tabla consultada | Decisión |
|---|---|---|---|
| Hub (repetidor) | Nada (señales de bits) | Ninguna | Repite la señal por todos los demás puertos |
| Switch L2 | MAC de destino + VLAN | Tabla de direcciones MAC | El unicast conocido se envía por un puerto; las difusiones y los destinos desconocidos se inundan dentro de la VLAN |
| Switch L3 | MAC dentro de una VLAN, IP de destino entre subredes | Tabla MAC + enrutamiento (FIB) | Conmuta dentro de una VLAN y enruta entre VLAN mediante interfaces virtuales por VLAN (SVI) que actúan como puertas de enlace |
| Router | IP de destino | FIB creada a partir de la tabla de enrutamiento | Reenvía al siguiente salto de la ruta con el prefijo más largo, reduce el TTL en 1 y escribe un encabezado L2 nuevo |
| Firewall con estado / NGFW | Tupla de 5 elementos y estado de la conexión; un NGFW también identifica la aplicación | Reglas de políticas + tabla de estado (conexiones) | Las reglas evalúan las conexiones nuevas; los paquetes de respuesta posteriores pasan si coinciden con la tabla de estado |
| Balanceador de carga | Tupla de 5 elementos en L4; host, ruta y encabezados HTTP en L7 | Reglas del listener, estado de los destinos del grupo de destino | Elige un destino en buen estado y reenvía el tráfico a él |
| AP inalámbrico | MAC de la estación, SSID | Lista de estaciones asociadas, asignación de SSID a VLAN | Conecta las tramas 802.11 a la red de distribución cableada |

Puntos que conviene tener en cuenta sobre cada dispositivo:

- Un **hub** es un dispositivo L1 y nunca examina direcciones. Todos los dispositivos conectados a él comparten un medio semidúplex, por lo que las transmisiones simultáneas chocan.
- Un **switch L2** aprende la **MAC de origen** de cada trama asociándola al puerto de entrada y a la VLAN, y selecciona el puerto de salida según la **MAC de destino**. No modifica la trama (la excepción es añadir o quitar una etiqueta 802.1Q en un trunk).
- Un **switch L3** es hardware de conmutación con funciones de enrutamiento integradas. Como en el ejemplo de Cisco, se crea una SVI por VLAN y se usa su dirección como puerta de enlace predeterminada de esa VLAN.
- Un **router** no reenvía a otras interfaces un paquete que recibió como difusión L2 (RFC 1812 §5.3.4, salvo que se trate de destinos de multidifusión IP), ni reenvía la difusión limitada `255.255.255.255` (§5.3.5.1), por lo que una interfaz de router (o una SVI) marca el límite de un dominio de difusión. Un paquete enrutado recibe un TTL menor y nuevas MAC de origen y destino, pero sus direcciones IP se mantienen, a menos que intervenga NAT.
- Un **firewall con estado** lleva el seguimiento de las conexiones, así que no es necesario escribir reglas separadas para los paquetes de respuesta. NIST SP 800-41 distingue los filtros de paquetes, la inspección con estado (que conserva una entrada por conexión en una tabla de estado) y los firewalls de aplicación y las puertas de enlace proxy; denomina UTM a un firewall que incluye detección de malware y funciones similares. «NGFW» no es un término de NIST; es un término de los proveedores para productos que agrupan la identificación de aplicaciones, la identificación de usuarios, la prevención de intrusiones y funciones similares.
- Un **balanceador de carga** toma decisiones distintas según su capa. En AWS, un ALB evalúa las reglas del listener en orden de prioridad y luego selecciona un destino del grupo de destino de la regla; un NLB selecciona un destino mediante un hash del flujo basado en el protocolo, las IP y los puertos de origen y destino, y el número de secuencia TCP, y mantiene cada conexión TCP en un mismo destino durante toda su vida útil.
- Un **AP** es un puente entre las redes inalámbrica y cableada. Es común asignar cada SSID a una VLAN distinta, por lo que las estaciones inalámbricas atraviesan las mismas decisiones de conmutación y enrutamiento descritas anteriormente.

**En la práctica:** para acotar una falla, consulta «la tabla que usa este dispositivo». En Linux, `bridge fdb show` muestra las MAC aprendidas por un puente, `ip route get <destination>` muestra la decisión de enrutamiento y las herramientas de conntrack muestran la tabla de seguimiento de conexiones (estado y NAT). Si falta la entrada que esperabas, la causa está en un paso anterior al de ese dispositivo.

### Dominios de colisión y dominios de difusión

**Definición:** un **dominio de colisión** es el alcance de un medio compartido en el que las transmisiones simultáneas chocan; un **dominio de difusión** es el alcance hasta el que llega una trama de difusión L2.

**Funcionamiento:**

- Un hub coloca todos sus puertos en un mismo dominio de colisión.
- Un switch asigna a cada puerto su propio dominio de colisión. En enlaces dúplex completo, la transmisión y la recepción son independientes, así que no se producen colisiones (consulta [Ethernet en la parte 1](./06-network-fundamentals-part1.md#ethernet)).
- Una VLAN es un dominio de difusión. Si la misma VLAN se extiende por varios switches mediante trunks, toda esa extensión sigue siendo **un solo** dominio de difusión.
- Las interfaces de los routers y las SVI no reenvían difusiones, así que dividen los dominios de difusión.

**Conteo con un ejemplo:** un switch transporta las VLAN 10, 20 y 30 y se conecta a un router (tres subinterfaces) mediante un trunk. Uno de los puertos del switch tiene conectado un hub con cuatro PC.

| Pregunta | Respuesta | Motivo |
|---|---|---|
| Número de dominios de difusión | 3 | Uno por VLAN; el router detiene las difusiones entre VLAN |
| Dominios de colisión para los cuatro PC conectados al hub | 1 | Un hub es un medio compartido, así que los cuatro PC comparten un dominio de colisión |
| Un host por puerto del switch | 1 por puerto | Los puertos del switch separan los dominios de colisión y, en dúplex completo, no hay colisiones reales |

**En la práctica:** en un dominio de difusión grande, las difusiones como ARP y DHCP activan la CPU de todos los hosts, y un bucle afecta a más hosts. Por eso las VLAN se mantienen pequeñas y el tráfico entre ellas se enruta.

---

<a id="vlan-trunk"></a>

## 2. VLAN y trunks 802.1Q

La definición de una VLAN y la regla de que el tráfico entre VLAN necesita un dispositivo L3 se encuentran en [VLAN en la parte 1](./06-network-fundamentals-part1.md#vlan). Esta sección examina qué contiene realmente la etiqueta y qué problemas pueden surgir en un trunk.

### La etiqueta 802.1Q

**Definición:** IEEE 802.1Q inserta una etiqueta de 4 bytes después de la MAC de origen de una trama Ethernet para indicar a qué VLAN pertenece la trama.

**Funcionamiento:** la etiqueta tiene cuatro campos.

| Campo | Tamaño | Significado |
|---|---|---|
| TPID | 16 bits | Valor `0x8100`: identifica la trama como etiquetada con 802.1Q |
| PCP | 3 bits | Prioridad de 0 a 7 (802.1p) |
| DEI (antes CFI) | 1 bit | Indica las tramas que pueden descartarse primero en caso de congestión |
| VID | 12 bits | ID de VLAN. Los valores van de 0 a 4095, pero 0 y 4095 están reservados, así que las VLAN reales usan del 1 al 4094 |

La etiqueta añade 4 bytes, por lo que una trama etiquetada puede medir hasta 1522 bytes, y el dispositivo que inserta la etiqueta vuelve a calcular el FCS.

### Puertos de acceso, puertos trunk y VLAN nativa

**Definición:**

- Un **puerto de acceso** pertenece a una VLAN y envía y recibe tramas sin etiqueta con el host.
- Un **puerto trunk** transporta varias VLAN por un mismo enlace y etiqueta cada trama con su VID.
- La **VLAN nativa** es la VLAN que atraviesa un trunk **sin etiqueta**.

**Funcionamiento:** según la documentación de Cisco Catalyst, la VLAN nativa predeterminada es la **VLAN 1**; el dispositivo asigna a la VLAN nativa las tramas sin etiqueta recibidas por un trunk y envía sin etiqueta las tramas de la VLAN nativa. La VLAN nativa **debe coincidir** en ambos extremos del trunk. Si no coincide, las tramas sin etiqueta de la VLAN de un lado terminan en otra VLAN en el otro lado, lo que rompe la separación entre VLAN, y Cisco advierte que pueden producirse bucles de spanning tree. De forma predeterminada, un trunk permite todas las VLAN del 1 al 4094.

**En la práctica:**

- Reduce la lista de VLAN permitidas de cada trunk a las que necesita, cambia la VLAN nativa por una VLAN sin usar y mantén la misma configuración en ambos extremos.
- Linux puede crear una subinterfaz etiquetada con `ip link add link eth0 name eth0.10 type vlan id 10`. Así es como los hipervisores y los nodos bare-metal de Kubernetes se conectan a un puerto trunk.

### Enrutamiento entre VLAN: router-on-a-stick

Colocar una subinterfaz de router por VLAN en un solo trunk permite que un router actúe como puerta de enlace de varias VLAN. La animación siguiente sigue una trama desde el PC-A de la VLAN 10 hasta el PC-B de la VLAN 20. El punto clave es que sube y baja por el mismo cable.

![Animación del enrutamiento entre VLAN. ① El PC-A (VLAN 10, 10.0.10.5) detecta que el destino está en otra subred, así que direcciona la trama a la MAC de la puerta de enlace 10.0.10.1. ② El switch de acceso L2 aprende la MAC de origen en el puerto 1 de la VLAN 10 y envía la trama por el trunk 802.1Q con una etiqueta de VLAN 10. ③ La búsqueda de ruta del router para 10.0.20.0/24 selecciona la subinterfaz .20, reduce el TTL de 64 a 63 y escribe un encabezado L2 nuevo (las direcciones IP no cambian). ④ La trama vuelve por el mismo trunk, etiquetada con la VLAN 20. ⑤ El switch quita la etiqueta y la reenvía por el puerto de acceso de la VLAN 20; el PC-B (10.0.20.7) la recibe.](../.gitbook/assets/en-basics-06-network-fundamentals-part5-anim-0.svg)

Cuando un switch L3 realiza la misma tarea, enruta entre SVI dentro del propio switch, en lugar de subir y bajar por un trunk. El tráfico entre VLAN ya no consume dos veces el ancho de banda del trunk, por lo que se usan switches L3 cuando hay mucho tráfico entre VLAN.

---

<a id="stp-lacp-fhrp"></a>

## 3. Prevención de bucles y redundancia: STP, LACP, FHRP

Los enlaces y dispositivos redundantes aumentan la disponibilidad, pero generan bucles en L2 y el problema de «¿quién es la puerta de enlace predeterminada?» en la puerta de enlace L3. Tres tecnologías resuelven cada una uno de estos problemas.

### STP y RSTP

**Definición:** el protocolo Spanning Tree (STP, IEEE 802.1D) bloquea algunos enlaces redundantes entre switches para que la topología L2 forme un árbol sin bucles. RSTP (802.1w, incorporado posteriormente a 802.1D-2004) es su versión de convergencia rápida.

**Por qué se necesita:** los encabezados IP llevan un TTL, pero **los encabezados Ethernet no**. Si hay un bucle entre switches, una trama de difusión nunca desaparece: sigue circulando y multiplicándose (una tormenta de difusión), y la misma MAC de origen aparece en varios puertos, por lo que las tablas MAC cambian constantemente.

**Funcionamiento:**

1. **Elección del puente raíz:** el switch con el ID de puente más bajo (prioridad + MAC) se convierte en la raíz. La prioridad predeterminada es 32768; por tanto, si no se configura nada, el switch con la MAC más baja, que suele ser el más antiguo, se convierte en la raíz.
2. **Funciones de los puertos:** cada switch que no es raíz designa su mejor puerto hacia la raíz como **puerto raíz**, y en cada segmento el puerto que envía la mejor BPDU se convierte en el **puerto designado**. Los puertos restantes se bloquean (los roles alternativo y de respaldo en RSTP).
3. **Convergencia:** 802.1D funciona con temporizadores. Los valores predeterminados son: hello 2 s, max age 20 s y forward delay 15 s; un puerto pasa dos intervalos de forward delay, unos 30 s, en los estados de escucha y aprendizaje. RSTP reduce los estados a descarte, aprendizaje y reenvío; en los enlaces punto a punto pasa al estado de reenvío mediante un intercambio de propuesta y acuerdo, en vez de esperar a que se cumplan los temporizadores. Los puertos de host se configuran como puertos perimetrales (PortFast de Cisco) y reenvían de inmediato.

**En la práctica:** no dejes la raíz del puente con la configuración predeterminada; reduce la prioridad en los switches centrales o de distribución para fijarla donde quieras. Si un switch cualquiera se convierte en raíz, el tráfico dará un rodeo a través de él. Recuerda también que, en condiciones normales, los enlaces bloqueados no transportan tráfico. LACP, que se explica a continuación, y la topología spine-leaf de la sección 4 evitan esta limitación de distintas maneras.

### LACP y EtherChannel

**Definición:** la agregación de enlaces (IEEE 802.1AX) agrupa varios enlaces paralelos punto a punto y dúplex completo entre dos dispositivos en un único enlace lógico (un LAG). LACP es el protocolo de control que ambos extremos usan para negociar el grupo; Cisco denomina EtherChannel a ese grupo.

**Funcionamiento:** STP ve el LAG como un solo enlace, así que los enlaces agrupados no se bloquean. Las tramas se asignan a uno de los enlaces miembros mediante el hash de valores como direcciones y puertos, por lo que **un flujo siempre utiliza el mismo enlace**. Cisco documenta la agrupación de hasta ocho puertos compatibles.

**En la práctica:** agrupar cuatro enlaces de 10 Gbps no permite que **una** conexión TCP supere los 10 Gbps; la capacidad agregada solo se aprovecha con muchos flujos. Responder a «una sola tarea de copia de seguridad es lenta» añadiendo miembros al LAG quizá no ayude. Los LAG de AWS Direct Connect también usan LACP para agrupar conexiones en el mismo punto de conexión (no se admite LAG multichasis); encontrarás más detalles en el [cuaderno de trabajo avanzado 07: WAN y conectividad híbrida](../networking/expert/07-wan-hybrid-connectivity.md#dx-lag).

### FHRP: VRRP y HSRP

**Definición:** un protocolo de redundancia de primer salto (FHRP) permite que varios routers compartan una **IP virtual y una MAC virtual**, para que los hosts puedan seguir funcionando si falla un router, sin cambiar la configuración de su puerta de enlace predeterminada.

**Por qué se necesita:** un host tiene una sola dirección de puerta de enlace predeterminada. Si ese router falla, el host no puede salir de su subred, aunque haya otro router en la misma subred.

**Funcionamiento de VRRPv3 (RFC 9568, que deja obsoleto RFC 5798):**

- Entre los routers con el mismo identificador de router virtual (VRID), uno se convierte en **Active** (Master en RFC 5798) y gestiona el tráfico enviado a la IP virtual. La MAC virtual IPv4 es `00-00-5E-00-01-{VRID}` y la IPv6 es `00-00-5E-00-02-{VRID}`.
- El router Active envía anuncios a la dirección de multidifusión IPv4 `224.0.0.18` mediante el número de protocolo IP 112. El intervalo predeterminado de anuncios es de 100 centésimas de segundo (1 s).
- El router que realmente posee la IP virtual tiene una prioridad de 255; la prioridad predeterminada de los routers de respaldo es 100. La prioridad 0 del router Active indica que ha dejado de participar en VRRP, así que un router de respaldo toma el control tras solo Skew_Time, en lugar de esperar todo el intervalo de caída. La opción Preempt está habilitada de forma predeterminada.
- Un router de respaldo se convierte en Active cuando no recibe anuncios durante `Active_Down_Interval = 3 × intervalo de anuncios + Skew_Time`, donde `Skew_Time = ((256 − prioridad) × intervalo de anuncios) / 256`. Con una prioridad de 100 y un intervalo de 1 s, Skew_Time es aproximadamente 0,61 s, así que la toma de control ocurre tras unos **3,61 s**.

**HSRP:** el FHRP de Cisco, publicado como RFC 2281 (Informativo). Los valores predeterminados son hello de 3 s y hold de 10 s, y la MAC virtual de la versión 1 es `0000.0c07.acXX` (XX es el número de grupo).

**En la práctica:** la MAC virtual se traslada al nuevo router Active, así que los vecinos y los switches deben aprender su nueva ubicación justo después de la conmutación por error (consulta ARP gratuito en [ARP en la parte 1](./06-network-fundamentals-part1.md#arp)). Mide el tiempo de conmutación por error como la suma de los temporizadores FHRP, la convergencia de STP y la convergencia del enrutamiento ascendente.

---

<a id="lan-topologies"></a>

## 4. Topologías de LAN: jerárquica y spine-leaf

### Campus: dos y tres niveles

**Definición:** tradicionalmente, las LAN de campus se dividen en las capas de acceso, distribución y núcleo.

| Capa | Función |
|---|---|
| Acceso | El borde de la red donde se conectan los hosts |
| Distribución | Agrega los switches de acceso y proporciona el límite L2/L3, la política de acceso y rutas redundantes |
| Núcleo | La red troncal que conecta todos los bloques, además del centro de datos y la WAN |

**Funcionamiento:** la guía de diseño de Cisco recomienda un diseño de **dos niveles (núcleo colapsado)**, que combina distribución y núcleo, para sitios pequeños como un solo edificio; además, describe el diseño de **tres niveles** como adecuado para sitios grandes con varios bloques de distribución, donde la separación facilita el aislamiento de fallas y el control de cambios.

### Centro de datos: spine-leaf

**Definición:** en una estructura spine-leaf (Clos), **cada leaf se conecta a cada spine** (una malla completa entre los dos niveles) y los servidores se conectan a los leaf. Este documento parte de una estructura básica de dos niveles en la que los leaf no se conectan entre sí y los spine tampoco; existen variantes, como el diseño multinivel de Cisco ACI, que cuelga un segundo nivel de leaf por debajo del primero.

**Funcionamiento:**

- Los enlaces entre leaf y spine son L3 y ECMP distribuye los flujos por todas las rutas de spine. STP no bloquea nada, así que todos los enlaces ascendentes transportan tráfico al mismo tiempo.
- Bajo ese supuesto, el tráfico dirigido a un servidor conectado a otro leaf siempre sigue la ruta **leaf → spine → leaf**: tres switches (dos enlaces entre switches). Todos los pares de servidores están a la misma distancia, lo que proporciona la latencia uniforme que Cisco cita como una ventaja de este diseño.
- Añade leaf para tener más puertos y spine para obtener más ancho de banda.

| Comparación | Tres niveles tradicional (L2 + STP) | Spine-leaf (L3 + ECMP) |
|---|---|---|
| Enlaces redundantes | STP bloquea algunos | ECMP los usa todos |
| Distancia entre servidores | Depende de su ubicación | Constante: leaf → spine → leaf |
| Extensión de L2 | Extiende ampliamente las VLAN | Superposición VXLAN/EVPN cuando se necesita |

**En la práctica:** cuando una VLAN debe extenderse por varios leaf en una estructura spine-leaf, ejecuta una superposición VXLAN/EVPN sobre la infraestructura subyacente L3. En el [cuaderno de trabajo avanzado 03: EVPN para centros de datos](../networking/expert/03-datacenter-evpn.md) se explica cómo demostrar los identificadores, las rutas y el plano de datos mediante pruebas.

---

<a id="nat-pat-cgnat"></a>

## 5. NAT, SNAT, PAT y CGNAT

La definición básica de NAT y el hecho de que «un dispositivo L3 toca los puertos L4» se explican en [NAT en la parte 1](./06-network-fundamentals-part1.md#nat). Esta sección aclara los términos, muestra cómo se llena realmente una tabla de traducción y explica cuándo se agotan sus recursos.

### Términos

| Término | Qué reescribe | Ejemplo |
|---|---|---|
| NAT básico (incluido el estático 1:1) | Solo la dirección IP | Una IP privada ↔ una IP pública; cómo una puerta de enlace de Internet de AWS gestiona IPv4 públicas |
| NAPT / PAT | Dirección IP + identificador de transporte (puerto TCP/UDP, ID de consulta ICMP) | Varios hosts internos comparten una IP pública |
| SNAT | Dirección de origen (y puerto) | Tráfico que sale a Internet |
| DNAT | Dirección de destino (y puerto) | Reenvío de puertos, un balanceador de carga que reenvía a un destino |

RFC 3022 define NAT básico y NAPT como «NAT tradicional». Las sesiones se inician desde la red privada hacia el exterior, y el primer paquete saliente crea la asignación. SNAT y DNAT provienen de los nombres de los destinos de netfilter de Linux; PAT suele implementarse como una forma de SNAT.

### Recorrido por una tabla de traducción PAT

El ejemplo usa direcciones privadas RFC 1918 para los hosts internos y rangos de documentación RFC 5737 (`203.0.113.0/24`, `198.51.100.0/24`) para la IP pública y el servidor. En la animación siguiente, los dos hosts internos usan deliberadamente **el mismo puerto de origen, 50000**. Con una sola IP pública, el dispositivo NAT los distingue mediante el **puerto** público.

![Animación de PAT. ① Host-A (10.0.1.10), en la red privada 10.0.1.0/24, envía un paquete desde 10.0.1.10:50000 hacia el servidor 198.51.100.20:443. ② El dispositivo NAT añade la fila de traducción 10.0.1.10:50000 → 203.0.113.10:30001 y envía el paquete con el origen 203.0.113.10:30001. ③ Host-B (10.0.1.20) también usa el puerto de origen 50000, así que NAT le asigna un puerto distinto en la misma IP pública y añade la fila 10.0.1.20:50000 → 203.0.113.10:30002. ④ La respuesta del servidor vuelve con destino 203.0.113.10:30002, y NAT busca en la tabla por puerto público y encuentra la fila 2. ⑤ NAT reescribe el destino de nuevo como 10.0.1.20:50000 y entrega el paquete a Host-B.](../.gitbook/assets/en-basics-06-network-fundamentals-part5-anim-1.svg)

Al regresar, NAT examina el **destino (IP pública:puerto)**. Si no encuentra ninguna fila coincidente —por ejemplo, porque la conexión se inició desde fuera o la asignación ya caducó—, el paquete no puede llegar a ningún host interno. Por eso, para acceder desde fuera a un servidor detrás de NAT se necesita una asignación estática independiente (DNAT).

### Agotamiento de puertos

**Funcionamiento:** el campo del puerto tiene 16 bits, así que una IP pública solo puede mantener un número limitado de conexiones simultáneas al mismo destino. AWS publica explícitamente el límite de su NAT gateway:

- Hasta **55 000** conexiones simultáneas **por cada dirección IPv4 pública y por cada destino único** (IP de destino, puerto de destino y protocolo)
- Hasta 8 direcciones IPv4 por NAT gateway (1 principal + 7 secundarias), es decir, hasta 440 000 conexiones al mismo destino; un NAT gateway público está limitado de forma predeterminada a 2 Elastic IP, así que se necesita solicitar un aumento de cuota
- Cuando no se puede asignar un puerto de origen, la métrica de CloudWatch `ErrorPortAllocation` pasa a ser mayor que cero
- Una conexión inactiva durante 350 s caduca; si se envían datos por ella después, el NAT gateway responde con un RST

**En la práctica:** cuando los Pod de cientos de nodos de Kubernetes llaman a **una sola API externa** (una IP:443), hay un único destino, así que ese límite se alcanza primero. Considera reutilizar las conexiones (keep-alive, grupos de conexiones), añadir IP secundarias, distribuir las subredes entre varios NAT gateway y sacar de la ruta NAT el tráfico hacia los servicios de AWS compatibles mediante VPC endpoints (consulta la explicación de la ruta de salida en la [parte 4](./06-network-fundamentals-part4.md)). Para conexiones que permanecen inactivas, configura TCP keepalive por debajo de 350 s.

### CGNAT y 100.64.0.0/10

**Definición:** CGNAT (NAT de nivel de operador) es una modalidad de NAT a gran escala en la que un operador agrupa a muchos suscriptores detrás de una sola dirección IPv4 pública. El tráfico suele traducirse primero en el router del suscriptor y luego en el CGN del operador.

**Funcionamiento:**

- RFC 6598 asigna **`100.64.0.0/10`, el espacio de direcciones compartidas**, al segmento entre el CGN y el equipo en las instalaciones del cliente (CPE). Es un espacio **separado** de los rangos privados de RFC 1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), así que no entra en conflicto con el rango RFC 1918 que use el suscriptor dentro de su red.
- Los paquetes y la información de enrutamiento de este rango no deben cruzar los límites del proveedor, y los proveedores deben filtrar los anuncios entrantes de ese rango.
- RFC 6888 exige que un CGN permita limitar los puertos externos por suscriptor y que, cuando se agoten los recursos, descarte el paquete nuevo en lugar de eliminar las asignaciones existentes. Para identificar a un suscriptor a partir de los registros se necesitan la dirección externa, el puerto externo y la marca de tiempo.

**En la práctica:**

- Los usuarios de redes móviles y algunos usuarios residenciales pueden compartir una IP pública. Bloquear o limitar la velocidad basándose solo en la IP puede afectar a usuarios que no tienen relación entre sí; para investigar incidentes se necesitan el **puerto y la hora exacta**, además de la IP.
- Una sucursal detrás de CGNAT no puede aceptar conexiones iniciadas desde fuera, así que diseña las VPN de sitio a sitio para que se inicien desde la sucursal.
- AWS permite asociar bloques CIDR de `100.64.0.0/10` a una VPC. Eso los convierte en una opción cuando escasea el espacio de direcciones privadas, pero primero comprueba que ninguna red local ni segmento de operador al que debas acceder use el mismo rango.

---

<a id="wan-types"></a>

## 6. Tipos de WAN

**Definición:** una WAN conecta sitios geográficamente separados (oficinas centrales, sucursales, centros de datos y nube). La mayor parte se contrata a operadores, así que la elección consiste en «¿qué servicio contratamos?».

| Tipo | Qué se contrata | Enrutamiento y direccionamiento | Ventajas | Consideraciones |
|---|---|---|---|---|
| Línea alquilada | Un circuito punto a punto de ancho de banda fijo entre dos sitios | Los routers de ambos extremos intercambian rutas directamente | Ancho de banda y latencia uniformes, sin compartir con otros clientes | Un circuito por cada par de sitios; costo elevado |
| MPLS L3VPN | Enrutamiento virtual dedicado al cliente dentro de la red MPLS del operador | Los routers PE del operador asocian las conexiones del cliente a VRF; se usa enrutamiento estático, RIP, OSPF o BGP entre CE y PE | Conectividad entre todos los sitios, SLA del operador | Dependencia del operador; más costosa que los circuitos de Internet |
| Internet de banda ancha | Acceso a Internet por fibra, cable o tecnologías similares | Dirección pública o CGNAT; sin control de la ruta | Bajo costo por unidad de ancho de banda | Calidad de mejor esfuerzo; la confidencialidad se obtiene mediante una superposición propia, como IPsec |
| LTE/5G | Acceso a datos móviles | Normalmente detrás del NAT del operador; difícil recibir conexiones entrantes | Rápida puesta en marcha sin cableado, buena como respaldo | Latencia y ancho de banda variables; modelo tarifario |
| SD-WAN | Una superposición gestionada sobre los circuitos anteriores | La política por flujo de aplicación elige la ruta del túnel | Combina circuitos y permite seleccionar rutas por aplicación | Siguen vigentes las limitaciones de calidad de la infraestructura subyacente |

**Funcionamiento:**

- En **MPLS L3VPN** (RFC 4364), los routers PE del operador mantienen tablas de enrutamiento llamadas VRF, además de la tabla de reenvío predeterminada, y asocian cada circuito de conexión del cliente a una VRF. Las rutas de clientes transportadas por BGP reciben el prefijo de un Route Distinguisher de 8 bytes, que las convierte en direcciones VPN-IPv4; así, dos clientes que usan el mismo rango privado no se mezclan. CE y PE intercambian rutas mediante enrutamiento estático, RIP, OSPF o BGP.
- **SD-WAN** es un modelo de servicio, no un tipo de circuito. MEF 70.2 define el servicio SD-WAN por separado de los servicios de conectividad subyacentes (acceso a Internet, MPLS, etc.), define los túneles entre sitios como Tunnel Virtual Connections (TVC) y define como Policy las reglas de ruta por flujo de aplicación.
- Los puntos de entrada de la WAN a la nube son AWS Site-to-Site VPN y Direct Connect (consulta la correspondencia con la nube en la [parte 4](./06-network-fundamentals-part4.md)). El diseño de redundancia, la selección de rutas BGP, la MTU del túnel y la comparación de costos se tratan en el [cuaderno de trabajo avanzado 07: WAN y conectividad híbrida](../networking/expert/07-wan-hybrid-connectivity.md).

**En la práctica:** al elegir una WAN, registra más que el ancho de banda: la latencia y la fluctuación de latencia, cómo funciona la conmutación por error y si los circuitos llegan desde distintos operadores por rutas diferentes (diversidad física). Si dos circuitos comparten el mismo conducto, una sola retroexcavadora puede dejar fuera de servicio a ambos.

---

## 7. En la nube

La [parte 4](./06-network-fundamentals-part4.md) comparó en términos generales los conceptos tradicionales con AWS. Esta tabla se limita a los **dispositivos y las decisiones** tratados aquí e indica qué se mantiene igual y qué cambia.

| Dispositivo o función tradicional | Equivalente en AWS | Diferencias |
|---|---|---|
| Puerta de enlace predeterminada de la subred (router, SVI) | Router de VPC y tablas de rutas de VPC | AWS reserva para el router de VPC la dirección de red de la subred + 1; las tablas de rutas incluyen automáticamente una ruta `local` para el CIDR de la VPC |
| FHRP (VRRP, HSRP) | No se configura por cuenta propia | La dirección de puerta de enlace corresponde al router de VPC y las VPC no admiten difusión, así que no hay traspaso L2 de una IP y MAC virtuales; la redundancia se diseña con varias AZ y comprobaciones de estado del balanceador de carga |
| Router de borde de Internet + NAT estático 1:1 | Internet gateway (IGW) | Componente de VPC redundante y escalado horizontal que proporciona, desde un punto de vista lógico, NAT 1:1 a las instancias con direcciones IPv4 públicas |
| Dispositivo PAT | NAT gateway | 55 000 conexiones simultáneas por IP y por destino, hasta 8 IP, escalado automático de 5 Gbps a 100 Gbps, sin asociación de grupo de seguridad, tiempo de espera por inactividad de 350 s |
| Router central, hub WAN | Transit Gateway | Router virtual regional; cada conexión se asocia a una tabla de rutas y puede propagar rutas a varias |
| Firewall con estado | Grupo de seguridad | Con estado; solo reglas de permiso, se evalúan todas las reglas; nivel de instancia (interfaz de red) |
| ACL sin estado en una interfaz de router | Network ACL | Sin estado; las reglas de permiso y denegación se evalúan en orden ascendente por número y se aplica la primera coincidencia; nivel de subred; el tráfico de respuesta en puertos efímeros debe permitirse explícitamente |

**Cómo puede causar una interrupción la diferencia entre un grupo de seguridad y una NACL:** una NACL no permite automáticamente el tráfico de respuesta. Cuando una instancia de la subred actúa como cliente, la respuesta vuelve a un **puerto efímero** elegido por el sistema operativo de esa instancia, así que la NACL de entrada debe permitir ese rango. Según la documentación de AWS, muchos kernels de Linux usan 32768–61000, Windows Server 2008 y versiones posteriores usan 49152–65535, y NAT gateway, ELB y Lambda usan 1024–65535. Si solo se usan grupos de seguridad, las respuestas se permiten automáticamente y este problema no se presenta.

---

## Conclusión

En última instancia, los dispositivos son máquinas que consultan una tabla para tomar una decisión: un switch lee su tabla MAC, un router consulta su FIB, un firewall consulta su tabla de estado, un balanceador de carga consulta sus reglas del listener y un dispositivo NAT consulta su tabla de traducción. La redundancia implica una compensación propia en cada nivel: bucles en L2 (STP), distribución por flujo en enlaces agrupados (LACP) y traspaso de la propiedad de una dirección virtual en la puerta de enlace (FHRP).

Al investigar una falla, comprueba «qué había en la tabla del último dispositivo que procesó correctamente el paquete». Las pruebas directas de la tabla —por ejemplo, dónde se aprendió una MAC, el resultado de una búsqueda de ruta, una entrada en la tabla de estado o NAT, o el valor de `ErrorPortAllocation` de un NAT gateway— son más útiles que las conjeturas.

---

## Documentos siguientes

- [Cuaderno de trabajo avanzado 03: EVPN para centros de datos](../networking/expert/03-datacenter-evpn.md): superposiciones VXLAN/EVPN en spine-leaf
- [Itinerario de estudio avanzado de redes](../networking/expert/README.md): mapa completo de cuadernos de trabajo, incluidos WAN y conectividad híbrida, CDN y edge
- [Itinerario de aprendizaje de redes](../networking/README.md#learning-path): desde los contenedores y los Service hasta las implementaciones de CNI
- [Parte 4: El recorrido de una solicitud y la nube](./06-network-fundamentals-part4.md): correspondencia completa con AWS y Kubernetes

## Referencias

Estándares y RFC

- [IEEE 802.1Q-2022: Bridges and Bridged Networks](https://standards.ieee.org/ieee/802.1Q/10323/)
- [IEEE 802.1AX: Link Aggregation](https://1.ieee802.org/tsn/802-1ax-rev/)
- [RFC 9568: VRRP Version 3 for IPv4 and IPv6](https://www.rfc-editor.org/rfc/rfc9568.html) (deja obsoleto RFC 5798), [RFC 5798](https://www.rfc-editor.org/rfc/rfc5798.html)
- [RFC 2281: Cisco Hot Standby Router Protocol (HSRP)](https://www.rfc-editor.org/rfc/rfc2281.html)
- [RFC 3022: Traditional IP Network Address Translator](https://www.rfc-editor.org/rfc/rfc3022.html)
- [RFC 6598: IANA-Reserved IPv4 Prefix for Shared Address Space](https://www.rfc-editor.org/rfc/rfc6598.html)
- [RFC 6888: Common Requirements for Carrier-Grade NATs](https://www.rfc-editor.org/rfc/rfc6888.html)
- [RFC 1918: Address Allocation for Private Internets](https://www.rfc-editor.org/rfc/rfc1918.html)
- [RFC 1812: Requirements for IP Version 4 Routers](https://www.rfc-editor.org/rfc/rfc1812.html)
- [RFC 4364: BGP/MPLS IP Virtual Private Networks](https://www.rfc-editor.org/rfc/rfc4364.html)
- [RFC 5737: IPv4 Address Blocks Reserved for Documentation](https://www.rfc-editor.org/rfc/rfc5737.html)
- [NIST SP 800-41 Rev. 1: Guidelines on Firewalls and Firewall Policy](https://csrc.nist.gov/pubs/sp/800/41/r1/final)
- [MEF 70.2: SD-WAN Service Attributes and Service Framework](https://www.mplify.net/resources/mef-70-2-sd-wan-service-attributes-and-service-framework/) ([PDF](https://www.mplify.net/wp-content/uploads/MEF-70.2.pdf))

Documentación de proveedores

- [Cisco: Inter-Switch Link and IEEE 802.1Q Frame Format](https://www.cisco.com/c/en/us/support/docs/lan-switching/8021q/17056-741-4.html)
- [Cisco Catalyst 9300: Configuring VLAN Trunks](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-12/configuration_guide/vlan/b_1712_vlan_9300_cg/configuring_vlan_trunks.html)
- [Cisco: Configure InterVLAN Routing with Catalyst Switches](https://www.cisco.com/c/en/us/support/docs/lan-switching/inter-vlan-routing/41260-189.html)
- [Cisco: Understand Rapid Spanning Tree Protocol (802.1w)](https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/24062-146.html)
- [Cisco: Understand and Tune Spanning Tree Protocol Timers](https://www.cisco.com/c/en/us/support/docs/lan-switching/spanning-tree-protocol/19120-122.html)
- [Cisco Meraki: Determining the RSTP/STP Root Bridge](https://documentation.meraki.com/MS/Port_and_VLAN_Configuration/Determining_the_RSTP%2F%2F%2F%2FSTP_Root_Bridge_on_an_MS_Switch_network)
- [Cisco: Understand EtherChannel Load Balance and Redundancy](https://www.cisco.com/c/en/us/support/docs/lan-switching/etherchannel/12023-4.html)
- [Cisco: Medium Enterprise Design Profile, LAN Design](https://www.cisco.com/en/US/docs/solutions/Enterprise/Medium_Enterprise_Design_Profile%28MEDP%29/chap2.html)
- [Cisco: Massively Scalable Data Center Network Fabric White Paper](https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/white-paper-c11-743245.html), [Cisco ACI Multi-tier Architecture White Paper](https://www.cisco.com/c/en/us/solutions/collateral/data-center-virtualization/application-centric-infrastructure/white-paper-c11-742214.html)
- [Linux ip-link(8)](https://man7.org/linux/man-pages/man8/ip-link.8.html), [bridge(8)](https://man7.org/linux/man-pages/man8/bridge.8.html), [iptables-extensions(8): destinos SNAT y DNAT](https://man7.org/linux/man-pages/man8/iptables-extensions.8.html)

Documentación de AWS

- [Conceptos básicos de NAT gateway](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-basics.html), [Solución de problemas de NAT gateway](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-troubleshooting.html), [Métricas de CloudWatch de NAT gateway](https://docs.aws.amazon.com/vpc/latest/userguide/metrics-dimensions-nat-gateway.html)
- [Internet gateways](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html)
- [Cómo funciona AWS Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/how-transit-gateways-work.html)
- [Comparación entre grupos de seguridad y ACL de red](https://docs.aws.amazon.com/vpc/latest/userguide/infrastructure-security.html#VPC_Security_Comparison), [ACL de red personalizadas y puertos efímeros](https://docs.aws.amazon.com/vpc/latest/userguide/custom-network-acl.html)
- [Bloques CIDR de VPC](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html), [Dimensionamiento de subredes (direcciones reservadas)](https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html)
- [Cómo funciona Elastic Load Balancing](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/how-elastic-load-balancing-works.html)
- [Grupos de agregación de enlaces de Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/lags.html)
