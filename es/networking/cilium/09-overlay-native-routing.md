# Parte 9: Análisis profundo del enrutamiento overlay y nativo

> **Base de revisión**: Cilium 1.20.2 (estable, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Los elementos marcados **[1.21 pre-release]** corresponden a v1.21.0-pre.3 y pueden cambiar antes de la versión GA.
> **Última actualización**: 15 de octubre de 2026

Este capítulo profundiza en el selector de modo descrito en [Modelos de red y VXLAN](03-networking.md). Explica qué ocurre con un paquete entre Pods de nodos distintos en modo túnel y en modo de enrutamiento nativo; qué programa BPF realiza cada tarea; cómo viaja la identidad de seguridad dentro de la encapsulación; cómo se deciden la MTU y el masquerade; y qué combinaciones hacen que el agente se niegue a iniciar. También ubica el reemplazo de kube-proxy, DSR, Maglev, socket-LB, el enrutamiento del host, netkit, el administrador de ancho de banda y el cifrado dentro del mismo datapath, y termina con una guía de decisiones para EKS y un procedimiento de solución de problemas.

Capítulos relacionados: [Internals del datapath eBPF](08-ebpf-datapath-internals.md) (puntos de conexión de programas y mapas), [Análisis profundo de IPAM](10-ipam-deep-dive.md) (origen de los CIDR de Pods), [BGP, balanceo de carga, egreso y edge](11-bgp-lb-egress-edge.md) (anuncio de CIDR de Pods y LB externo), [mTLS, cifrado e identidad](12-mtls-encryption-identity.md) (detalles de WireGuard/IPsec), [ClusterMesh, instalación y actualización](13-clustermesh-install-upgrade.md).

## Tabla de contenido

1. Matriz de modos de enrutamiento
2. VXLAN frente a Geneve en Cilium
3. Cómo viaja la identidad en el VNI
4. Plano de control: de CiliumNode al extremo del túnel
5. Recorridos de paquetes: mismo nodo, túnel y modo nativo
6. Enrutamiento nativo: quién proporciona las rutas
7. Validaciones de inicio: fallos definitivos y alternativas silenciosas
8. Cálculo de MTU
9. Masquerade
10. Enrutamiento del host: heredado frente a BPF
11. Dispositivo del datapath: veth frente a netkit
12. Balanceo de carga de servicios en el datapath
13. Administrador de ancho de banda, BBR y BIG TCP
14. Interacción con el cifrado
15. VTEP y multicast (beta)
16. Guía de decisiones para EKS
17. Hoja rápida de inspección
18. Laboratorios
19. Diferencias entre versiones
20. Solución de problemas
21. Límites de validación y fuentes

---

## 1. Matriz de modos de enrutamiento

En 1.20, `routingMode` acepta exactamente dos valores: `tunnel` (predeterminado) y `native`. Todo lo demás de este capítulo se deriva de esa elección y de algunas funciones que solicitan por sí mismas un dispositivo de túnel.

| Situación | Helm | Pod a Pod, en nodos diferentes | Quién debe enrutar los CIDR de Pods |
|---|---|---|---|
| Túnel (predeterminado) | `routingMode: tunnel`, `tunnelProtocol: vxlan` (predeterminado) o `geneve` | BPF establece los metadatos del túnel; el kernel encapsula en UDP mediante `cilium_vxlan`/`cilium_geneve` | Nadie; la red subyacente solo necesita conectividad IP entre nodos y UDP 8472/6081 |
| Nativo | `routingMode: native` | El paquete sale con la IP del Pod y el kernel lo enruta (o BPF lo redirige mediante FIB con enrutamiento de host BPF) | La red: router de nube/ENI, `autoDirectNodeRoutes`, BGP o rutas estáticas |
| Nativo + túnel activado por una función | `routingMode: native` y Egress Gateway o DSR con `dsrDispatch: geneve` | El tráfico normal de Pods usa enrutamiento nativo; la función crea un dispositivo de túnel para sus propios paquetes | Igual que en modo nativo; el túnel solo transporta el tráfico de esa función |

La tercera fila importa al inspeccionar `ip link`: un dispositivo `cilium_geneve` en un clúster con enrutamiento nativo no indica una configuración errónea. En el código, Egress Gateway y DSR con Geneve son «activadores de túnel» que solicitan el dispositivo incluso con `routingMode: native` (consulta el paquete `tunnel` del agente, `pkg/datapath/tunnel/tunnel.go`).

Madurez según la documentación de 1.20.2: los modos de túnel VXLAN/Geneve y el enrutamiento nativo son estables. BGP anuncia rutas; no es un modo de reenvío. Consulta [BGP, balanceo de carga, egreso y edge](11-bgp-lb-egress-edge.md).

> **Aspecto para vigilar en 1.21.** El árbol v1.21.0-pre.3 contiene código preliminar e inconcluso para otro modo de enrutamiento que no está expuesto en el chart de Helm. Este capítulo no lo nombra ni lo describe. Antes de asumir que `routingMode` sigue teniendo dos valores, vuelve a leer la documentación de enrutamiento de la versión GA 1.21.

## 2. VXLAN frente a Geneve en Cilium

Ambos encapsulan sobre UDP. Cilium usa un **dispositivo de red del kernel basado en flujo (collect-metadata)** en los dos casos; el controlador del kernel construye los encabezados externos a partir de metadatos por paquete que adjunta BPF. Cilium no construye los encabezados externos en BPF.

| Propiedad | VXLAN | Geneve |
|---|---|---|
| Valor de Helm | `tunnelProtocol: vxlan` (predeterminado) | `tunnelProtocol: geneve` |
| Puerto UDP de destino predeterminado | 8472 | 6081 |
| Dispositivo | `cilium_vxlan` | `cilium_geneve` |
| Transporte de la identidad | VNI (24 bits) | VNI (24 bits); mismo mecanismo |
| Opciones/TLV que usa Cilium | ninguna | solo la opción de dirección/puerto de servicio DSR (clase `0x014B`, tipo `0x81`) |
| Compatibilidad con DSR | no es posible; el agente rechaza `dsr`/`hybrid` con túneles VXLAN | `dsrDispatch: geneve` |
| Configuración del kernel | `CONFIG_VXLAN` | `CONFIG_GENEVE` |

Ambos requieren también `CONFIG_FIB_RULES`. El puerto 8472 es el puerto VXLAN histórico predeterminado del kernel Linux, no el 4789 asignado por IANA; Cilium conserva 8472 por compatibilidad. Puedes cambiarlo con `tunnelPort`, pero ten en cuenta que hacerlo recrea el dispositivo y causa una breve interrupción, mientras que un cambio de MTU modifica el dispositivo en el lugar.

Parámetros relacionados:

- `tunnelSourcePortRange: "0-0"` (predeterminado) deja que el controlador del kernel elija el rango de puertos UDP de origen externo. Un rango más estrecho reduce la entropía que observan ECMP y los filtros de la red subyacente; no afecta a la identidad.
- `underlayProtocol: auto|ipv4|ipv6` (añadido en 1.18). `auto` prefiere IPv4 si está habilitado y, de lo contrario, IPv6. Una red subyacente IPv6 eleva la sobrecarga del túnel a 70 bytes e impide la aceleración XDP; Egress Gateway requiere una red subyacente IPv4.
- Al cambiar `tunnelProtocol`, se elimina el otro dispositivo y se crea uno nuevo; planifica el cambio como una operación disruptiva, nodo por nodo.

Requisito de grupo de seguridad/firewall: UDP 8472 (VXLAN) o UDP 6081 (Geneve) entre **todos** los nodos, además de TCP 4240 para comprobaciones de estado e ICMP echo. En AWS, exprésalo con referencias entre grupos de seguridad (el SG del nodo hace referencia a sí mismo); nunca abras un CIDR a Internet. WireGuard necesita UDP 51871; IPsec necesita ESP (protocolo IP 50), que los grupos de seguridad de AWS no permiten de forma predeterminada.

```yaml
# values: Geneve overlay (needed if you later want DSR dispatch via Geneve)
routingMode: tunnel
tunnelProtocol: geneve
```

## 3. Cómo viaja la identidad en el VNI

El ID de túnel de 24 bits (VNI) de cada paquete encapsulado por Cilium es la **identidad de seguridad de origen** del endpoint emisor. Esto se aplica a VXLAN y Geneve. Geneve no usa sus opciones para transportar la identidad.

Reglas en `bpf/lib/identity.h`, `bpf/lib/encap.h` y `bpf/bpf_overlay.c` (v1.20.2):

- En clústeres de doble pila, las identidades reservadas `world-ipv4` (9) y `world-ipv6` (10) se envían como `world` (2); el receptor recupera la identidad correcta a partir del protocolo L3 interno.
- La identidad `host` (1) nunca se envía. Antes de encapsular, el emisor la reescribe como `local-node`/`remote-node` (6). Si un paquete llega por el túnel indicando `host`, se descarta con `DROP_INVALID_IDENTITY`.
- El receptor sigue teniendo ipcache. Upstream describe el transporte de la identidad como una optimización que evita una consulta de identidad en el nodo remoto, no como la única fuente de verdad. Para el tráfico de nodos remotos, `bpf_overlay.c` refina la identidad mediante ipcache.

Consecuencias prácticas:

1. En el cable, el VNI coincide con el número de identidad que aparece en `cilium-dbg endpoint list` (columna IDENTITY) o `cilium-dbg identity list`. El laboratorio 1 lo comprueba.
2. Como la decisión de política de ingreso se toma en el nodo de destino con la identidad transportada, no es necesario volver a resolver la IP de origen para encontrar el Pod.
3. La integración VTEP (sección 15) depende de esto: el tráfico desde VTEP externos debe llevar VNI 2 (`world`).

DSR sobre Geneve es el único caso que usa opciones: el nodo de balanceo inserta una opción Geneve con la dirección y el puerto originales del servicio para que el nodo backend pueda reescribir las respuestas. Esto añade 12 bytes, que el datapath tiene en cuenta (consulta la sección 8).

## 4. Plano de control: de CiliumNode al extremo del túnel

En modo túnel, el emisor necesita conocer, para cualquier IP de Pod de destino, (a) su identidad de seguridad y (b) la IP del nodo que lo aloja (el extremo del túnel). Ambas se almacenan en un mapa LPM BPF:

```text
 Kubernetes API                       cilium-agent                       BPF
 --------------                       ------------                       ---
 CiliumNode (remote node IPs,   -->   node manager: node discovery
              podCIDRs)                 |- kernel route per remote PodCIDR
 CiliumEndpoint(Slice)/identity -->   ipcache listener                 cilium_ipcache_v2
   (Pod IP -> identity)                   writes {identity,   ------>  key: prefix
                                                  tunnel_endpoint,       value: identity,
                                                  encrypt key,                  tunnel endpoint,
                                                  flags}                        flags (skip_tunnel...)
```
- Para cada PodCIDR remoto, el agente también instala una ruta del kernel a través de `cilium_host` (`<podCIDR> via <cilium_host IP> dev cilium_host src <cilium_host IP> mtu <route MTU>`). La decisión de encapsulación BPF usa ipcache; la ruta sirve de alternativa para el tráfico originado por el host.
- `cilium_ipcache_v2` es un mapa LPM. El valor contiene la identidad, el extremo del túnel (dirección IPv4 o IPv6 de un nodo remoto), el índice de clave de cifrado y marcas como `skip_tunnel`. El listener solo define el extremo del túnel cuando la IP del host difiere de la IP del nodo local.
- Para cada PodCIDR remoto, el agente también instala una ruta del kernel a través de `cilium_host` (`<podCIDR> via <cilium_host IP> dev cilium_host src <cilium_host IP> mtu <route MTU>`). La decisión de encapsulación BPF usa ipcache; la ruta sirve de alternativa para el tráfico originado por el host.
- **`cilium_tunnel_map` ya no existe.** Todavía estaba en BPF en 1.17 (`bpf/lib/encap.h`) y `cilium-dbg bpf tunnel list` lo mostraba. Se eliminó del datapath en 1.18 (el árbol BPF de 1.18.14 no lo referencia; el agente solo quita el pin de un mapa sobrante) y el paquete Go se eliminó en 1.19. Los extremos del túnel están en el valor de ipcache: inspecciónalos con `cilium-dbg bpf ipcache list` (columna del extremo del túnel), `cilium-dbg bpf nodeid list` y `cilium-dbg node list`.

## 5. Recorridos de paquetes: mismo nodo, túnel y modo nativo

Los nombres de los programas provienen de `bpf/bpf_lxc.c`, `bpf/bpf_overlay.c` y `bpf/lib/local_delivery.h` (v1.20.2). Consulta [Internals del datapath eBPF](08-ebpf-datapath-internals.md) para conocer cómo se conectan.

### 5.1 Pod A (nodo 1) a Pod B (nodo 2), modo túnel

```text
 node 1                                                          node 2
 ------                                                          ------
 Pod A eth0
   |  (veth/netkit peer on host)
   v
 [bpf_lxc: cil_from_container]
   1. service DNAT (socket-LB at connect(), or lb4_local per packet)
   2. conntrack lookup (cilium_ct4_global)
   3. ipcache lookup of dst -> dst identity + tunnel endpoint (node 2)
   4. egress policy (per-endpoint policy map, by identity)
   5. dst not local -> TUNNEL_MODE branch:
        set tunnel key { id = src identity, remote = node 2 IP }
        (bpf_skb_set_tunnel_key), redirect to ifindex of cilium_vxlan
   v
 [cilium_vxlan  (flow-based netdev)]
   cil_to_overlay on its egress: identity mark, SNAT handling,
   EDT bandwidth (if bandwidth manager is on)
   kernel vxlan driver builds outer Eth/IP/UDP(8472)/VXLAN(VNI)
   v
 NIC  ==== underlay IP network, UDP 8472 ====>  NIC
                                                  |
                                                  v
                                       kernel vxlan driver decapsulates
                                                  v
                                       [cilium_vxlan ingress: cil_from_overlay]
                                         validate ethertype, read tunnel key
                                         -> src_sec_identity
                                         tail call IPV4_FROM_OVERLAY (handle_ipv4):
                                           VTEP source check (must be world)
                                           remote-node identity refinement (ipcache)
                                           lookup destination endpoint
                                           ipv4_local_delivery(from_tunnel=true)
                                         tail call cilium_call_policy:
                                           ingress policy of Pod B using the carried identity
                                         redirect into Pod B's netns (redirect_peer with veth
                                           when BPF host routing is active)
                                                  v
                                                Pod B eth0
```

Puntos clave:

- **El kernel encapsula; BPF dirige.** BPF establece la clave de túnel (`BPF_F_ZERO_CSUM_TX`, TTL 64) y redirige al dispositivo de túnel. Esto corrige una simplificación habitual: «eBPF encapsula el paquete directamente».
- El cifrado se aplica **después** de la encapsulación (IPsec desde 1.18; WireGuard usa otro dispositivo); cuando está habilitado, la NIC física ve ESP o WireGuard, no VXLAN.
- Las respuestas vuelven de forma simétrica usando la entrada conntrack; el nodo de destino encapsula con la identidad del Pod B como VNI.
- El tráfico de Pod dirigido a una dirección de un **nodo remoto** no atraviesa el túnel. En modo túnel pasa por masquerade (sección 9).

### 5.2 Mismo nodo

`__lookup_ip4_endpoint` encuentra el endpoint local de destino; `ipv4_local_delivery` hace una tail call a `cilium_call_policy` (política de ingreso del destino) y entrega el paquete mediante `bpf_redirect_peer` (veth con enrutamiento de host BPF) o `bpf_redirect`. Con netkit, el tráfico Pod a Pod usa un `redirect` simple de egress a ingress. No hay encapsulación.

### 5.3 Pod A a Pod B, enrutamiento nativo

Los pasos 1-4 son idénticos. En el paso 5 no se usa el túnel:

- Con **enrutamiento de host BPF** (predeterminado cuando están activos KPR y masquerade BPF), `fib_redirect_v4` consulta la FIB y redirige directamente hacia fuera de la NIC (al estilo `bpf_redirect_neigh`), sin pasar por netfilter ni por la pila superior.
- Con **enrutamiento de host heredado**, el programa devuelve `CTX_ACT_OK` (pasa el paquete a la pila) y el kernel Linux lo enruta usando las rutas disponibles: AWS ENI/rutas por endpoint, `autoDirectNodeRoutes`, rutas aprendidas por BGP o un router de nube.

La red externa ve las IP originales de los Pods; por eso debe poder enrutar esas direcciones y los controles contra suplantación (por ejemplo, la comprobación de origen/destino de EC2 en instancias que no usan ENI) y los grupos de seguridad deben permitirlas. Si las IP de Pod usan ENI, la VPC es propietaria de esas direcciones.

## 6. Enrutamiento nativo: quién proporciona las rutas

`routing-mode: native` entrega los paquetes no locales al kernel y Cilium habilita el reenvío IP. Cilium no anuncia a la red dónde están los CIDR de Pods; una de estas opciones debe hacerlo:

| Proveedor de rutas | Helm | Notas |
|---|---|---|
| Red de nube | `eni.enabled` (AWS), `gke.enabled`, IPAM de Azure | Las IP de Pods son nativas de la red de nube; el chart configura las rutas por endpoint (`enable-endpoint-routes`) |
| Rutas directas a nodos | `autoDirectNodeRoutes: true` | Instala `<remote podCIDR> via <remote node IP>`; todos los nodos deben compartir el mismo segmento L2 |
| BGP | Plano de control BGP de Cilium o daemon externo | Consulta el [capítulo 11](11-bgp-lb-egress-edge.md) |
| Rutas estáticas | ninguna | Las administra el operador |

`directRoutingSkipUnreachable` (predeterminado false) omite la instalación de rutas directas a nodos que no son de enlace directo; **requiere** `autoDirectNodeRoutes` o el agente termina. No es una alternativa al túnel.

Protección de Helm: con enrutamiento nativo y `enableIPv4Masquerade` configurado con un valor verdadero, `helm template` falla con «ipv4NativeRoutingCIDR must be set when routingMode is native» salvo que se cumpla una de estas condiciones: `ipam.mode` es `eni` o `alibabacloud`, ip-masq-agent está habilitado o `nativeRoutingCIDRFromClusterPool: true` (nuevo en 1.20; requiere `ipam.mode=cluster-pool` con exactamente un CIDR de pool). El valor predeterminado del chart para `enableIPv4Masquerade` es null (el valor predeterminado del agente es true), por lo que dejarlo sin configurar no activa la protección, aunque el agente aplique masquerade. La protección IPv6 funciona igual con `ipv6.enabled`, `enableIPv6Masquerade` (predeterminado true en el chart) y `ipv6NativeRoutingCIDR`.

```yaml
# values: native routing in a single L2 segment
routingMode: native
autoDirectNodeRoutes: true
ipv4NativeRoutingCIDR: 10.244.0.0/16   # must cover all Pod CIDRs
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.244.0.0/16"]
```

Semántica del CIDR de enrutamiento nativo: los destinos dentro de este rango no pasan por masquerade y se entregan a la pila. Si no lo defines, el valor predeterminado es el PodCIDR del nodo local. Para ENI/Azure/AlibabaCloud, el operador lo obtiene de la nube (solo el CIDR principal de la VPC); si especificas uno, debe estar contenido en un CIDR de VPC o el agente falla con «None of the VPC CIDRs contains the specified native routing CIDR».

### Datapath de AWS ENI (cómo enruta)

Con ENI IPAM, la IP del Pod es una IP secundaria o un prefijo de una ENI. El agente instala rutas por endpoint y dos reglas ip rule por IP de Pod: una regla de ingreso `to <podIP> lookup main` (prioridad 20, `RulePriorityIngress`) y otra de egreso `from <podIP> lookup <ENI table>` (prioridad 111, `RulePriorityEgressv2`; la prioridad antigua 110 solo se usa en modo IPAM de Azure). El selector `to <VPC CIDR>` se añade a la regla de egreso (una regla por CIDR de VPC) solo si masquerade está activo; ENI lo tiene desactivado de forma predeterminada, así que normalmente la regla de egreso no lleva selector `to`. La tabla ENI contiene una ruta predeterminada a través del router de la subred ENI. La IP del router se obtiene del espacio de direcciones de ENI para poder generar mensajes ICMP packet-too-big. Desde 1.18, el operador necesita `ec2:DescribeRouteTables`. Para los detalles de direccionamiento, consulta [Análisis profundo de IPAM](10-ipam-deep-dive.md).

## 7. Validaciones de inicio: fallos definitivos y alternativas silenciosas

Los operadores pierden tiempo porque algunas combinaciones incorrectas detienen el agente y otras solo generan una línea de registro y ejecutan un datapath más limitado. Conviene saber cuáles son cuáles.

### Fallos definitivos (el agente termina o falla el renderizado de Helm)

| Configuración | Resultado |
|---|---|
| `routingMode: tunnel` + `autoDirectNodeRoutes: true` | Fatal: «auto-direct-node-routes cannot be used with tunneling. Packets must be routed through the tunnel device.» (1.20.2) |
| `ipam: eni` + túnel | Fatal: «Cannot specify IPAM mode eni in tunnel mode.» |
| `directRoutingSkipUnreachable` sin `autoDirectNodeRoutes` | Fatal |
| Modo DSR o hybrid + túnel VXLAN | Error: el modo Node Port `dsr` no se puede usar con túnel `vxlan` |
| Túnel + DSR/hybrid sin `dsrDispatch: geneve` | Error: requiere dispatch `geneve` |
| `dsrDispatch: geneve` sin `tunnelProtocol: geneve` | Error: requiere protocolo de túnel Geneve |
| Aceleración XDP + red subyacente IPv6 | Error |
| Enrutamiento nativo + `enableIPv4Masquerade` verdadero + sin CIDR nativo ni excepción | Error al generar la plantilla Helm (un valor sin definir, cuyo predeterminado en el chart es null, no falla) |
| `bpf.datapathMode: netkit` explícito con requisitos incumplidos | Falla de forma definitiva (sección 11) |
| BBR sin `skb_set_tstamp` de kernel 5.18, o BBR para Pods sin enrutamiento de host BPF | Error del agente (sección 13) |
| BIG TCP sin enrutamiento de host BPF / KPR / masquerade BPF, o junto con IPsec o DSR IPIP | Error al iniciar |
| `enable-remote-node-masquerade` sin masquerade BPF | Error |
| `ip-masq-agent` sin masquerade BPF | Error |

Con VXLAN y el modo de anotación por servicio (`bpf.lbModeAnnotation=true`), el validador solo acepta `dsrDispatch: ipip`; el modo global predeterminado debe seguir siendo `snat`.

**[1.21 pre-release]** El mensaje de `autoDirectNodeRoutes` dice «auto-direct-node-routes requires native routing mode». La condición sigue siendo que el túnel esté habilitado.

### Alternativas silenciosas (el agente sigue ejecutándose con un datapath más limitado)

| Configuración | Qué ocurre |
|---|---|
| Enrutamiento de host BPF (predeterminado), pero masquerade de iptables o KPR desactivado | Registra «BPF host routing requires bpf-masquerade / kube-proxy-replacement ... Falling back to legacy host routing»; usa enrutamiento heredado |
| `bpf.datapathMode: auto` sin los requisitos de netkit | Registra «datapath autodiscovery failed, reverting from netkit to veth»; usa veth |
| Administrador de ancho de banda + IPsec | Se deshabilita el administrador con una advertencia |
| BIG TCP en un kernel no compatible | Emite una advertencia y lo deshabilita |
| Multicast habilitado sin el helper BPF necesario en el kernel | Registra «Disabled support for BPF Multicast» y lo mantiene deshabilitado |
| Encadenamiento CNI | El chart fuerza el enrutamiento de host heredado y deshabilita las reglas iptables sin conntrack |

La asimetría es deliberada en el código: el enrutamiento del host y `auto` son de «mejor esfuerzo», mientras que las funciones solicitadas explícitamente (netkit, BBR, BIG TCP) fallan si no pueden habilitarse. Después de cualquier cambio, comprueba el estado efectivo (sección 17) en vez de confiar solo en los valores configurados.

## 8. Cálculo de MTU

**Detección.** La MTU base es la MTU mínima entre los dispositivos nativos seleccionados por Cilium, excluidos `cilium_vxlan`, `cilium_geneve`, los dispositivos IPIP y los dispositivos dummy. `MTU: 0` (predeterminado) significa «detectar»; un valor Helm `MTU` distinto de cero es la **MTU de la red subyacente**, no la MTU final del Pod. Una MTU en la configuración CNI también la sobrescribe. La detección local no demuestra cuál es la MTU de ruta entre los routers.

**MTU del dispositivo del Pod y de la ruta.** La MTU del dispositivo veth/netkit del Pod es igual a la MTU base; la MTU de ruta dentro del Pod es la base menos la sobrecarga. Por eso, `ip link` en un Pod puede mostrar 1500 mientras que `ip route` muestra `mtu 1450`.

Sobrecargas según `pkg/mtu/mtu.go` (v1.20.2):

| Componente | Bytes | Composición |
|---|---|---|
| Túnel, red subyacente IPv4 | 50 | 20 IP + 8 UDP + 8 VXLAN + 14 Ethernet interno |
| Túnel, red subyacente IPv6 | 70 | 40 IP + 8 + 8 + 14 |
| IPsec (GCM de 128 bits, tamaño de clave predeterminado) | 77 | se ajusta según el tamaño de la clave |
| WireGuard | 95 | constante |
| Opción Geneve DSR | 12 | se aplica en el datapath, no en la MTU de ruta |

| Escenario (red subyacente de 1500) | MTU de ruta en el Pod | Cálculo |
|---|---|---|
| Nativo, sin cifrado | 1500 | base |
| Túnel VXLAN, red subyacente IPv4 | 1450 | 1500 - 50 |
| Túnel VXLAN, red subyacente IPv6 | 1430 | 1500 - 70 |
| Nativo + WireGuard | 1405 | 1500 - 95 |
| Nativo + IPsec | 1423 | 1500 - 77 |
| Túnel + IPsec | 1373 | 1500 - (50 + 77) |
| Túnel + WireGuard | 1355 | 1500 - (95 + 50) |

Las cifras se calculan a partir de las constantes y la función `getRouteMTU`; no se midieron en un clúster. Con tramas jumbo, la sobrecarga absoluta es la misma y representa una proporción mucho menor (una red subyacente de 9001 produce 8951 con VXLAN sobre IPv4).

Notas:

- **Geneve DSR** añade la opción de 12 bytes. Como la inserta el nodo de balanceo, los paquetes grandes pueden superar la MTU de ruta; el modo híbrido TCP (DSR solo para los metadatos SYN de TCP y SNAT para UDP) existe en parte para limitar este problema.
- **`pmtuDiscovery.enabled`** (predeterminado false) envía a los clientes ICMP fragmentation-needed. `pmtuDiscovery.packetizationLayerPMTUDMode` (nuevo en 1.19; valores `always|blackhole|disabled|unset`; predeterminado `blackhole`) controla el sondeo RFC 4821 del kernel dentro del netns del Pod. Define `disabled` cuando conoces la MTU.
- **Encadenamiento CNI**: `cni.enableRouteMTUForCNIChaining: true` pasa la MTU de ruta a los Pods del plugin encadenado (necesario, por ejemplo, para WireGuard sobre aws-cni).
- **Fragmentos IPv4/IPv6**: el seguimiento está habilitado de forma predeterminada (`enable-ipv4-fragment-tracking`, `enable-ipv6-fragment-tracking`; el mapa es `bpf-fragments-map-max`, predeterminado 8192; upstream lo marca beta). Consulta [Redes L2/L7](05-l2-l7-networking.md).
- **XDP** en AWS requiere una MTU suficientemente baja para XDP nativo de ENA (el ejemplo upstream indica 3498); los nodos con tramas jumbo no pueden usarlo sin reducir la MTU.

Desde un Pod, compruébalo con `kubectl exec <pod> -- ip route` e `ip link`; prueba con `ping -M do -s <size>` en ambas direcciones.

## 9. Masquerade

Masquerade reescribe la dirección de origen del tráfico de Pods que sale del clúster por la IP de un nodo. Cilium tiene dos implementaciones.

| | iptables (predeterminado) | BPF (`bpf.masquerade: true`) |
|---|---|---|
| Requiere | módulos iptables/ipset | KPR (NodePort BPF) y detección de dispositivos |
| Alcance | Todo el tráfico que sale por un dispositivo ajeno a Cilium, salvo que se restrinja con `egressMasqueradeInterfaces` | Dispositivos seleccionados por detección o `devices`; exclusiones por CIDR |
| Enrutamiento del host | Fuerza el enrutamiento de host heredado (alternativa silenciosa) | Compatible con el enrutamiento de host BPF |
| Protocolos | todo lo que maneja netfilter | TCP, UDP, ICMP (echo, echo-reply, frag-needed); IPv4 en producción, IPv6 beta |
| Funciones adicionales | `enableMasqueradeRouteSource` | ip-masq-agent, `enableRemoteNodeMasquerade` |
| Rango de puertos | kernel | máximo de NodePort + 1 .. 65535 (`bpf/lib/nat.h`); tabla NAT `bpf.natMax`, predeterminado 524288 |

Valores predeterminados: `enableIPv4Masquerade: true`, excepto que es **false** con `eni.enabled=true` (desde 1.18). `enableIPv6Masquerade: true`; **[1.21 pre-release]** pasa a ser «true salvo que se use ENI IPAM». `egressMasqueradeInterfaces` solo afecta al masquerade de iptables, así que no tiene efecto en un perfil ENI con masquerade desactivado.

### Orden de decisión de masquerade BPF

Según `bpf/lib/nat.h` (v1.20.2), se evalúa para cada paquete de egreso en este orden:

1. Coincide una política Egress Gateway: SNAT a la IP del gateway.
2. El destino está en el CIDR de exclusión SNAT (el CIDR de enrutamiento nativo o, en su defecto, el PodCIDR local): no aplica masquerade.
3. El endpoint local tiene la marca `SKIP_MASQ` (IPAM con varios pools): no aplica masquerade.
4. El destino está en `cilium_ipmasq_v4` (ip-masq-agent, LPM): no aplica masquerade.
5. La identidad de destino corresponde a un **nodo remoto**:
   - `enable-remote-node-masquerade=true`: aplica SNAT.
   - en caso contrario, con enrutamiento nativo: no aplica masquerade.
   - en caso contrario, con modo túnel: aplica SNAT, salvo que la entrada ipcache contenga `skip_tunnel`.
6. El origen es un endpoint local: aplica SNAT a la dirección del nodo del dispositivo de egreso; de lo contrario, deja pasar el paquete.

De esto se derivan dos consecuencias. Primero, en enrutamiento nativo el tráfico de Pod a un nodo remoto conserva la IP del Pod, pero en modo túnel pasa por masquerade; esto cambia lo que observan los firewalls del host y las políticas `NetworkPolicy`/host del nodo. Segundo, la documentación upstream de masquerade formula vagamente el paso 5 (dice que se excluyen los «paquetes destinados a otros nodos del clúster»); la tabla anterior se basa en el código BPF.

`enable-remote-node-masquerade` (nuevo en 1.19) no tiene una clave Helm específica en 1.20.2. Configúralo mediante `extraConfig: {enable-remote-node-masquerade: "true"}`. Requiere masquerade BPF y debilita la aplicación de políticas de ingreso del firewall del host, porque el origen pasa a ser una dirección de nodo.

### ip-masq-agent

```yaml
kubeProxyReplacement: true
bpf:
  masquerade: true
ipMasqAgent:
  enabled: true
  config:
    nonMasqueradeCIDRs: [10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16]
    masqLinkLocal: false
```

El chart genera un ConfigMap llamado `ip-masq-agent` con la clave `config` (JSON) en el espacio de nombres de la versión instalada; el agente vigila el archivo montado con fsnotify. Una configuración vacía usa los CIDR integrados sin masquerade: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 100.64.0.0/10, 192.0.0.0/24, 192.0.2.0/24, 192.88.99.0/24, 198.18.0.0/15, 198.51.100.0/24, 203.0.113.0/24, 240.0.0.0/4, además de 169.254.0.0/16 salvo que se active `masqLinkLocal`, y fe80::/10 salvo que se active `masqLinkLocalIPv6`. Los mapas `cilium_ipmasq_v4/v6` tienen 16384 entradas cada uno. Con ip-masq-agent habilitado, ya no es obligatorio definir un CIDR de enrutamiento nativo.

Verifica: `cilium-dbg status | grep Masquerading` (por ejemplo `BPF (ip-masq-agent) [eth0] <cidr> [IPv4: Enabled, IPv6: Disabled]`) y `cilium-dbg bpf ipmasq list`.

Límites conocidos: masquerade BPF no aplica masquerade al tráfico de Pod dirigido a la IP External de un nodo (incidencia upstream 17177). **[1.21 pre-release]** `nodePort.extendedNATPortRange` (`--node-port-nat-range-ext`) amplía el rango de puertos SNAT para tablas NAT grandes.

Incompatibilidades que se validan al iniciar: la selección de dispositivos al estilo `--masquerade-interfaces` y `enable-masquerade-to-route-source` no se pueden combinar con masquerade BPF.

## 10. Enrutamiento del host: heredado frente a BPF

| | Enrutamiento de host heredado | Enrutamiento de host BPF |
|---|---|---|
| Indicador | `bpf.hostLegacyRouting: true` | predeterminado cuando se cumplen los requisitos |
| Ruta | Pod -> veth -> netfilter/enrutamiento del host -> NIC | Pod -> consulta FIB BPF -> NIC; `redirect_peer` al netns del Pod |
| netfilter/iptables | en la ruta | se omite |
| Requisitos | ninguno especial | KPR activo y masquerade BPF (si no, vuelve al modo heredado sin fallar) |
| Requerido por | n/a | netkit, BBR para Pods, BIG TCP y enrutamiento dinámico de egreso mediante anotación de tabla FIB |

El enrutamiento de host BPF omite netfilter y la pila superior; por tanto, se interrumpen las funciones que dependen de netfilter en el espacio de nombres del host. Incompatibilidades conocidas: redirección de sidecars Istio (incidencia upstream 36022) y funciones de proveedores que dependen de netfilter, como Workload Identity de GKE. La alternativa es `bpf.hostLegacyRouting: true` o Local Redirect Policy. Desde 1.19, el enrutamiento del host se habilita automáticamente con IPsec cuando KPR y masquerade BPF están activos; el kernel debe incluir la corrección de CVE-2025-37959.

En modo heredado, reduce el costo de conntrack con `installNoConntrackIptablesRules: true` (enrutamiento nativo, IPv4, KPR con socket-LB y masquerade BPF). El chart lo desactiva para eni, azure, gke y encadenamiento CNI.

Comprueba el campo `Host:` de la línea `Routing:` en `cilium-dbg status` (`Host: BPF` o `Host: Legacy`). Cilium 1.20.2 no muestra una línea independiente «Host Routing».

## 11. Dispositivo del datapath: veth frente a netkit

`bpf.datapathMode` acepta `veth` (predeterminado), `netkit`, `netkit-l2` y, desde 1.20, `auto`.

- `netkit` (modo L3, sin ARP y variante recomendada por upstream) y `netkit-l2` conectan BPF dentro del peer y usan tcx; admiten BIG TCP. En 1.20.2 se documentan como **beta**; según la documentación, requieren kernel 6.8+ (`CONFIG_NETKIT`), aunque un comentario del código indica 6.7+. Usa la documentación como mínimo y la sonda en tiempo de ejecución como criterio definitivo.
- Requisitos (`canUseNetkit`): la sonda netkit pasa; no se usa `bpf.hostLegacyRouting`; masquerade BPF está activo (no iptables); `kubeProxyReplacement: true`; no se usa `bpf.tproxy` (incompatible desde 1.19); y, con `enableEndpointRoutes`, el controlador admite el atributo scrub (kernel 6.13 o backports).
- Si se especifica `netkit`/`netkit-l2` sin cumplir los requisitos, **el inicio falla**; `auto` vuelve a veth con una advertencia y `cilium-dbg status` muestra un resultado similar a «Device Mode: netkit [Configured: auto]», para distinguir el modo configurado del operativo.
- Si el nodo ya tiene Pods veth, el cambio de modo (incluso con `auto`) genera un error. Usa configuración por nodo (`CiliumNodeConfig`) o vacía el nodo primero.

```yaml
# values: safe netkit probe
bpf:
  datapathMode: auto
  masquerade: true
kubeProxyReplacement: true
routingMode: native
```

Verifica con `cilium-dbg status | grep -E "Device Mode|Routing|Attach Mode"` (el enrutamiento del host aparece como `Host: BPF|Legacy` en la línea `Routing:`). Upstream indica que veth podría quedar obsoleto cuando los kernels compatibles sean habituales y que el valor predeterminado podría cambiar; no asumas que será permanente.

## 12. Balanceo de carga de servicios en el datapath

Dónde se ubica cada función de servicio respecto del recorrido Pod a Pod de la sección 5:

```text
 client Pod -> connect()  --[socket-LB: cgroup connect4/sendmsg/recvmsg hooks]--> backend IP:port chosen
                |                                         (E/W, ClusterIP; before any packet exists)
                v
 packet leaves Pod -> bpf_lxc (lb4_local if socket-LB did not already translate)
                |
 external client -> NIC -> [XDP, optional: LB at driver level] -> bpf_host (from-netdev)
                       -> NodePort/LB lookup -> backend selection: random or Maglev
                       -> forward mode: SNAT, DSR (opt/ipip/geneve) or hybrid
                       -> backend local: deliver; remote: native route / tunnel (+Geneve option for DSR)
```

**Reemplazo de kube-proxy (KPR).** Es un booleano: `kubeProxyReplacement: true|false` (strict/partial ya no existen). `true` fuerza socket-LB activado. Define `k8sServiceHost`/`k8sServicePort`, porque no hay kube-proxy que resuelva el ClusterIP de la API. Abarca ClusterIP, NodePort, LoadBalancer, externalIPs y hostPort; funciona en modos túnel y nativo. Con KPR=false, el balanceo de ClusterIP por paquete sigue activo. Eliminados en 1.19: `--enable-node-port`, `--enable-host-port`, `--enable-external-ips`; eliminados en 1.20: `--node-port-mode`, `--node-port-algorithm` (usa `loadBalancer.mode`/`loadBalancer.algorithm`).

**Socket-LB.** `socketLB.enabled` (se activa con KPR) conecta hooks `connect`/`sendmsg`/`recvmsg`/`getpeername`. `socketLB.hostNamespaceOnly: true` lo limita al espacio de nombres del host; esto es necesario para sidecars Istio, KubeVirt, Kata y gVisor (se fuerza con `gatewayAPI.enabled`). `socketLB.terminatePodConnections` (predeterminado true) requiere `CONFIG_INET_DIAG*` en el kernel. **Cambio de comportamiento en 1.20**: con socket-LB desactivado o `hostNamespaceOnly=true`, las conexiones de Pod a NodePort reciben DNAT en el egreso del Pod cliente, por lo que la NetworkPolicy de egreso debe permitir los backends, no solo NodePort.

**Algoritmo.** `loadBalancer.algorithm: random|maglev`. Maglev crea una tabla de búsqueda por servicio en los mapas map-in-map `cilium_lb4_maglev` / `cilium_lb6_maglev` y calcula un hash de la 5-tupla (pone el puerto de origen en cero cuando está activada la afinidad ClientIP), módulo el tamaño de la tabla. Solo se aplica al tráfico norte-sur; el tráfico este-oeste por socket-LB no lo usa. `maglev.tableSize` debe ser 251, 509, 1021, 2039, 4093, 8191, 16381, 32749, 65521 o 131071 (predeterminado 16381, dimensionado para aproximadamente 160 backends por servicio); `maglev.hashSeed` debe ser idéntico en todos los agentes.

```bash
SEED=$(head -c12 /dev/urandom | base64 -w0)   # generate once, store it in your values/secret store
helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values \
  --set kubeProxyReplacement=true \
  --set loadBalancer.algorithm=maglev \
  --set maglev.tableSize=65521 \
  --set maglev.hashSeed=$SEED
```

Anulación por servicio: `bpf.lbAlgorithmAnnotation=true` y anotación `service.cilium.io/lb-algorithm: maglev` (solo al crear el Service). Nuevo en 1.20: anotación de EndpointSlice `service.cilium.io/weight` (0-65535, solo Maglev; 0 significa mantenimiento).

**Modo de reenvío.** `loadBalancer.mode: snat|dsr|hybrid`.

- `snat`: el nodo que recibe la solicitud reescribe el origen, así que las respuestas vuelven por él.
- `dsr`: el backend responde directamente al cliente; la dirección/puerto del servicio se transporta hasta el backend. `hybrid` usa DSR para TCP (la dirección del servicio solo se codifica en el SYN) y SNAT para UDP.
- Dispatch (`loadBalancer.dsrDispatch`, predeterminado `opt`): método de transporte.

| `dsrDispatch` | Enrutamiento nativo | Túnel (Geneve) | Túnel (VXLAN) |
|---|---|---|---|
| `opt` (opción IP / opción de destino IPv6) | sí | no | no |
| `geneve` | sí (crea el dispositivo Geneve) | sí | no (VXLAN no admite DSR) |
| `ipip` (documentado en 1.20) | sí | no | excepción del validador solo en modo de anotación; configuración funcional no documentada |

IPIP crea `cilium_ipip4/6`, requiere que el puerto del servicio coincida con el puerto de destino, admite un CIDR RSS de origen opcional (`--bpf-lb-rss-ipv4-src-cidr`) y es incompatible con BIG TCP. Las redes de nube pueden descartar paquetes con opciones IP (`opt`); en esos entornos, prefiere `geneve` o `ipip`. En AWS hay que deshabilitar la comprobación de origen/destino de EC2 para DSR. Por tanto, en modo túnel DSR requiere `tunnelProtocol: geneve` y `dsrDispatch: geneve`.

```yaml
# values: tunnel mode, kube-proxy-free, DSR via Geneve
routingMode: tunnel
tunnelProtocol: geneve
kubeProxyReplacement: true
k8sServiceHost: <API_SERVER_FQDN>      # host only, no scheme
k8sServicePort: 443
loadBalancer:
  mode: dsr
  dsrDispatch: geneve
```

Modo de anotación: `bpf.lbModeAnnotation=true` permite configurar por Service `service.cilium.io/forwarding-mode: dsr|snat` y requiere definir explícitamente `loadBalancer.dsrDispatch`. En EKS, cualquier Service LoadBalancer anotado debe mantenerse interno (`service.beta.kubernetes.io/aws-load-balancer-scheme: internal`); publica tráfico externo solo mediante CloudFront y un origen de VPC.

**Aceleración XDP.** `loadBalancer.acceleration: disabled|native|best-effort`. Requiere un controlador XDP nativo en todos los dispositivos seleccionados (si no, usa `best-effort`); solo acelera el dispositivo de enrutamiento directo; es incompatible con una red subyacente IPv6 y habilita automáticamente el descubrimiento de vecinos L2. Los paquetes que XDP devuelve a la pila no aparecen en `tcpdump`. El tráfico norte-sur acelerado por XDP o que use DSR distinto de Geneve no se cifra con WireGuard.

**Problemas conocidos que conviene tener presentes:** agotamiento del mapa inverso de sockets, parches del kernel para NFS/SMB con socket-LB, carreras al terminar backends (añade una pausa `preStop`), incompatibilidad de TCP Fast Open con DSR y una advertencia de rp_filter para DSR con varios dispositivos. Consulta también las tablas comparativas de [Redes L2/L7](05-l2-l7-networking.md).

## 13. Administrador de ancho de banda, BBR y BIG TCP

**Administrador de ancho de banda.** `bandwidthManager.enabled` (predeterminado false), `bandwidthManager.bbr`, `bandwidthManager.bbrHostNamespaceOnly`. Anotaciones `kubernetes.io/egress-bandwidth` (EDT con FQ, aplicado en el dispositivo del host del Pod y de nuevo en el egress del dispositivo de túnel) y `kubernetes.io/ingress-bandwidth` (bucket de tokens BPF). Los valores son cantidades de Kubernetes en **bits**: `"10M"` son 10 Mbit/s, no 10 MB/s. Se aplica por Pod, no por conjunto de réplicas.

Efectos secundarios: establece los sysctl del host `net.core.default_qdisc=fq` y `net.ipv4.tcp_congestion_control` (`cubic` o `bbr`), eleva los mínimos de `netdev_max_backlog` (>= 1000), `somaxconn` y `tcp_max_syn_backlog` (>= 4096), e instala FQ en dispositivos externos. Requisitos: BBR necesita kernel 5.18; BBR para Pods requiere enrutamiento de host BPF (si no, produce un error salvo que se configure `bbrHostNamespaceOnly`); con IPsec, el administrador se deshabilita silenciosamente. Los Pods existentes conservan su control de congestión anterior; BBR se aplica a Pods nuevos.

Verifica con `cilium-dbg status | grep BandwidthManager` (por ejemplo, `EDT with BPF [BBR] [eth0]`) y `cilium-dbg bpf bandwidth list`.

**BIG TCP.** `enableIPv4BIGTCP`, `enableIPv6BIGTCP` (ambos false). Kernels: IPv6 5.19+, IPv4 6.3+; entre los controladores NIC enumerados upstream están mlx4, mlx5 e ice. Requiere enrutamiento de host BPF, KPR y masquerade BPF; es incompatible con IPsec y DSR IPIP. Eleva el tamaño máximo de gso/gro a 192 KB sin cambiar la MTU; reinicia los Pods después de activarlo o desactivarlo. La documentación upstream dice «tunneling disabled», pero el código permite BIG TCP sobre VXLAN/Geneve solo si pasa una sonda del kernel para BIG TCP en túnel UDP; de lo contrario, falla con «BIG TCP in tunneling mode requires pending kernel support». En la práctica, se recomienda el enrutamiento nativo.

**Perfil de rendimiento recomendado por upstream** (no es una actualización in situ; usa configuración por nodo):

```bash
helm upgrade --install cilium cilium/cilium --version 1.20.2 -n kube-system \
  --set routingMode=native \
  --set bpf.datapathMode=netkit \
  --set bpf.masquerade=true \
  --set bpf.distributedLRU.enabled=true \
  --set bpf.mapDynamicSizeRatio=0.08 \
  --set ipv6.enabled=true --set enableIPv6BIGTCP=true \
  --set ipv4.enabled=true --set enableIPv4BIGTCP=true \
  --set kubeProxyReplacement=true \
  --set bpfClockProbe=true
```

Si quieres el administrador de ancho de banda, añade `bandwidthManager.enabled=true` y `bandwidthManager.bbr=true`. Ten en cuenta la interacción con la sección 7: netkit y BIG TCP de este perfil requieren enrutamiento de host BPF, por lo que solo funciona con KPR y masquerade BPF, como se indica.

## 14. Interacción con el cifrado

Aquí solo se describen las consecuencias para el datapath; consulta el [capítulo 12](12-mtls-encryption-identity.md) para la administración de claves.

| | WireGuard | IPsec |
|---|---|---|
| Transporte | UDP 51871 | ESP (protocolo IP 50) |
| Con modo túnel | Doble encapsulación: primero VXLAN/Geneve y después WireGuard | El cifrado se aplica **después** de encapsular en overlay (siempre desde 1.18) |
| MTU de ruta @1500 | túnel 1355, nativo 1405 | túnel 1373, nativo 1423 |
| Modo estricto | `encryption.strictMode.ingress.enabled` (1.19+) requiere WireGuard (no IPsec) y funciona con enrutamiento nativo y en modo túnel; `strictMode.egress.allowRemoteNodeIdentities` es una opción de egreso, necesaria cuando se usa un túnel o cuando se superponen CIDR de nodos y Pods con enrutamiento directo; `strictMode.egress.*` reemplazó las claves anteriores, eliminadas en 1.20 | n/a |
| Administrador de ancho de banda | funciona | se deshabilita silenciosamente |
| BIG TCP | funciona con salvedades | error al iniciar |
| Encadenamiento | no se admite el cifrado | no se admite el cifrado |

Otros datos: `encryptedOverlay` de IPsec no hacía nada desde 1.18 y se eliminó en 1.20. IPsec requiere `ipv4NativeRoutingCIDR` con cualquier configuración de enrutamiento directo, admite menos de 65535 nodos y descifra en un solo núcleo por túnel. WireGuard no cubre el tráfico norte-sur acelerado por XDP ni DSR distinto de Geneve; sí cubre DSR sobre Geneve.

Al capturar tráfico, recuerda el orden: en la NIC se ve UDP 51871 o ESP, no VXLAN/Geneve; en el dispositivo del host del Pod se ve texto sin cifrar. Captura en ambos puntos antes de concluir que falta cifrado o encapsulación.

## 15. VTEP y multicast (beta)

**La integración VTEP** permite que los Pods intercambien tráfico con extremos VXLAN externos (por ejemplo, un VTEP de hardware).

- Helm: `vtep.enabled`, `vtep.endpoint`, `vtep.cidr`, `vtep.mask`, `vtep.mac`; `vtep.endpoint`, `vtep.cidr` y `vtep.mac` son listas separadas por espacios y de igual longitud (una entrada por VTEP), mientras que `vtep.mask` es una sola máscara para todos los CIDR.
- Límites: máximo 8 VTEP; solo IPv4; intervalo de sincronización `--vtep-sync-interval` (1 min); no se combina con IPsec; la MTU del dispositivo VTEP se fija en 1500 - 50.
- El dispositivo VTEP debe usar **VNI 2** (`world`). BPF descarta paquetes overlay desde una dirección VTEP que tenga una identidad distinta de `world` (`DROP_INVALID_VNI`). En egreso, `bpf_lxc` consulta `cilium_vtep_map` y encapsula con identidad de destino `world`.
- Inspecciona con `cilium-dbg bpf vtep list`. No está documentado ni validado si VTEP funciona sobre Geneve; la configuración documentada usa modo túnel con VXLAN.

**Multidifusión (multicast).**

- Habilítalo con `cilium config set multicast-enabled true` o `extraConfig: {multicast-enabled: "true"}`; en 1.20.2 no hay un valor Helm específico.
- La documentación requiere modo VXLAN y kernel 5.10+ en amd64 o 6.0+ en arm64. El código también comprueba el helper `bpf_for_each_map_elem` (Linux 5.13+); si falta, el agente registra «Disabled support for BPF Multicast» y lo deja deshabilitado. Aquí no se verificó cuál de estos requisitos prevalece en kernels 5.10-5.12.
- Solo IPv4; IGMP v2/v3 se procesa en `bpf_lxc`; límite de 1024 grupos por 1024 suscriptores; incompatible con IPsec; debe configurarse en cada nodo (`cilium-dbg bpf multicast group add <group>` y `... subscriber add <group> <remote CiliumInternalIP>`, o en todo el clúster mediante `cilium multicast add --group-ip`, como muestra `multicast.rst` upstream; no se verificó ese comando de CLI en el código fuente de cilium-cli).

## 16. Guía de decisiones para EKS

| Opción | Configuración | Elígela cuando | Aspectos que vigilar |
|---|---|---|---|
| **IPAM ENI de Cilium** (reemplaza VPC CNI) | `eni.enabled=true`, `ipam.mode=eni`, `routingMode: native` (predeterminado con ENI), permisos del operador mediante IRSA/Pod Identity, taint `node.cilium.io/agent-not-ready=true:NoExecute` | Los Pods necesitan IP enrutables por VPC, sin SNAT dentro de la VPC, y grupos de seguridad/registros de flujo por IP de Pod | ENI prohíbe túneles; masquerade IPv4 se desactiva de forma predeterminada (1.18+); densidad de Pods limitada por capacidad de ENI/IP; el operador necesita `ec2:DescribeRouteTables`; AWS solo admite VPC CNI en nodos EC2 |
| **Overlay en EKS** | `ipam.mode=cluster-pool`, `routingMode: tunnel`, `eni.enabled=false` | El espacio de IP de Pods en la VPC es escaso o necesitas funciones de túnel | Las IP de Pods no son enrutables por VPC, así que el plano de control administrado no puede alcanzarlas: los **backends de webhook (admission y conversión) deben usar `hostNetwork`**. SG del nodo: referencia a sí mismo para UDP 8472 (o 6081). MTU 1450 (8951 con red subyacente de 9001) |
| **Encadenamiento VPC CNI** | `cni.chainingMode=aws-cni`, `cni.exclusive=false`, `enableIPv4Masquerade=false`, `routingMode=native` | Conserva IPAM y ENI de VPC CNI; añade políticas Cilium, LB y Hubble | El chart fuerza enrutamiento de host heredado y desactiva iptables sin conntrack; sin IPsec/WireGuard; L7 limitado; aws-node 1.11.2 o posterior; reinicia los Pods después de habilitarlo |
| **EKS Auto Mode / Fargate** | n/a | n/a | No se admiten CNIs alternativos |
| **EKS Hybrid Nodes** | Cilium es un CNI compatible | Nodos locales | Los CIDR de Pods deben poder enrutarse para los webhooks; consulta la sección EKS Hybrid Nodes de este repositorio |

La recomendación sobre webhooks con overlay se deriva de la guía de AWS para Hybrid Nodes (los CIDR de Pods deben ser enrutables para los webhooks) y de cómo el plano de control de Kubernetes llama a los webhooks; valídala en el laboratorio 5 antes de depender de ella.

Perfil ENI de Cilium (se omite intencionalmente la clave inerte `egressMasqueradeInterfaces`: no tiene efecto con masquerade desactivado):

```yaml
eni:
  enabled: true
ipam:
  mode: eni
routingMode: native
# enableIPv4Masquerade: true   # only if Pods must reach non-VPC destinations without a NAT gateway
```

Encadenamiento VPC CNI:

```bash
helm upgrade --install cilium cilium/cilium --version 1.20.2 -n kube-system \
  --set cni.chainingMode=aws-cni \
  --set cni.exclusive=false \
  --set enableIPv4Masquerade=false \
  --set routingMode=native
```

Notas de EKS:

- Elimina el DaemonSet `aws-node` antes de instalar Cilium como CNI (aws-node vacía las tablas de rutas) o reinicia los Pods después.
- CIDR VPC secundarios (por ejemplo, 100.64.0.0/16): el CIDR de enrutamiento nativo detectado automáticamente solo es el CIDR **principal** de la VPC. Si masquerade está activo y los Pods usan un rango secundario, establece `ipv4NativeRoutingCIDR` en un rango que lo incluya y comprueba `cilium-dbg status | grep Masquerading`. Esto se deduce del código y no se probó.
- IPv6 ENI: `eni.rst` documenta un prefijo /80 por nodo y subredes de doble pila, mientras que la página de requisitos de EKS todavía indica solo IPv4. El soporte ENI IPv6 sigue sin estar resuelto upstream; confírmalo en tu región.
- Comprobación de origen/destino: se documenta que hay que deshabilitarla para DSR. En enrutamiento nativo sobre EC2 sin ENI, en principio existe la misma limitación (la instancia no es propietaria de las IP de los Pods); esta parte es una inferencia.
- Política para el camino público: solo CloudFront llega a las cargas de trabajo, mediante un ALB/NLB interno detrás de un origen VPC de CloudFront. Los ejemplos de Cilium aquí nunca requieren un listener público ni una regla `0.0.0.0/0`.

## 17. Hoja rápida de inspección

```bash
# Effective routing, device, host-routing, masquerade, KPR, bandwidth, BIG TCP, XDP
kubectl -n kube-system exec ds/cilium -c cilium-agent -- \
  cilium-dbg status --verbose | grep -E "Routing|Device Mode|Masquerading|KubeProxyReplacement|BandwidthManager|BIG TCP|XDP"

# Tunnel device (VNI mode, port, metadata-based)
ip -d link show cilium_vxlan        # or cilium_geneve
ip route | grep cilium_host         # remote PodCIDR routes (tunnel mode)

# Tunnel endpoints and node IDs (ipcache, not the old tunnel map)
cilium-dbg bpf ipcache list | grep -i <remote-node-ip>
cilium-dbg bpf nodeid list
cilium-dbg node list

# Identity numbers to compare with the VNI
cilium-dbg endpoint list
cilium-dbg identity list

# NAT and masquerade
cilium-dbg bpf nat list
cilium-dbg bpf ipmasq list

# Services
cilium-dbg service list
cilium-dbg bpf lb list
cilium-dbg bpf lb maglev list
cilium-dbg bpf socknat list

# Bandwidth, VTEP
cilium-dbg bpf bandwidth list
cilium-dbg bpf vtep list

# Datapath events
cilium-dbg monitor -v --type trace      # to-overlay / from-overlay trace points
cilium-dbg monitor --type drop

# Wire capture on the node (not on your laptop)
sudo tcpdump -nni any -c 50 'udp port 8472'      # Geneve: 'udp port 6081'
sudo tcpdump -nni <nic> -vv 'udp port 8472'       # -vv prints the VNI
```

`cilium-dbg status` muestra una línea `Routing:` similar a `Network: Tunnel [vxlan]  Host: BPF`. Los comandos que muestran el contenido de mapas pueden variar en la disposición de columnas entre versiones; no automatices procesos basándote en las posiciones de las columnas.

## 18. Laboratorios

Ejecuta estos laboratorios solo en un clúster descartable (kind o un clúster EKS de prueba de dos nodos con grupos de seguridad que se referencian a sí mismos). Todo se comprobó con el código fuente y la documentación upstream; nada se ejecutó en un clúster activo durante esta revisión. Se describen los resultados esperados, no son capturas de una ejecución real.

### Laboratorio 1: anatomía del overlay y el VNI

**Requisitos previos:** dos nodos Linux programables, Cilium 1.20.2 con `routingMode: tunnel`, acceso al shell de los nodos y UDP 8472 permitido entre nodos.

1. En un agente, ejecuta `cilium-dbg status | grep Routing`: espera una red de túnel con protocolo vxlan.
2. En un nodo, ejecuta `ip -d link show cilium_vxlan`: debe aparecer un dispositivo vxlan con el atributo basado en flujo (externo) y el puerto de destino 8472.
3. Inicia un Pod servidor en el nodo 1 y un Pod cliente en el nodo 2 (usa nodeName o anti-affinity). Mientras el cliente consulta al servidor, ejecuta `sudo tcpdump -nni <nic> -vv 'udp port 8472' -c 20` en el nodo.
4. Anota el `vni` de la salida decodificada. Compáralo con la identidad del Pod cliente en `cilium-dbg endpoint list` del nodo 2. Deben coincidir en los paquetes cliente-servidor; las respuestas deben llevar la identidad del servidor.
5. Ejecuta `helm upgrade ... --set tunnelProtocol=geneve`, reinicia los agentes y comprueba que desaparece `cilium_vxlan`, aparece `cilium_geneve` y el filtro de captura debe cambiar al puerto 6081.

**Limpieza/reversión:** restablece `tunnelProtocol` a `vxlan` y reinicia los agentes. El cambio de protocolo recrea el dispositivo; espera una breve pérdida de conectividad entre nodos.

### Laboratorio 2: MTU con WireGuard sobre el túnel

**Requisitos previos:** clúster del laboratorio 1; UDP 51871 permitido entre nodos (referencia propia del grupo de seguridad).

1. Habilita `encryption.enabled=true`, `encryption.type=wireguard`; conserva `MTU: 0`.
2. En un Pod, ejecuta `ip route` e `ip link`. Espera que la MTU del dispositivo coincida con la de la red subyacente y que la MTU de ruta sea 1355 con una red subyacente de 1500 (sobrecarga de 95 + 50).
3. Desde un Pod ejecuta `ping -M do -s 1327 <other pod ip>` y después `-s 1328`. El primero debería funcionar (1327 + 28 = 1355) y el segundo fallar con un error parecido a fragmentation-needed.
4. `cilium-dbg status | grep Encryption` debe indicar WireGuard.

**Limpieza:** deshabilita el cifrado y reinicia los agentes; la MTU de ruta vuelve a 1450 para los Pods nuevos (los existentes conservan su MTU hasta recrearse).

### Laboratorio 3: árbol de decisión de masquerade

**Requisitos previos:** KPR activo, `bpf.masquerade=true`, un servidor echo de prueba en la misma VPC que registre la IP de origen observada y solo sea alcanzable mediante grupos de seguridad que referencien el SG del nodo.

1. Conecta un Pod al servidor echo. Comprueba el origen observado: si la IP del servidor queda fuera del CIDR de enrutamiento nativo y de la lista ip-masq-agent, debería aparecer la IP de un nodo.
2. Habilita `ipMasqAgent` con `nonMasqueradeCIDRs` que incluya el rango del servidor echo, reinicia los agentes y repite. La IP del Pod debería conservarse (la VPC debe poder devolver tráfico a las IP de Pods; esto fallará con IP de Pods overlay, que es precisamente lo que se quiere comprobar).
3. `cilium-dbg bpf ipmasq list` enumera los CIDR; `cilium-dbg bpf nat list` muestra las entradas SNAT activas.
4. Tráfico Pod a nodo remoto: en modo nativo, el origen sigue siendo la IP del Pod; en modo túnel, es la IP del nodo. Configura `extraConfig: {enable-remote-node-masquerade: "true"}` y comprueba que el modo nativo ahora también aplica masquerade.

**Limpieza/reversión:** quita el bloque ip-masq-agent y la clave extraConfig. El cambio de modo masquerade modifica las direcciones de origen que ven los firewalls; hazlo nodo por nodo.

### Laboratorio 4: servicio sin kube-proxy con Maglev y DSR Geneve

**Requisitos previos:** clúster instalado sin kube-proxy, `routingMode: tunnel`, `tunnelProtocol: geneve`, KPR activo, `loadBalancer.mode: dsr`, `dsrDispatch: geneve`, ajustes `maglev` de la sección 12; un host cliente dentro de la VPC; un Service NodePort cuyo backend esté en un nodo distinto del nodo al que te conectas. Usa solo una ruta de red interna.

1. En el nodo al que te conectas, `iptables-save | grep KUBE-SVC` no debería devolver resultados.
2. `cilium-dbg bpf lb list` muestra el servicio; `cilium-dbg bpf lb maglev list` muestra la tabla de búsqueda.
3. En el nodo backend, captura con tcpdump en su NIC: la solicitud llega como Geneve (UDP 6081) con la opción DSR; la respuesta sale directamente al cliente y usa la IP del servicio como origen.
4. Comprueba que configurar `tunnelProtocol: vxlan` junto con `loadBalancer.mode: dsr` hace que el agente falle al iniciar (hazlo en un clúster desechable y luego revierte).

**Limpieza:** revierte los valores Helm. Cambiar los modos en un clúster activo interrumpe los flujos DSR.

### Laboratorio 5: netkit/auto, enrutamiento del host y EKS ENI

**Requisitos previos:** (a) un nodo con kernel 6.8 o posterior y otro con kernel anterior; (b) para la parte ENI, un clúster EKS descartable creado sin `aws-node`.

1. Con `bpf.datapathMode=auto`, `bpf.masquerade=true` y `kubeProxyReplacement=true`, compara `cilium-dbg status | grep -E "Device Mode|Routing"` en los kernels nuevo y antiguo. Espera que `Device Mode` muestre netkit en el nodo nuevo y veth con un registro de alternativa en el antiguo; la línea `Routing:` debe mostrar `Host: BPF` en ambos. No cambies un nodo que ya ejecute Pods veth; primero vacíalo.
2. Define `bpf.masquerade=false`: la línea `Routing:` debe terminar en `Host: Legacy` y el agente debe registrar que volvió al modo heredado. Revierte el cambio.
3. Añade `kubernetes.io/egress-bandwidth: "10M"` a un Pod con el administrador de ancho de banda habilitado y confirma que aparezca en `cilium-dbg bpf bandwidth list`.
4. ENI: instala con el perfil ENI de la sección 16. `ip rule` debe mostrar, por cada IP de Pod, una regla de ingreso `to <podIP> lookup main` (prioridad 20) y otra de egreso `from <podIP> lookup <ENI table>` (prioridad 111), además de tablas de rutas por ENI. Como ENI desactiva masquerade de forma predeterminada, la regla de egreso no incluye `to <VPC CIDR>` salvo que habilites masquerade. Prueba `routingMode: tunnel` con ENI en un clúster de prueba: el agente debe negarse a iniciar.
5. Overlay en EKS: despliega un webhook de validación respaldado por un Pod normal en un clúster overlay y comprueba si el servidor API puede alcanzarlo; luego trasládalo a `hostNetwork`.

**Limpieza:** elimina las cargas de prueba, revierte los valores Helm y termina el clúster desechable. Reemplazar el CNI en un clúster poblado queda fuera del alcance y no se admite como migración in situ.

## 19. Diferencias entre versiones

| Tema | 1.18 | 1.19 | 1.20 | 1.21-pre.3 |
|---|---|---|---|---|
| Kernel mínimo | 5.10 (4.18 RHEL 8.10) | igual | igual | igual |
| `cilium_tunnel_map` | eliminado del datapath (el agente quita el pin de un mapa sobrante); CLI eliminada | paquete Go **eliminado**; extremo del túnel en el valor de ipcache | n/a | n/a |
| `underlayProtocol` (red subyacente IPv6) | **nuevo** | estable | igual | el cálculo de MTU usa la marca de túnel para la sobrecarga IPv6 |
| `enableIPv4Masquerade` con ENI | predeterminado **false** | igual | igual | igual; el valor predeterminado de masquerade IPv6 pasa a true salvo con ENI |
| `bpf.datapathMode` | veth, netkit, netkit-l2 | tproxy incompatible con netkit | se añade **`auto`**; el estado muestra modo configurado y operativo | igual |
| Enrutamiento de host BPF + IPsec | n/a | automático con IPsec + KPR + masquerade BPF (requiere la corrección CVE-2025-37959) | igual | igual |
| `enable-remote-node-masquerade` | n/a | **nuevo** | igual | igual |
| `packetizationLayerPMTUDMode` | n/a | **nuevo**, predeterminado `blackhole` | igual | igual |
| Modo estricto de WireGuard | claves antiguas | se añade `strictMode.ingress` | se **eliminan** las claves antiguas `strictMode.enabled/cidr` | igual |
| IPsec `encryptedOverlay` | no hacía nada | obsoleto | **eliminado** | n/a |
| Dispatch DSR | existen los indicadores `opt`/`ipip`/`geneve`; IPIP no documentado | igual | IPIP documentado; anotaciones DSR/algoritmo por servicio; `bpf-lb-rss-*`; `service.cilium.io/weight` | igual |
| Indicadores eliminados | n/a | `--enable-node-port/host-port/external-ips` | `--node-port-mode`, `--node-port-algorithm` | n/a |
| Socket-LB para Pod a NodePort | n/a | cambia el formato de traza | DNAT en egreso del cliente con socketLB desactivado o `hostNamespaceOnly` | igual |
| `nativeRoutingCIDRFromClusterPool`, `nodePort.enableDynamicSourceLookup` | n/a | n/a | **nuevos** | igual |
| `nodePort.extendedNATPortRange` | n/a | n/a | n/a | **nuevo [1.21 pre-release]** |
| Valor predeterminado de `l2NeighDiscovery.enabled` | false (antes true) | igual | igual | igual |
| Mensaje de autoDirectNodeRoutes + túnel | «cannot be used with tunneling» | igual | igual | «requires native routing mode» |

Madurez: estables: túnel, modo nativo, masquerade BPF (IPv4), KPR, Maglev, DSR, aceleración XDP, administrador de ancho de banda, BBR y BIG TCP. Beta: netkit, masquerade BPF IPv6, VTEP, multicast y seguimiento de fragmentos. Eliminados: `cilium_tunnel_map`, `encryptedOverlay`, `--node-port-mode`.

## 20. Solución de problemas

| Síntoma | Causa probable | Comprobación / solución |
|---|---|---|
| El agente termina al iniciar con «cannot be used with tunneling» | `autoDirectNodeRoutes` con modo túnel | Elige enrutamiento nativo o elimina el indicador |
| El agente termina con «Cannot specify IPAM mode eni in tunnel mode» | IPAM ENI con modo túnel | Usa `routingMode: native` |
| Falla el tráfico entre Pods de nodos distintos, pero funciona dentro del mismo nodo | UDP 8472/6081 bloqueado, puerto de túnel incorrecto o al SG del nodo le falta la autorreferencia | `tcpdump -nni <nic> 'udp port 8472'` en ambos nodos; revisa SG/NACL y la línea `Routing:` |
| Se detienen transferencias grandes, pero funcionan las solicitudes pequeñas | agujero negro de MTU (sobrecarga del túnel o ICMP filtrado) | Compara la MTU de `ip route` del Pod con la MTU de ruta; usa `ping -M do -s`; revisa los ajustes `pmtuDiscovery` |
| El tráfico Pod a redes externas funciona en Pods nativos, pero el origen es una IP de Pod y las respuestas nunca vuelven | masquerade desactivado (predeterminado de ENI) o destino dentro del CIDR de enrutamiento nativo | `cilium-dbg status \| grep Masquerading`; habilita masquerade o ip-masq-agent según corresponda |
| La IP de origen de Pod a nodo remoto difiere entre clústeres | En modo túnel se aplica masquerade; en modo nativo no (sección 9) | Decide el comportamiento intencionalmente; usa `enable-remote-node-masquerade` si necesitas uniformidad |
| El registro del agente muestra «Falling back to legacy host routing» | masquerade iptables o KPR desactivado | Habilita `bpf.masquerade` y KPR, o acepta el modo heredado |
| El tráfico del sidecar Istio se omite o se interrumpe | enrutamiento de host BPF/socket-LB en espacios de nombres de Pods | `socketLB.hostNamespaceOnly=true` o `bpf.hostLegacyRouting=true` |
| Falla `bpf.datapathMode=netkit` | falta el kernel requerido, se usa enrutamiento heredado o masquerade iptables, KPR está desactivado o se usa tproxy | Usa `auto` para sondear el soporte y cumple los requisitos |
| El agente rechaza DSR | túnel VXLAN o falta dispatch Geneve | Usa `tunnelProtocol: geneve` y `dsrDispatch: geneve` |
| Los flujos de servicio se restablecen de forma intermitente tras un cambio de nodo | la semilla Maglev difiere entre agentes | Configura el mismo `maglev.hashSeed` en todas partes |
| No aparece tráfico NodePort en `tcpdump` | aceleración XDP | Captura en otro punto o desactiva la aceleración para depurar |
| Se agota el tiempo de espera del webhook en EKS overlay | el servidor API no puede alcanzar IP de Pods ajenas a VPC | Ejecuta los backends del webhook con `hostNetwork` |
| No se ven paquetes cifrados en la NIC | interacción entre administrador de ancho de banda, IPsec/WireGuard o una ruta XDP/DSR distinta de Geneve | Comprueba `cilium-dbg status \| grep Encryption` y la tabla de cifrado de la sección 14 |

Procedimiento general: (1) `cilium-dbg status --verbose` para ver los ajustes efectivos; (2) `cilium-dbg monitor --type drop` para los motivos de descarte (busca `DROP_INVALID_IDENTITY`, `DROP_INVALID_VNI`); (3) confirma que el destino aparece en `cilium-dbg bpf ipcache list` con el extremo de túnel correcto; (4) captura en las NIC de ambos nodos y en `cilium_vxlan`/`cilium_geneve`; (5) revisa los registros de inicio del agente en busca de mensajes de alternativa.

## 21. Límites de validación y fuentes

Durante esta revisión, los laboratorios del capítulo no se ejecutaron en un clúster activo. Tanto ellos como todas las afirmaciones de comportamiento anteriores se contrastaron con el código fuente y la documentación upstream en las etiquetas indicadas abajo. Algunas afirmaciones son inferencias y se identifican como tales: alcanzabilidad de webhooks overlay en EKS, comprobación de origen/destino EC2 con enrutamiento nativo en instancias sin ENI, comportamiento del CIDR de enrutamiento nativo para CIDR VPC secundarios, VTEP sobre Geneve y el requisito mínimo de kernel para multicast entre 5.10 y 5.13 (sin verificar). Se omite deliberadamente describir otro modo de enrutamiento presente como andamiaje en la versión preliminar 1.21.

Los valores calculados (tabla de MTU) son operaciones aritméticas con constantes del código fuente, no mediciones.

Fuentes (v1.20.2 salvo indicación):

- [Enrutamiento](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/routing.rst), [masquerade](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/masquerading.rst), [ajuste](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/performance/tuning.rst), [requisitos del sistema](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst)
- [Reemplazo de kube-proxy](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/kubeproxy-free.rst), [administrador de ancho de banda](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/bandwidth-manager.rst), [VTEP](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/vtep.rst), [multicast](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/multicast.rst), [IPAM ENI](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst), [encadenamiento AWS CNI](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/cni-chaining-aws-cni.rst)
- [BPF de túnel/overlay](https://github.com/cilium/cilium/blob/v1.20.2/bpf/bpf_overlay.c), [BPF lxc](https://github.com/cilium/cilium/blob/v1.20.2/bpf/bpf_lxc.c), [helpers de identidad](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/identity.h), [NAT](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/nat.h), [opciones de túnel](https://github.com/cilium/cilium/blob/v1.20.2/bpf/lib/tunnel.h), [MTU](https://github.com/cilium/cilium/blob/v1.20.2/pkg/mtu/mtu.go), [validación de inicio](https://github.com/cilium/cilium/blob/v1.20.2/daemon/cmd/daemon_main.go), [validación KPR](https://github.com/cilium/cilium/blob/v1.20.2/pkg/kpr/initializer/kube_proxy_replacement.go), [valores Helm](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)
- Versión preliminar: [daemon_main.go en v1.21.0-pre.3](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/daemon/cmd/daemon_main.go), [values.yaml en v1.21.0-pre.3](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/install/kubernetes/cilium/values.yaml)
- AWS: [plugins CNI alternativos de EKS](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html)

## Cuestionario

[Comprueba lo que sabes sobre enrutamiento overlay y nativo](../../quizzes/networking/cilium/09-overlay-native-routing-quiz.md).

[Volver a la página principal](README.md)
