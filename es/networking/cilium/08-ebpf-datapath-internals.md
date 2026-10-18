# Parte 8: Internals del datapath eBPF

> **Base de revisión**: Cilium 1.20.2 (estable, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Los elementos marcados **[1.21 pre-release]** corresponden a v1.21.0-pre.3 y pueden cambiar antes de la versión GA.
> **Última actualización**: 15 de octubre de 2026

Este capítulo examina el datapath de Cilium: qué programas BPF se ejecutan, dónde se conectan, cómo se invocan entre sí, qué mapas consultan, cómo los compila y carga el agente, y cómo se procesa un paquete salto a salto. Los conceptos generales de eBPF (historia, verificador y tipos de mapas) se explican en [Parte 2: eBPF](02-ebpf.md). El comportamiento de overlay y enrutamiento se describe en [Parte 9](09-overlay-native-routing.md); IPAM, en [Parte 10](10-ipam-deep-dive.md).

> **Advertencia sobre guías antiguas: `cilium_tunnel_map` ya no existe.** Publicaciones antiguas y algunas listas de ejemplos upstream muestran un `cilium_tunnel_map` que asociaba un CIDR de Pod con la IP de un nodo remoto. Cilium 1.17 todavía lo tenía en BPF (`bpf/lib/encap.h`) y `cilium-dbg bpf tunnel list` lo mostraba. Se eliminó del datapath en 1.18 (el árbol BPF de 1.18.14 no lo referencia; el agente solo quita el pin de un mapa sobrante) y el paquete Go se eliminó en 1.19. En Cilium 1.20.2 ningún programa BPF lo referencia. El nodo remoto (punto de conexión del túnel) se almacena en el **valor** de `cilium_ipcache_v2` (campo `tunnel_endpoint`, con el indicador `flag_has_tunnel_ep`). En 1.18 y 1.20 no existe el comando `cilium-dbg bpf tunnel list`. Si una guía recomienda ejecutar `bpftool map dump` sobre el mapa de túnel para depurar el enrutamiento overlay, consulta ipcache en su lugar (`cilium-dbg bpf ipcache list`). Un documento de desarrollo upstream todavía enumera el mapa en una salida de ejemplo; eso no significa que el mapa siga activo.

## Objetivos de aprendizaje

- Identificar cada objeto BPF de Cilium, sus programas de entrada y el dispositivo o hook cgroup al que se conecta cada uno.
- Explicar por qué Cilium usa tail calls y cómo el programa del emisor ejecuta la política del endpoint de destino.
- Interpretar la estructura de claves y valores de los mapas de políticas, ipcache, conntrack y servicios, y dimensionarlos con los indicadores adecuados.
- Describir el flujo del agente: caché de plantillas ELF, constantes `.rodata.config`, fijación de mapas, conexión y confirmación.
- Seguir una conexión Pod -> ClusterIP -> Pod e indicar las consultas a mapas en cada salto.
- Inspeccionar un nodo activo con `cilium-dbg bpf ...` y `bpftool`.

## 1. Conjunto de programas y puntos de conexión

Cilium compila unos pocos archivos fuente C bajo `bpf/`. Cada uno genera un objeto ELF; cada objeto contiene uno o más **programas de entrada** (sección ELF `tc/entry`, `xdp/entry`, `cgroup/...`) y muchos **programas de continuación** (sección `tc/tail`). Los nombres que muestra `bpftool prog show` llevan el prefijo `cil_`.

### 1.1 Programas de entrada en 1.20.2

| Objeto ELF (fuente) | Programa de entrada | Conectado a | Función |
|---|---|---|---|
| `bpf_lxc.o` | `cil_from_container` | Ingress del veth `lxc*` del lado del host (es decir, tráfico que sale del Pod); en netkit, hook principal del peer netkit | Ruta de salida por endpoint: identidad, CT, política de salida, balanceo de carga de servicio (modo por paquete) y reenvío |
| `bpf_lxc.o` | `cil_to_container` | Egress del `lxc*` del lado del host (tráfico hacia el Pod, entregado a través de la pila) | Política de entrada para tráfico entregado por la pila (rutas de endpoint, respuestas del proxy L7). Solo se conecta cuando el endpoint necesita un programa de egress |
| `bpf_lxc.o` | `cil_lxc_policy`, `cil_lxc_policy_egress` | **no se conecta a un dispositivo**; se guarda en los arreglos globales de programas `cilium_call_policy` / `cilium_egresscall_policy` | Políticas de entrada del destino y de salida del origen; otros programas las invocan |
| `bpf_host.o` | `cil_from_netdev` | Ingress de cada dispositivo nativo/externo | Tráfico dirigido al host y reenviado, NodePort, identidad obtenida de ipcache y firewall del host |
| `bpf_host.o` | `cil_to_netdev` | Egress de dispositivos nativos (solo se conecta cuando lo requieren masquerade, NodePort, WireGuard o IPsec) | Masquerade BPF, SNAT de NodePort, EDT/ancho de banda e indicadores de cifrado |
| `bpf_host.o` | `cil_from_host` | Egress de `cilium_host` | Tráfico de la pila del host -> Pod |
| `bpf_host.o` | `cil_to_host` | Ingress de `cilium_host` y `cilium_net` | Tráfico Pod -> host y firewall del host |
| `bpf_host.o` | `cil_host_policy` | Slot del arreglo de programas (política del endpoint host) | Política de firewall del host |
| `bpf_overlay.o` | `cil_from_overlay`, `cil_to_overlay` | Ingress / egress de `cilium_vxlan` o `cilium_geneve` | Lee el ID del túnel como identidad de origen |
| `bpf_wireguard.o` | `cil_from_wireguard`, `cil_to_wireguard` | Ingress de `cilium_wg0` (siempre) / egress (solo cuando es necesario) | Marca el tráfico descifrado |
| `bpf_xdp.o` | `cil_xdp_entry` | XDP en dispositivos nativos | Prefiltro CIDR y aceleración de NodePort/DSR |
| `bpf_sock.o` | `cil_sock4_connect`, `cil_sock4_sendmsg`, `cil_sock4_recvmsg`, `cil_sock4_getpeername`, `cil_sock4_pre_bind`, `cil_sock4_post_bind`, equivalentes IPv6, `cil_sock_release` | Hooks sock_addr / sock de **cgroup v2** en la raíz del cgroup | Balanceo de carga a nivel de socket |
| `bpf_sock_term.o` | `cil_sock_{tcp,udp}_destroy_v{4,6}` | Iteradores BPF (`iter/tcp`, `iter/udp`) que llaman a la kfunc `bpf_sock_destroy` | Termina sockets conectados a backends eliminados; si la kfunc no está disponible, el agente recurre a `sock_diag` mediante netlink |
| `bpf_probes.o`, `bpf_alignchecker.o` | n/a | Se ejecutan una vez al iniciar mediante `BPF_PROG_RUN` | Sondeos de capacidades del kernel y comprobación del diseño de estructuras C/Go |

`bpf_network.c` (`cil_from_network`, descifrado IPsec en el ingress de dispositivos nativos) existe en 1.18.14 y 1.19.8 y se **eliminó en 1.20**.

```
                       node A                                   node B
 pod C eth0 ----veth---- lxc_C           lxc_B ----veth---- pod B eth0
   |  cgroup/connect4          |             ^                     
   |  (bpf_sock.o)             | tcx ingress |  redirect_peer
   |                           v cil_from_container                 
   |                    +-------------------+   (tail calls, maps)
   |                    |   bpf_lxc.o       |-------+
   |                    +-------------------+       | encap / FIB redirect
   |                           |                     v
   |        cilium_host  <-----+          cilium_vxlan (cil_to_overlay)  ==underlay==>
   |        cil_from_host/cil_to_host        eth0 (cil_from_netdev / cil_to_netdev)
   |                                         eth0 XDP (cil_xdp_entry, optional)
```

### 1.2 tcx, tc heredado y netkit

Para los programas por dispositivo, el cargador (`pkg/datapath/loader/tc.go`) elige el mecanismo en este orden:

1. **tcx** (Helm `bpf.enableTCX: true`, valor predeterminado): un `bpf_link` conectado con `link.AttachTCX` al ancla tail. El enlace queda **fijado** bajo `/sys/fs/bpf/cilium/endpoints/<id>/links/` (endpoints) o `/sys/fs/bpf/cilium/devices/<dev>/links/` (dispositivos). Al actualizar el programa, el enlace se actualiza de forma atómica, por lo que durante una recarga no hay un intervalo sin programa. Requiere kernel 6.6 o posterior. Tras conectar tcx correctamente, se eliminan los filtros tc heredados obsoletos.
2. **tc heredado**: si el kernel responde «not supported» o `enableTCX: false`, el cargador usa una disciplina qdisc `clsact` con `cls_bpf` en modo de acción directa y desconecta cualquier enlace tcx obsoleto.
3. **Fallo definitivo** solo si ninguno funciona: el agente informa que necesita compatibilidad con tc-bpf o tcx (Linux 6.6 o posterior).

**netkit** (madurez: **beta**): `bpf.datapathMode: veth | netkit | netkit-l2 | auto`. El valor predeterminado es `veth`. Con netkit, los programas específicos del Pod se conectan dentro del dispositivo **peer** de netkit; los demás dispositivos siguen usando tcx y al seleccionar netkit se activa tcx automáticamente. Requisitos comprobados por el código (`canUseNetkit`): el sondeo del kernel debe pasar (la documentación upstream indica 6.8 o posterior; el mensaje de error del código menciona 6.7), enrutamiento de host BPF (sin `bpf.hostLegacyRouting`), masquerade BPF, reemplazo de kube-proxy y **sin `bpf.tproxy`** (requiere `bpf_sk_assign`, válido solo en ingress tc). `auto` es nuevo en 1.20: sondea el soporte y, si falla, vuelve a veth con una advertencia. Una vez que los Pods usan veth, se rechaza el cambio a netkit o `auto`; en su lugar, crea grupos de nodos nuevos.

| Mecanismo | Kernel | Objeto fijado | Comportamiento al recargar | Madurez en Cilium |
|---|---|---|---|---|
| tc heredado (`clsact` + `cls_bpf`) | base 5.10 | filtro en el dispositivo | reemplazo del filtro | estable, alternativa |
| tcx | 6.6+ | `bpf_link` bajo `/sys/fs/bpf/cilium/...` | actualización atómica del enlace | estable, predeterminado cuando está disponible |
| netkit | 6.8+ (documentación) | enlace netkit en peer | actualización atómica del enlace | beta |

### 1.3 Hooks XDP y cgroup

- **XDP** (`cil_xdp_entry`) se conecta cuando `loadBalancer.acceleration` es `native` o `best-effort`. Ejecuta un prefiltro CIDR (mapas LPM `cilium_cidr_v4_fix`/`dyn`) y la ruta rápida de NodePort/DSR. Si el controlador devuelve `EINVAL`, el cargador reintenta hasta cuatro combinaciones de conexión (tipo de conexión e indicador `XDP_HAS_FRAGS`).
- **Hooks cgroup** se conectan una vez en la raíz de cgroup (indicador del agente `--cgroup-root`, predeterminado `/run/cilium/cgroupv2`) mediante `bpf_link`, fijado bajo `/sys/fs/bpf/cilium/socketlb/links/cgroup`. Se ejecutan en el espacio de nombres de red de cada Pod, salvo que `socketLB.hostNamespaceOnly=true`.

## 2. Tail calls y estructura de los programas de política

### 2.1 Por qué se usan tail calls

Una tail call sustituye el programa en ejecución por otro sin retornar. Cilium las usa por tres motivos: el límite de complejidad del verificador en un solo programa (1 millón de instrucciones), la pila de 512 bytes y la posibilidad de mantener las funciones opcionales grandes fuera de la ruta habitual. La longitud máxima de la cadena es de 33 tail calls. Mezclar llamadas bpf-to-bpf con tail calls requiere kernel 5.10, una de las razones para adoptar esa versión como base.

El estado se conserva entre tail calls en dos lugares: `skb->cb[]` (las posiciones `CB_*`, como `CB_SRC_LABEL`) y los mapas scratch por CPU `cilium_tail_call_buffer4/6`, que guardan, por ejemplo, la tupla conntrack y el resultado calculados por el programa tail de CT.

### 2.2 Arreglos de llamadas por endpoint

Cada endpoint tiene un `PROG_ARRAY` privado llamado `cilium_calls_<endpoint-id, 5 digits>` (`cilium_calls_00312`). El endpoint host usa `cilium_calls_hostns_<id>` y cada dispositivo nativo usa `cilium_calls_netdev_<ifindex>`. Otros cargadores usan `cilium_calls_overlay_2` (el dispositivo overlay, identificado con la identidad reservada `world` 2), `cilium_calls_wireguard_<ifindex>` y `cilium_calls_xdp_<ifindex>`. Se declaran con `CILIUM_CALL_SIZE` entradas y un indicador de fijación que significa «reemplaza el pin en cada carga; nunca reutilices un arreglo anterior».

| Versión | `CILIUM_CALL_SIZE` |
|---|---|
| 1.18.14 | 48 |
| 1.19.8 | 49 |
| 1.20.2 | 50 |
| 1.21.0-pre.3 | 50 |

Las posiciones (slots) son **estáticas**: el punto de llamada es ensamblador inline con un número de slot constante. El cargador lee las etiquetas BTF decl-tag (`tail:cilium_calls/<idx>`) de cada programa `tc/tail`, completa el arreglo y **elimina los programas tail inalcanzables** una vez aplicadas las constantes (sección 5). Grupos de posiciones en 1.20:

| Slots | Significado |
|---|---|
| 1-2, 4-5 | notificación de descarte/error, solicitud de vecino ICMPv6 y tiempo excedido |
| 6 | ARP |
| 3 | sin uso (hueco de numeración conservado para evitar conflictos al retroportar cambios) |
| 7, 10 | IPv4 / IPv6 desde LXC (alias para las entradas netdev, overlay y WireGuard) |
| 8-9 | traducción IPv4 a IPv6 y de IPv6 a IPv4 (`CILIUM_CALL_IPV46_RFC6052`, `CILIUM_CALL_IPV64_RFC6052`; NAT46/NAT64) |
| 11-14 | solo política to-LXC, hacia el endpoint |
| 15-25, 36-39 | NAT de NodePort, rev-NAT, DSR, reenvío SNAT; desde el host |
| 26-27 | continuación desde LXC (segunda mitad de la ruta de salida; divide la complejidad del verificador) |
| 28-33 | ingreso CT / solo política de ingreso CT / egreso CT, IPv4 e IPv6 |
| 34-35, 40 | SRv6, rev-SNAT entre clústeres |
| 41-47 | continuación desde host/netdev, ICMP «sin servicio» inalcanzable y entrega multicast |
| 48-49 | respuesta ICMP ante denegación de política (nuevo en 1.20; se usa cuando `policy_deny_response` está habilitado) |

### 2.3 Arreglos globales de programas de política

La política no está en el arreglo de llamadas por endpoint. `cil_lxc_policy` y `cil_lxc_policy_egress` se insertan en dos arreglos **globales** de programas, indexados por ID de endpoint y con tamaño `ENDPOINTS_MAP_SIZE`:

| Arreglo | Índice | Ejecuta |
|---|---|---|
| `cilium_call_policy` | ID del endpoint de destino | política de **ingreso** del destino |
| `cilium_egresscall_policy` | ID del endpoint de origen | política de **egreso** del origen |

El cargador escribe estos posiciones **antes** de conectar el programa tc/tcx (`PolicyMap.Update(ep id, PolicyProg)`). Cuando el emisor termina la reescritura L3 para un destino local, llama a `tail_call_policy(ep->lxc_id)`. Esto importa porque, con enrutamiento de host BPF, el paquete se mueve al espacio de nombres de red del Pod de destino mediante `bpf_redirect_peer`, lo que **omite el hook tc egress del destino**. Llamar desde el emisor al programa de política del destino es lo que sigue aplicando la política de ingreso entre Pods del mismo nodo. Si el slot está vacío (el endpoint está finalizando), el paquete se descarta con `DROP_EP_NOT_READY`.

`cil_to_container` sigue existiendo para el tráfico entregado por la pila; por tanto, la política de ingreso del destino puede ejecutarse mediante la tail call del emisor o desde ese hook egress.

## 3. Ruta de aplicación de políticas

### 3.1 Mapa de políticas

Cada endpoint tiene `cilium_policy_v3_<id>` (1.20; `cilium_policy_v2_` en 1.18/1.19). Tipo `LPM_TRIE`, indicadores `BPF_F_NO_PREALLOC | BPF_F_RDONLY_PROG_COND` y tamaño `--bpf-policy-map-max` (valor predeterminado: 16384 por endpoint).

```
policy_key  { lpm prefixlen; u32 sec_label;   /* remote identity, 0 = wildcard */
              u8 egress:1;  u8 protocol;      /* 0 = any */
              be16 dport; }                   /* prefix match => port ranges */
policy_entry{ be16 proxy_port;                /* != 0 => redirect to L7 proxy */
              deny:1; lpm_prefix_length:5; auth_type:7; has_explicit_auth_type:1;
              u32 precedence; u32 cookie; }
```

El prefijo LPM cubre `sec_label` y `egress` de forma exacta, `protocol` en su totalidad o nada, y `dport` como prefijo de bits; así los rangos de puertos se representan con unas pocas entradas.

### 3.2 Algoritmo de búsqueda

Para un flujo con identidad remota `R`, protocolo `P` y puerto `D`:

1. Búsqueda específica con `sec_label = R`. Si el resultado tiene precedencia máxima (una denegación), se detiene.
2. Búsqueda agregada: agregado de la identidad (por ejemplo, un grupo CIDR) y luego `sec_label = 0` (comodín L3).
3. Se elige la mayor `precedence` (denegación antes que redirección al proxy y esta antes que autorización), y luego el prefijo LPM más largo. Si no hay coincidencia, el resultado es `DROP_POLICY`.

El tipo de coincidencia se informa en los eventos (L3+L4, solo L3, solo L4, solo protocolo o todos). Cuando se habilitan reglas ICMP, el tipo ICMP se guarda en `dport`; «se necesita fragmentación» siempre se permite.

### 3.3 Veredicto y efectos secundarios

- Denegar: `DROP_POLICY_DENY` y un evento de descarte. Permitir con `proxy_port != 0`: redirigir al proxy (sección 3.5). Permitir con `auth_type != 0`: `DROP_POLICY_AUTH_REQUIRED`, salvo que `cilium_auth_map` tenga una entrada válida.
- La **política de egreso la aplica el endpoint de origen** (`handle_ipv4_from_lxc`), solo para `CT_NEW` y `CT_ESTABLISHED`; las respuestas (`CT_REPLY`, `CT_RELATED`) omiten la política. La **política de ingreso la aplica el destino** (`ipv4_policy()` en su programa de política) y, tras permitir, crea la entrada CT de ingreso.
- Se emite un evento de veredicto de política al denegar y al permitir una conexión nueva. El tráfico hairpin (un Pod accede a su propia IP de servicio) omite la política.
- Los contadores opcionales por entrada se guardan en `cilium_policystats` (`--bpf-policy-stats-map-max` 65536).

### 3.4 Los cambios de política no requieren recompilación

Las actualizaciones de política son operaciones sobre el mapa `cilium_policy_v3_<id>` (`applyPolicyMapChangesLocked`). El objeto solo se reconstruye y vuelve a cargar si cambia el hash de configuración del endpoint o del nodo. Por eso, editar un `CiliumNetworkPolicy` nunca ejecuta clang.

### 3.5 Redirección L7 y FQDN

Cuando `proxy_port != 0`, `ctx_redirect_to_proxy4()` envía el flujo a Envoy o al proxy DNS. Hay dos implementaciones:

| Método | Funcionamiento | Madurez |
|---|---|---|
| iptables TPROXY (predeterminado) | El datapath establece `mark = MARK_MAGIC_TO_PROXY \| proxy_port << 16` y devuelve OK; las reglas `CILIUM_PRE_mangle` con `xt_socket`/`TPROXY` lo dirigen al listener | estable |
| `bpf.tproxy: true` | `bpf_sk_assign` asigna el socket del listener en ingress tc | beta, desactivado de forma predeterminada, **incompatible con netkit** (el agente se niega a iniciar en 1.19.8, 1.20 y 1.21.0-pre.3; no se encontró esa comprobación en el código de 1.18.14) |

Los puertos del proxy provienen de `--proxy-portrange-min/max` (10000-20000). La entrada CT registra `proxy_redirect` para que las respuestas vuelvan al proxy. BPF no genera eventos L7; Envoy y el proxy DNS envían registros de acceso al agente.

La autenticación mutua (`auth_type`) está **obsoleta desde 1.20** (usa ztunnel); **[1.21 pre-release]** elimina `--bpf-auth-map-max` y `cilium_auth_map`, y los bits de autenticación de la entrada quedan reservados.

## 4. Catálogo de mapas

Los mapas globales se fijan por nombre bajo `/sys/fs/bpf/tc/globals/`; los enlaces y objetos de plugins se encuentran bajo `/sys/fs/bpf/cilium/`. Helm: `bpf.root` (predeterminado `/sys/fs/bpf`), `bpf.autoMount.enabled`.

### 4.1 Mapas principales

| Mapa | Tipo | Clave -> Valor (campos esenciales) | Notas |
|---|---|---|---|
| `cilium_lxc` | HASH | IP del endpoint (+familia, cluster_id) -> `{ifindex, lxc_id, flags, mac, node_mac, sec_id, parent_ifindex}` | endpoints locales e IP del host; 65535 entradas (`lxcmap.MaxEntries`) |
| `cilium_ipcache_v2` | LPM_TRIE | `{cluster_id, family, ip/prefix}` -> `{sec_identity, tunnel_endpoint, key, flag_skip_tunnel, flag_has_tunnel_ep, flag_ipv6_tunnel_ep, flag_remote_cluster}` | **identidad y extremo del túnel**; 512000 entradas (`ipcachemap.MaxEntries`) |
| `cilium_policy_v3_<id>` | LPM_TRIE | consulta 3.1 | por endpoint |
| `cilium_calls_<id>`, `_hostns_`, `_netdev_` | PROG_ARRAY | slot -> programa | privado; se reemplaza con cada carga |
| `cilium_call_policy`, `cilium_egresscall_policy` | PROG_ARRAY | ID del endpoint -> programa de política | global |
| `cilium_ct4_global`, `cilium_ct6_global` | LRU_HASH | 5-tupla + indicadores de dirección -> `ct_entry` | TCP |
| `cilium_ct_any4_global`, `cilium_ct_any6_global` | LRU_HASH | igual | no TCP |
| `cilium_snat_v4_external` (+`v6`) | LRU_HASH | tupla CT -> entrada NAT (`to_saddr/to_sport` o `to_daddr/to_dport`) | masquerade, SNAT de NodePort |
| `cilium_nodeport_neigh4/6` | LRU_HASH | IP del siguiente salto -> MAC | |
| `cilium_node_map_v2` | HASH | `{family, ip}` -> `{node id, spi}` | ID de nodo para IPsec/WireGuard/ClusterMesh (v1 se eliminó en 1.19) |
| `cilium_devices` (nuevo en 1.20) | HASH | ifindex -> `{mac, l3}` | sincronizado por el agente |
| `cilium_runtime_config` | ARRAY | índice -> u64 (desfase temporal, actividad del agente) | `cilium-dbg bpf config list` |
| `cilium_metrics` | PERCPU_HASH | `{reason, direction, line, file}` -> `{count, bytes}` | alimenta los contadores de reenvío y descarte |
| `cilium_events` | PERF_EVENT_ARRAY | CPU -> fd de perf | origen para monitor y Hubble (sección 8) |
| `cilium_signals` | PERF_EVENT_ARRAY | datapath -> señales al agente | por ejemplo, CT completo activa GC |

Las direcciones de conntrack se almacenan con origen y destino invertidos respecto del paquete; `ct_entry` contiene la duración, `rx/tx_closing`, `rev_nat_index`, `proxy_redirect`, `from_l7lb`, `from_tunnel`, `src_sec_id` y los indicadores TCP observados. Un solo mapa guarda entradas de egreso, ingreso y ámbito de servicio, diferenciadas por `tuple.flags`. Cluster Mesh agrega mapas internos por clúster (`cilium_per_cluster_ct_*`) para admitir IP superpuestas.

Tiempos de espera (indicadores del agente, 1.20.2): TCP establecido 2 h 13 min 20 s, SYN 1 min, FIN 10 s, no TCP 1 min, TCP de servicio 2 h 13 min 20 s y gracia del servicio 1 min.

### 4.2 Mapas de balanceo de carga

| Mapa | Tipo | Clave -> Valor | Notas |
|---|---|---|---|
| `cilium_lb4_services_v2` (+`6`) | HASH | `{address, dport, backend_slot, proto, scope}` -> `{backend_id or affinity/algorithm, count, rev_nat_index, flags, qcount}` | el slot 0 es el frontend; los slots 1..count contienen ID de backends; `scope` separa el tráfico externo e interno (`externalTrafficPolicy`) |
| `cilium_lb4_backends_v3` (+`6`) | HASH | `backend_id` -> `{address, port, proto, flags, cluster_id, zone}` | |
| `cilium_lb4_reverse_nat` (+`6`) | HASH | `rev_nat_index` -> `{address, port}` | restaura las respuestas de LB por paquete |
| `cilium_lb4_reverse_sk` (+`6`) | LRU_HASH | `{socket cookie, backend addr, port}` -> `{original service addr, port, rev_nat_index}` | traducción inversa de socket-LB |
| `cilium_lb4_affinity`, `cilium_lb_affinity_match` | LRU_HASH / HASH | cliente (IP o cookie de netns) + rev_nat -> backend | `sessionAffinity` |
| `cilium_lb4_source_range` | LPM_TRIE | `{rev_nat_id, cidr}` -> indicador | `loadBalancerSourceRanges` |
| `cilium_lb4_maglev` | HASH_OF_MAPS | `rev_nat_id` -> arreglo de tabla de búsqueda | `--bpf-lb-algorithm maglev`, tamaño de tabla `--bpf-lb-maglev-table-size` |
| `cilium_lb4_health` | LRU_HASH | cookie de socket -> backend par | datapath de comprobación de estado de LB; kernel 5.12 |

Los 8 bits superiores del campo `affinity_timeout` del servicio contienen el algoritmo de selección (aleatorio o maglev).

### 4.3 Mapas de funciones (una línea por mapa)

`cilium_ipmasq_v4/v6` (CIDR sin masquerade), `cilium_ipv4_frag_datagrams` (8192 de forma predeterminada), `cilium_vtep_map`, `cilium_srv6_*`, `cilium_egress_gw_policy_v4_v2` (renombrado de `_v4` en 1.20), `cilium_l2_responder_v4/v6`, `cilium_mcast_*`, `cilium_cidr_v4_fix/dyn` (prefiltro XDP), `cilium_encrypt_state`, `cilium_auth_map`, `cilium_policystats`, `cilium_ratelimit`, `cilium_throttle`, `cilium_lb_act`/`cilium_lb_fct` (seguimiento de conexiones activas, desactivado de forma predeterminada) y mapas scratch por CPU (`cilium_tail_call_buffer4/6`, `cilium_nodeport_nat_buffer`, `cilium_xdp_scratch`, `cilium_percpu_trace_id`).

### 4.4 Indicadores de dimensionamiento

| Indicador (Helm) | Predeterminado (1.20.2) | Afecta a |
|---|---|---|
| `--bpf-map-dynamic-size-ratio` (`bpf.mapDynamicSizeRatio`) | 0.0025 (0.25 % de RAM); el **dimensionamiento dinámico está activado de forma predeterminada** | CT TCP/no TCP, NAT, NAT inverso de socket; el mapa de vecinos de NodePort sigue el tamaño de NAT (la ayuda del indicador dice «mapas BPF de CT, NAT y políticas», pero el código de dimensionamiento no ajusta los mapas de políticas) |
| `--bpf-ct-global-tcp-max` (`bpf.ctTcpMax`) | 524288 | CT TCP |
| `--bpf-ct-global-any-max` (`bpf.ctAnyMax`) | 262144 | CT no TCP |
| `--bpf-nat-global-max` (`bpf.natMax`) | 524288 | NAT; limitado a 2/3 de la suma de CT con una advertencia |
| `--bpf-neigh-global-max` (`bpf.neighMax`) | 524288 | vecinos de NodePort |
| `--bpf-policy-map-max` (`bpf.policyMapMax`) | 16384 por endpoint (máximo 65536) | políticas |
| `--bpf-fragments-map-max` | 8192 | fragmentos |
| `--bpf-node-map-max` | 16384 | mapa de nodos |
| `--bpf-lb-map-max` (`bpf.lbMapMax`) | 65536 | valor alternativo para seis indicadores por mapa de LB (`--bpf-lb-service-map-max`, `-service-backend-map-max`, `-rev-nat-map-max`, `-affinity-map-max`, `-source-range-map-max`, `-maglev-map-max`); cada uno vale 0 de forma predeterminada = usar `lb-map-max`. Está en el código (`pkg/loadbalancer/config.go`), pero no en la referencia de comandos generada, que solo muestra `--bpf-lb-map-max` |
| `--bpf-sock-rev-map-max` | dinámico; de forma predeterminada usa el tamaño de CT-any | mapa inverso de socket |
| `bpf.distributedLRU.enabled` | false | listas LRU libres por CPU; se usa con mapas más grandes |
| `bpf.preallocateMaps` | false | intercambia memoria por menor latencia de inserción |

El dimensionamiento dinámico calcula `entries = default_entries * (ratio * RAM) / total_default_bytes`, con un mínimo por mapa (CT TCP 128 Ki, CT cualquiera 64 Ki, NAT 128 Ki, socket inverso 64 Ki) y un máximo de 16 Mi (2^24). **Al definir explícitamente un indicador se desactiva el dimensionamiento dinámico solo para ese mapa.** Cuando aplica el ajuste, el agente registra `option <name> set by dynamic sizing to <N>`. El perfil de rendimiento ajustado de upstream usa una proporción de 0.08.

> Al cambiar el tamaño de un mapa, este se recrea y sus entradas se pierden hasta volver a poblarlo. Ajustar mapas LB o CT en un nodo activo interrumpe las conexiones establecidas. Programa estos cambios como una operación gradual por nodos.

Supervisa `cilium_bpf_map_pressure{map_name}` (se emite por encima de `--bpf-policy-map-pressure-metrics-threshold`, cuyo valor predeterminado es 0.1), `cilium_bpf_map_capacity` y `cilium_bpf_map_ops_total`.

## 5. Del agente al kernel: compilar, cargar y conectar

### 5.1 Flujo

```
agent start
  |  write node headers  (StateDir/globals: node_config.h, netdev_config.h, ...)
  |  hash node config -> if changed, wipe template cache (StateDir/templates)
  v
template config hash (compile-time #defines only)
  |  cache hit?  -> reuse StateDir/templates/<sha>/bpf_lxc.o
  |  miss        -> clang -O2 --target=bpf -mcpu=v3|v2|v1 ... -> new ELF template
  v
LoadCollection (per endpoint / device)
  |  copy spec -> patch maps -> rename maps (cilium_calls -> cilium_calls_<id>, cilium_policy -> cilium_policy_v3_<id>)
  |  write .rodata.config (endpoint ID, IPs, MAC, ifindex, feature switches)
  |  dead-code analysis -> remove unused tail calls and maps
  |  fill tail-call arrays from BTF decl tags
  |  load into kernel (verifier); reuse pinned global maps, replace incompatible ones
  v
attach: policy progs into cilium_call_policy/egresscall_policy
        -> tcx/tc/netkit entry programs -> commit() map pins -> endpoint routes
```

### 5.2 Plantillas ELF y `.rodata.config`

El paso de compilación, que es costoso, sigue ejecutándose en el agente (la imagen del contenedor incluye clang/LLVM; para ejecutar el agente de forma nativa se necesita LLVM 18.1 o posterior). Para evitar compilar de nuevo por cada Pod, Cilium calcula el hash solo de la **configuración de plantilla**: indicadores `#define ENABLE_*` que cambian la estructura del código. Los endpoints con los mismos indicadores comparten un objeto en `StateDir/templates/<sha>/`. Puedes enumerarlos con `cilium-dbg bpf sha list`.

Los valores específicos de cada endpoint no se compilan. Son variables globales de la sección `.rodata.config`, declaradas con `DECLARE_CONFIG(type, name, desc)` y leídas con `CONFIG(name)`. Antes de la carga, el agente escribe los valores en una copia de la especificación; el kernel congela los datos de solo lectura, por lo que el verificador ve los valores como constantes y **elimina las ramas inactivas**. Esto requiere compatibilidad con eliminación de código muerto (kernel 5.1 o posterior). Las estructuras del lado Go se generan con `dpgen` a partir de etiquetas BTF decl-tag (`pkg/datapath/config/*_config.go`). Las constantes efectivas se vuelcan como JSON por endpoint/dispositivo (por ejemplo, `bpf_lxc.json`) en el directorio de estado y se incluyen en `cilium sysdump`.

Cada versión mueve más indicadores `#define` a `.rodata.config`, lo que reduce la cantidad de plantillas distintas y recompilaciones. Un recuento de las declaraciones `DECLARE_CONFIG`/`NODE_CONFIG` con grep en el árbol BPF da 18 (1.18.14), 43 (1.19.8), 73 (1.20.2) y 104 (**[1.21 pre-release]**, v1.21.0-pre.3), usando `grep -rE '^\s*(DECLARE_CONFIG|NODE_CONFIG)\(' bpf --include=*.h --include=*.c | wc -l` en el checkout de cada etiqueta. Interpreta estas cifras como una tendencia aproximada, no como una API.

### 5.3 Regeneración

En cada regeneración del endpoint, el agente calcula el hash del encabezado del endpoint. Si coincide con el anterior, solo sincroniza los mapas (`RegenerateWithoutDatapath`, el caso de cambio de política). De lo contrario, escribe los encabezados y vuelve a cargar el datapath. Métricas pertinentes: `cilium_endpoint_regenerations_total`, `endpoint_regeneration_time_stats_seconds` (etapas como `bpfCompilation`, `bpfLoadProg`, `bpfWaitForELF`) y `cilium_endpoint_component_status` (nuevo en 1.20).

El orden importa: `commit()` de los pins de mapas debe ejecutarse después de conectar todos los programas de entrada; de lo contrario, un programa nuevo podría hacer una tail call a un arreglo anterior y «perder» la llamada.

### 5.4 Pruebas del verificador

Cilium compila y prueba las compilaciones con el máximo de funciones frente a kernels 5.10, 6.1 y net-next (`bpf/complexity-tests/`). Los fallos del verificador durante la carga se registran con toda la salida del verificador.

## 6. Matriz de kernel y funciones

### 6.1 Requisitos estrictos de inicio (1.20.2)

El agente se niega a iniciar si falta alguno de estos elementos: `bpf()` y JIT; tc-bpf o tcx; `bpf_skb_change_tail`; `bpf_get_socket_cookie`; `bpf_get_current_cgroup_id`; `bpf_fib_lookup`; eliminación de código muerto; `skb->queue_mapping` escribible; programas grandes (1 millón de instrucciones); `bpf_skb_adjust_room` con `BPF_ADJ_ROOM_MAC`; `bpf_jiffies64`; `BPF_MAP_LOOKUP_BATCH`; `bpf_get_netns_cookie`; `bpf_sk_assign`; `bpf_get_cgroup_classid`; `bpf_perf_event_output` en cgroup sock_addr; `bpf_csum_level`; `bpf_skb_change_head`; `bpf_redirect_neigh`; `bpf_redirect_peer`. Por eso, la versión mínima documentada es **kernel 5.10** (RHEL 8.10 con 4.18 es una excepción explícita debido a los backports de Red Hat). El sondeo heredado de encabezados por helper ya no contiene comprobaciones; la base 5.10 da por hecho que todos los helpers están disponibles.

Entre las opciones de configuración del kernel indicadas upstream están `BPF`, `BPF_SYSCALL`, `BPF_JIT`, `NET_CLS_BPF`, `NET_CLS_ACT`, `NET_SCH_INGRESS`, `CGROUPS`, `CGROUP_BPF`, `DEBUG_INFO_BTF` y funciones adicionales como `VXLAN`, `GENEVE`, `NET_SCH_FQ` (administrador de ancho de banda) y `NETKIT`.

### 6.2 Aceleradores opcionales

| Función | Kernel mínimo | Madurez / nota |
|---|---|---|
| Enlaces tcx | 6.6 | predeterminado cuando está disponible; si no, se usa tc heredado |
| netkit (`bpf.datapathMode`) | 6.8 (documentación; el texto del sondeo en el código indica 6.7) | beta |
| BIG TCP IPv6 | 5.19 | requiere un controlador NIC compatible |
| BIG TCP IPv4 | 6.3 | |
| BBR para el administrador de ancho de banda | 5.18 | |
| Datapath de comprobación de estado de LB | 5.12 | |
| Multicast | 5.10 en AMD64; 6.0 en AArch64 | |
| kfunc `bpf_sock_destroy` | no se indica en el código fuente | recurre automáticamente a `sock_diag` mediante netlink |

El datapath no utiliza helpers de reubicación CO-RE (al buscar `preserve_access_index` en el árbol `bpf/` de 1.20.2, solo aparece un comentario de encabezado UAPI): compila contra sus propios encabezados y el UAPI `__sk_buff`. Usa BTF para las definiciones de mapas, la sección de datos `.rodata.config` y las decl-tags; se requiere `CONFIG_DEBUG_INFO_BTF=y`.

En EKS, comprueba el kernel real del nodo con `uname -r` y `cilium-dbg status` antes de activar ajustes que dependan de tcx o netkit; este capítulo no presupone qué kernel incluye cada AMI.

## 7. Traza detallada: Pod -> Servicio -> Pod

Configuración ilustrativa (los números son ejemplos; las estructuras se basan en el código fuente): Pod cliente `C` 10.0.1.10, identidad 4711, ID de endpoint 312, en el nodo A. Servicio `web` ClusterIP 10.100.0.20:80/TCP, `rev_nat_index` 42 y dos backends: B1 10.0.1.55 (nodo A, endpoint 87) y B2 10.0.2.77 (nodo B), ambos con identidad 9001. Ajustes: IPv4, veth, tcx, enrutamiento de host BPF, `kubeProxyReplacement: true` (lo que activa socket-LB) y `socketLB.hostNamespaceOnly=false`.

### Salto 0: `connect()` en el Pod, `cgroup/connect4` (`cil_sock4_connect`)

1. Busca en `cilium_lb4_services_v2` con `{10.100.0.20, 80, TCP, slot 0, scope 0}`. Si no hay entrada, deja intacta la sockaddr; en este ejemplo hay una entrada con `count=2`.
2. Elige un slot: aleatorio para TCP (cookie de socket para UDP). Busca la clave de servicio con ese slot para obtener `backend_id`; luego consulta `cilium_lb4_backends_v3[backend_id]` para obtener 10.0.2.77:80. Si está configurado `sessionAffinity`, primero consulta `cilium_lb4_affinity`.
3. Escribe `cilium_lb4_reverse_sk[{cookie, 10.0.2.77, 80}] = {10.100.0.20, 80, 42}`.
4. Reescribe `user_ip4/user_port` en la llamada al sistema. **El paquete no pasa por DNAT en la red.** `tcpdump` dentro del Pod muestra la IP del backend, algo que suele sorprender. Cuando está habilitado el seguimiento de socket-LB, se emite un evento `trace_sock_notify`.

### Salto 1: el SYN sale del Pod, `cil_from_container` en el veth del lado del host (ingress tcx)

| Paso | Acción | Mapas afectados |
|---|---|---|
| 1 | limpia los metadatos, `send_trace_notify(TRACE_FROM_LXC)` (sujeto a agregación) | `cilium_events` |
| 2 | tail call al slot 7 (IPv4 desde LXC) | `cilium_calls_00312` |
| 3 | se omite el LB por paquete (socket-LB ya tradujo la dirección) | ninguno |
| 4 | tail call al slot 30 (egreso CT): búsqueda `CT_NEW`; tupla almacenada en el búfer por CPU | `cilium_ct4_global`, `cilium_tail_call_buffer4` |
| 5 | tail call al slot 26 (`handle_ipv4_from_lxc`) | `cilium_calls_00312` |
| 6 | resuelve la identidad de destino: la búsqueda LPM de 10.0.2.77 devuelve la identidad 9001 y (con overlay) el extremo del túnel del nodo B; si no hay coincidencia, usa `world` | `cilium_ipcache_v2` |
| 7 | política de egreso: `{egress=1, sec_label=9001, TCP, 80}`, búsqueda en dos pasadas; permite o descarta; un flujo nuevo permitido emite un evento de veredicto de política | `cilium_policy_v3_00312`, `cilium_events`, `cilium_metrics` si se descarta |
| 8 | si `proxy_port != 0`: marca el tráfico para el proxy, activa la marca CT `proxy_redirect` y lo pasa a la pila (sección 3.5) | |
| 9 | `ct_create4(CT_EGRESS)`: inserta la entrada; el SYN dura 1 min hasta el ACK y luego 2 h 13 min 20 s | `cilium_ct4_global` (y CT-any para ICMP relacionado) |
| 10 | elige la ruta de reenvío (a continuación) | |

Opciones de reenvío en el paso 10:

- **Destino en el mismo nodo** (B1): `cilium_lxc[dst]` devuelve `{ifindex, lxc_id=87, mac, node_mac}`; se reescribe el encabezado L2 y se establecen los metadatos (`CB_SRC_LABEL=4711`, indicadores de entrega); después, `tail_call_policy(87)` ejecuta el `cil_lxc_policy` de B1 desde `cilium_call_policy` (salto 3).
- **Remoto, overlay**: `flag_has_tunnel_ep` está establecido en el valor de ipcache, por lo que `bpf_skb_set_tunnel_key` define `tunnel_id` = identidad del origen 4711 y `remote_ipv4` = nodo B; el paquete se redirige a `cilium_vxlan`/`cilium_geneve`, donde `cil_to_overlay` se ejecuta antes de la encapsulación del kernel. El tráfico Pod a Pod no pasa por masquerade.
- **Remoto, enrutamiento nativo con enrutamiento de host BPF**: ejecuta `bpf_fib_lookup` y luego redirige a la NIC. Con `bpf.hostLegacyRouting=true`, en su lugar devuelve OK a la pila del kernel y netfilter. No hay VNI; el receptor vuelve a obtener la identidad de origen desde ipcache usando la IP de origen (o desde las marcas en IPsec/WireGuard).

### Salto 2 (solo remoto): recepción en el nodo B

- Overlay: `cil_from_netdev` pasa UDP 8472 (VXLAN) / 6081 (Geneve) a la pila; el kernel desencapsula el paquete en `cilium_vxlan`; `cil_from_overlay` lee `bpf_skb_get_tunnel_key`, asigna `tunnel_id` a la **identidad de origen** (se rechaza una identidad de host con `DROP_INVALID_IDENTITY`), la guarda en `CB_SRC_LABEL`, emite `TRACE_FROM_OVERLAY`, consulta `cilium_lxc[10.0.2.77]` y llama a `tail_call_policy(ep)`.
- Enrutamiento nativo: `cil_from_netdev` realiza los mismos pasos usando la identidad de origen de `cilium_ipcache_v2[src ip]`.

### Salto 3: política de ingreso y entrega al destino

1. `cil_lxc_policy` ejecuta la tail call de ingreso CT: consulta `cilium_ct4_global`, `CT_NEW`.
2. Política de ingreso: `cilium_policy_v3_00087` con `{egress=0, sec_label=4711, TCP, 80}`. Se emite un evento de veredicto.
3. `ct_create4(CT_INGRESS)` registra `src_sec_id=4711`, `from_tunnel` y `proxy_redirect`.
4. Entrega: `bpf_redirect_peer` al espacio de nombres de red del Pod (veth) o `redirect` (netkit), con evento `TRACE_TO_LXC`. La pila del backend responde con origen 10.0.2.77; nunca ve el ClusterIP.

### Salto 4: respuesta y cierre

- El `cil_from_container` de B encuentra la entrada CT de ingreso como `CT_REPLY`, por lo que **omite la política**; el paquete se encapsula de vuelta con VNI 9001 (o se enruta de forma nativa). En el nodo A, `tail_call_policy(312)` ejecuta el programa de política de C; `CT_REPLY` omite la política y `redirect_peer` entrega el paquete a C.
- Inversión de socket-LB: la aplicación cree que se comunica con 10.100.0.20. Los hooks `getpeername` y `recvmsg` consultan `cilium_lb4_reverse_sk[{cookie, 10.0.2.77, 80}]` y devuelven la dirección del servicio.
- Sin socket-LB (modo solo espacio de nombres del host, LB L7, SCTP): en el salto 1 se realiza DNAT en `bpf_lxc` y se guarda `rev_nat_index` en la entrada CT; las respuestas usan `cilium_lb4_reverse_nat[rev_nat_index]` para restaurar el origen.
- FIN/RST establece `tx/rx_closing` y reduce la duración al tiempo de espera FIN (10 s); la recolección de basura CT del agente elimina las entradas vencidas. Las entradas `cilium_lb4_reverse_sk` permanecen hasta que se expulsen por LRU o se ejecute `cil_sock_release`.

### Lista de consultas por salto

| Salto | Programa | Consultas / escrituras |
|---|---|---|
| 0 | `cil_sock4_connect` | `lb4_services_v2` x2, `lb4_backends_v3`, `lb4_affinity` (opcional), escribe `lb4_reverse_sk` |
| 1 | `cil_from_container` + tails | `calls_<id>` x3, `tail_call_buffer4`, `ct4_global` (consulta, creación), `ipcache_v2`, `policy_v3_<src>` (egreso), `cilium_lxc`, `call_policy`, `events`, `metrics` |
| 2 | `cil_from_overlay` / `cil_from_netdev` | clave de túnel o `ipcache_v2`, `cilium_lxc`, `call_policy` |
| 3 | `cil_lxc_policy` (destino) | `ct4_global`, `policy_v3_<dst>` (ingreso), creación en `ct4_global`, `events` |
| 4 | ruta de respuesta, `recvmsg` | `ct4_global` (respuesta), `lb4_reverse_sk` o `lb4_reverse_nat` |

### Cambio de comportamiento en 1.20 que afecta a esta traza

Con el reemplazo de kube-proxy y `socketLB.enabled=false` o `socketLB.hostNamespaceOnly=true`, las conexiones de Pod a NodePort dentro del clúster ahora se balancean en el hook tc del **Pod cliente**. Las NetworkPolicies de egreso del cliente y de ingreso del backend deben permitir el tráfico correspondiente.

## 8. Canalización de eventos de Hubble

```
BPF program --ctx_event_output--> cilium_events (PERF_EVENT_ARRAY, per CPU)
      |   trace_notify / drop_notify / policy_verdict_notify / debug / capture / trace_sock_notify
      v
agent monitor (pkg/monitor/agent): perf reader, 64 pages per CPU, opened only if a consumer exists
      |-- lost samples (kernel buffer overrun) -> MonitorStatus.Lost
      |-- unix-socket listeners (cilium-dbg monitor), queue --monitor-queue-size
      v
Hubble consumer -> observer queue (--hubble-event-queue-size)
      |   full => LostEvent source=OBSERVER_EVENTS_QUEUE, hubble_lost_events_total
      v
Hubble parser (identity/endpoint/service enrichment) -> ring buffer (--hubble-event-buffer-capacity)
      v
gRPC: hubble observe / Relay / UI
```

Aspectos que conviene recordar:

- En 1.20 y 1.21-pre.3, el mapa de eventos es un **arreglo de eventos perf**, no un búfer circular BPF.
- Control de volumen en el datapath: `bpf.monitorAggregation` (valor predeterminado de Helm: `medium`; indicador del agente: `None`). En `medium` y niveles superiores se suprimen las trazas de recepción entre nodos y los flujos establecidos solo se notifican cuando transcurre `bpf.monitorInterval` (5 s) o se observa un indicador de `bpf.monitorFlags`. Controles por clase: `bpf.events.drop.enabled`, `bpf.events.policyVerdict.enabled`, `bpf.events.trace.enabled` (todos habilitados de forma predeterminada) y el límite experimental `bpf.events.default.rateLimit` / `burstLimit` (ambos deben tener valor o ambos ser cero).
- Los flujos de `hubble observe` viven en un búfer circular en memoria (`hubble.eventBufferCapacity`, debe ser 2^n - 1; predeterminado 4095, máximo 65535). La entrega es de mejor esfuerzo: tanto los desbordamientos del búfer perf como los de la cola del observador provocan pérdida de eventos y se cuentan con etiquetas `source` distintas (`perf_event_ring_buffer`, `observer_events_queue`).
- Los eventos L7 no se originan en BPF; llegan como eventos del agente enviados por los proxies.

## 9. Herramientas de inspección

### 9.1 cilium-dbg

```bash
CILIUM_POD=$(kubectl -n kube-system get pod -l k8s-app=cilium -o jsonpath='{.items[0].metadata.name}')
kc() { kubectl -n kube-system exec "$CILIUM_POD" -c cilium-agent -- "$@"; }

kc cilium-dbg status --verbose         # KPR, datapath mode (configured vs operational), BPF map pressure
kc cilium-dbg bpf fs show              # bpffs mount
kc cilium-dbg map list -v              # pinned maps and sizes
kc cilium-dbg bpf endpoint list        # cilium_lxc
kc cilium-dbg bpf ipcache list         # identity + tunnel endpoint per IP/CIDR
kc cilium-dbg bpf ct list global       # conntrack
kc cilium-dbg bpf nat list             # SNAT maps
kc cilium-dbg bpf lb list --frontends  # also --backends, --revnat, --source-ranges
kc cilium-dbg bpf lb maglev list       # only with Maglev
kc cilium-dbg bpf policy get --all -n  # every cilium_policy_v3_*, numeric identities
kc cilium-dbg bpf metrics list         # cilium_metrics
kc cilium-dbg bpf config list          # cilium_runtime_config
kc cilium-dbg bpf sha list             # compiled ELF templates
kc cilium-dbg monitor -t drop -t policy-verdict --related-to <ENDPOINT_ID>
```

`cilium-dbg map get <name>` muestra la vista almacenada en caché por el agente, que no siempre coincide con el kernel; `cilium-dbg map events <name>` muestra el registro de actualizaciones. No hay subcomandos `bpf tunnel` ni `bpf calls`.

### 9.2 bpftool (ejecútalo en el nodo)

```bash
sudo bpftool net show                                     # tcx/tc/xdp/netkit attachments per device
sudo bpftool prog show | grep -E 'cil_|tail_'             # entry and tail programs
sudo bpftool map show pinned /sys/fs/bpf/tc/globals/cilium_ct4_global
sudo bpftool cgroup tree /run/cilium/cgroupv2             # socket-LB hooks
sudo ls /sys/fs/bpf/cilium/endpoints/*/links /sys/fs/bpf/cilium/devices/*/links
```

Trata los mapas fijados como de solo lectura. No escribas bytes sin procesar en los mapas de Cilium: el estado en caché del agente dejaría de coincidir. Es posible que la imagen del agente no incluya `bpftool`; esta revisión no lo comprobó. Si falta, ejecútalo desde el nodo o desde un Pod de depuración.

**[1.21 pre-release]** `--enable-bpf-stats` (Helm `bpf.stats.enabled`, desactivado de forma predeterminada) habilita las estadísticas de tiempo de ejecución del kernel y agrega el comando hive `bpf/stats/report`, expuesto como `cilium-dbg bpf stats report` (`--sort avg|total|runs`, `--pod`, `--device`, `--json`), que muestra el número de ejecuciones y el tiempo promedio por programa.

## 10. Plugins de datapath (beta, nuevos en 1.20)

Los plugins de datapath permiten que un componente externo ejecute sus propios programas BPF alrededor de los puntos de entrada de Cilium sin bifurcar el datapath.

- Habilítalos con Helm `datapathPlugins.enabled=true` (desactivado de forma predeterminada; indicador del agente `--enable-datapath-plugins`); directorio de estado `datapathPlugins.stateDir` (predeterminado `/var/run/cilium/plugins`).
- Registra un plugin con la CRD `CiliumDatapathPlugin` (`cilium.io/v2alpha1`): `spec.attachmentPolicy: Always | BestEffort` y `spec.version`.
- El agente se comunica con cada plugin por gRPC en `<stateDir>/<name>/plugin.sock` mediante las llamadas `PrepareCollection` e `InstrumentCollection`. Cilium genera un despachador para ejecutar programas plugin de tipo `BPF_PROG_TYPE_EXT` (freplace) antes o después de los programas de entrada de Cilium para hooks tc, XDP y cgroup sock.
- El Pod del plugin necesita `SYS_ADMIN`. Crear, actualizar o eliminar una CR de plugin provoca la reinicialización completa del datapath. No hay garantía de compatibilidad entre versiones. No está disponible en 1.18 ni 1.19.

Úsalos para experimentos e integraciones de proveedores, no como un punto de extensión general para cambios de producción todavía.

## 11. Laboratorios

Requisitos previos para todos los laboratorios: un clúster Linux descartable con Cilium 1.20.2 y reemplazo de kube-proxy, acceso al shell de los nodos (SSM o equivalente) y `kubectl`. Ninguno de estos pasos expone recursos fuera del clúster.

### Laboratorio 1: inventariar cada programa Cilium en un nodo

1. En un nodo, ejecuta `sudo bpftool net show` y `sudo bpftool prog show | grep cil_`.
2. Enumera los enlaces fijados con `sudo ls /sys/fs/bpf/cilium/endpoints/*/links /sys/fs/bpf/cilium/devices/*/links`.
3. Ejecuta `kc cilium-dbg bpf sha list`.

Resultado esperado: `cil_from_netdev` en cada dispositivo nativo, `cil_from_container` por dispositivo `lxc*`, `cil_to_host`/`cil_from_host` en `cilium_host` y (con overlay) `cil_from_overlay`/`cil_to_overlay` en `cilium_vxlan` o `cilium_geneve`. En kernels 6.6 o posteriores, existen pins de enlaces por endpoint; en kernels anteriores, `tc filter show dev <lxc> ingress` muestra el filtro heredado. Limpieza: ninguna (solo lectura).

### Laboratorio 2: los cambios de política no recompilan

1. Anota `kc cilium-dbg bpf sha list` y el mapa del endpoint con `kc cilium-dbg bpf policy get <ENDPOINT_ID>`.
2. Aplica un `CiliumNetworkPolicy` que permita tráfico desde clientes con una etiqueta de cliente hacia TCP/80 en un backend de prueba.
3. Vuelve a ejecutar ambos comandos.

Resultado esperado: aparece una entrada nueva de ingreso con la identidad numérica del cliente en el mapa de políticas del endpoint backend; la lista de plantillas no cambia. Añade una regla de denegación explícita y observa una entrada con el indicador de denegación. Limpieza: elimina los objetos de política. Practica en un espacio de nombres sin otras políticas, porque interactúa con la denegación predeterminada del clúster.

### Laboratorio 3: seguir una conexión en los mapas

1. Crea un Deployment con dos réplicas y un Service ClusterIP en un espacio de nombres de prueba, además de un Pod cliente.
2. Desde el cliente, ejecuta `curl` contra el ClusterIP. En otra terminal del nodo del cliente, ejecuta `cilium-dbg monitor -t trace -t policy-verdict --related-to <CLIENT_ENDPOINT_ID>`.
3. Ejecuta `bpf lb list --frontends`, `--backends` y `bpf ct list global | grep <backend ip>`.
4. Compara la salida de `tcpdump -ni eth0 port 80` en el netns del cliente con la IP del Service.

Resultado esperado: el frontend del servicio enumera los backends; existe una entrada CT para el backend seleccionado y, con socket-LB habilitado, la captura muestra la IP del backend, no el ClusterIP. Opcional: con `socketLB.hostNamespaceOnly=true`, la captura muestra el ClusterIP (LB por paquete). Este cambio modifica el balanceo de tráfico en todo el clúster; aplícalo solo en un clúster de prueba y revierte restaurando el valor anterior de Helm.

### Laboratorio 4: contabilizar pérdidas de Hubble

1. En un clúster de prueba, asigna un valor deliberadamente pequeño a `hubble.eventQueueSize` (para revertirlo, restaura el valor anterior; esto reinicia los agentes).
2. Genera carga con una herramienta de tráfico en un espacio de nombres de prueba.
3. Consulta las métricas del agente para `hubble_lost_events_total`, agrupadas por `source`.

Resultado esperado: `observer_events_queue` aumenta cuando la cola se desborda y el agente registra «hubble events queue is full». Los desbordamientos del búfer perf aparecerían como `perf_event_ring_buffer`.

### Laboratorio 5 (avanzado): netkit en un grupo de nodos nuevo

Solo en nodos con un kernel compatible con netkit. Instala o actualiza un grupo de nodos nuevo con `bpf.datapathMode=auto`; después, comprueba con `cilium-dbg status` el modo configurado frente al operativo, con `ip -d link show` el tipo de dispositivo y con `bpftool net show` las conexiones netkit. Si se combina `bpf.tproxy=true` con netkit en 1.19 o posterior, el agente rechaza netkit (`auto` vuelve a veth). Para revertirlo, no cambies in situ los Pods veth existentes; vacía y reemplaza los nodos.

## Diferencias entre versiones

| Elemento | 1.18.14 | 1.19.8 | 1.20.2 | 1.21.0-pre.3 |
|---|---|---|---|---|
| Kernel mínimo (documentación) | 5.10 (4.18 en RHEL 8.10) | 5.10 | 5.10 | 5.10 |
| `bpf_network.c` | presente | presente | **eliminado** | eliminado |
| `CILIUM_CALL_SIZE` | 48 | 49 | 50 | 50 |
| Variables de configuración (recuento grep) | 18 | 43 | 73 | 104 |
| Nombre del mapa de políticas | `cilium_policy_v2_` | `cilium_policy_v2_` | `cilium_policy_v3_` | `cilium_policy_v3_` (bits de autenticación reservados) |
| Mapa de nodos | v1 + v2 | solo v2 | v2 | v2 |
| Mapa de gateway de egreso | `..._v4` | `..._v4` | `..._v4_v2` | `..._v4_v2` |
| Mapa `cilium_devices` | no | no | sí | sí |
| Valores de `--datapath-mode` | veth, netkit, netkit-l2 | igual | + `auto` | + `auto` |
| `bpf.tproxy` | beta (no se encontró comprobación netkit) | beta; rechaza netkit | beta; rechaza netkit | beta; rechaza netkit |
| Plugins de datapath | no | no | sí (beta) | sí |
| Mapa de autenticación mutua (`--bpf-auth-map-max`) | sí | sí | sí; autenticación mutua obsoleta | eliminado |
| `--enable-bpf-stats` | no | no | no | yes |
| `--node-port-mode`, `--node-port-algorithm` | presentes | presentes | eliminados (usar `--bpf-lb-mode`, `--bpf-lb-algorithm`) | eliminados |
| Respuesta ICMP ante denegación de política | no | no | sí (slots tail 48-49) | sí |

Las notas de actualización de 1.21 en el árbol de la versión preliminar todavía conservan el texto de 1.20; por tanto, aún no existe una diferencia de 1.21 autorizada.

## Solución de problemas

| Síntoma | Causa probable | Comprobación |
|---|---|---|
| Descartes con `DROP_EP_NOT_READY` (código -203) | el slot de política está vacío mientras se crea o elimina un endpoint | `cilium-dbg endpoint list`; puede ser transitorio durante cambios; si persiste, falla la regeneración |
| Descartes «Missed tail call» | el arreglo no está poblado o se rompió el orden de confirmación tras una recarga fallida | revisa errores de carga en el registro del agente; `cilium-dbg endpoint log <id>`; reinicia el Pod del agente |
| Fallan conexiones nuevas y `cilium_bpf_map_pressure` se acerca a 1 en un mapa CT | mapa CT/NAT lleno | `cilium-dbg map list -v`; aumenta `bpf.mapDynamicSizeRatio` o el máximo explícito; mantén NAT como máximo a 2/3 de CT; recuerda que cambiar el tamaño pierde entradas |
| Los servicios dejan de coincidir tras aumentar el volumen | se alcanzó el límite del mapa LB | `bpf.lbMapMax` (afecta a seis mapas); el cambio de tamaño interrumpe el tráfico |
| El agente no inicia: «Require support for tcx links» o errores de helper | kernel inferior a la base | `uname -r`, `cilium-dbg status`; migra a una AMI compatible |
| Los programas usan tc heredado en vez de tcx | kernel anterior a 6.6 o `enableTCX: false` | `bpftool net show`, `tc filter show` |
| Se rechaza netkit | falta un requisito (enrutamiento del host, masquerade BPF, KPR, tproxy o kernel) | motivo en el registro del agente; compara los modos configurado y operativo en `cilium-dbg status` |
| El verificador rechaza el programa durante la carga | combinación de funciones inusual o límite del kernel | salida completa del verificador en stderr del agente; compara con las compilaciones probadas en 5.10/6.1/net-next |
| `hubble observe` no muestra algunos flujos | pérdida en perf-buffer o cola del observador, agregación demasiado alta o búfer circular demasiado pequeño | `hubble_lost_events_total` por `source`; `bpf.monitorAggregation`; `hubble.eventBufferCapacity` |
| Una guía antigua recomienda volcar `cilium_tunnel_map` | el mapa se eliminó | usa `cilium-dbg bpf ipcache list` |
| Pod -> NodePort deja de funcionar tras actualizar a 1.20 con socket-LB desactivado o solo en el espacio de nombres del host | LB ahora se aplica en el hook tc del Pod cliente | permite el tráfico en las políticas de egreso del cliente e ingreso del backend |

## Límites de validación y fuentes

Los laboratorios no se ejecutaron en un clúster activo durante esta revisión; se verificaron los comandos y los indicadores frente al código fuente y la documentación upstream. Los ID, direcciones IP e identidades de la traza son ilustrativos. Los datos de origen se consultaron en el árbol de Cilium v1.20.2 (por ejemplo, `bpf/bpf_lxc.c`, `bpf/lib/tailcall.h`, `bpf/lib/policy.h`, `bpf/lib/eps.h`, `pkg/datapath/loader/tc.go`, `pkg/bpf/collection.go`, `Documentation/cmdref/cilium-agent.md`); las líneas donde aparecen las entradas cambian entre versiones, así que compruébalas en la etiqueta exacta que uses. No se verificó si `bpftool` viene en la imagen del agente ni la versión exacta del kernel que incorporó la kfunc `bpf_sock_destroy`; el informe de estadísticas **[1.21 pre-release]** se consultó en el código (`cilium-dbg/cmd/bpf_stats_report.go`), pero no se ejecutó.

- Requisitos del sistema para Cilium v1.20.2: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst
- Referencia de mapas: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/ebpf/maps.rst (nota: usa `cilium_ct_{4,6}_global`; los nombres reales son `cilium_ct4_global` y `cilium_ct6_global`)
- Código fuente BPF: https://github.com/cilium/cilium/tree/v1.20.2/bpf
- Cargador del datapath: https://github.com/cilium/cilium/tree/v1.20.2/pkg/datapath/loader
- Indicadores del agente: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/cmdref/cilium-agent.md
- Plugins de datapath: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/contributing/development/plugins.rst
- Notas de actualización: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc
- Ajuste del rendimiento (netkit, BIG TCP): https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/performance/tuning.rst
- Estadísticas BPF **[1.21 pre-release]**: https://github.com/cilium/cilium/tree/v1.21.0-pre.3/pkg/bpf/stats

## Cuestionario

Comprueba lo que aprendiste con el [cuestionario de la Parte 8](../../quizzes/networking/cilium/08-ebpf-datapath-internals-quiz.md).
