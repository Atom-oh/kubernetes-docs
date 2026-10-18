# Parte 11: BGP Control Plane, IP de balanceadores de carga y salida

> **Base de revisión**: Cilium 1.20.2 (estable, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Los elementos marcados **[versión preliminar 1.21]** proceden de v1.21.0-pre.3 y pueden cambiar antes de la disponibilidad general.
> **Última actualización**: 15 de octubre de 2026

Este capítulo cubre todo lo que conecta un clúster de Cilium con la red **fuera** de la red de Pods: anunciar rutas con BGP Control Plane, asignar y anunciar IP de LoadBalancer (LB IPAM, anuncios L2 y Node IPAM), dirigir el tráfico saliente (Egress Gateway), interceptar tráfico dirigido a backends locales al nodo (Local Redirect Policy), preferir backends cercanos (distribución del tráfico) y los puntos de entrada de capa 7 (Ingress y Gateway API). Termina con dos topologías de referencia: switches ToR locales con BGP y EKS detrás de CloudFront.

Capítulos relacionados: [análisis detallado de IPAM](10-ipam-deep-dive.md) (Pod IPAM decide qué puede anunciar BGP), [enrutamiento superpuesto y nativo](09-overlay-native-routing.md), [detalles internos del plano de datos eBPF](08-ebpf-datapath-internals.md) (el reemplazo de kube-proxy en que se basa el balanceo de Services de abajo) y [ClusterMesh y actualización](13-clustermesh-install-upgrade.md).

## 1. Cómo encaja el tráfico norte-sur

A menudo se confunden tres tareas distintas bajo el término «balanceador de carga»:

| Tarea | Pregunta que responde | Componente de Cilium |
|---|---|---|
| Asignación de direcciones | ¿Qué IP recibe este Service? | LB IPAM (`CiliumLoadBalancerIPPool`), Node IPAM o un controlador de nube |
| Alcance | ¿Cómo aprende la red externa que esa IP está en estos nodos? | BGP Control Plane, anuncios L2 o balanceador de carga de nube |
| Balanceo de carga | Cuando un paquete llega a un nodo, ¿qué Pod backend lo recibe? | Balanceo de Services de eBPF (reemplazo de kube-proxy) y Envoy para capa 7 |

Por tanto, BGP Control Plane, los anuncios L2 y LB IPAM son funciones **independientes** que se combinan. Una combinación habitual en entornos locales es `LB IPAM` (asigna la VIP) + `BGP Control Plane` (la anuncia) + reemplazo eBPF de kube-proxy (distribuye el tráfico). `loadBalancerClass` del Service determina qué función lo administra (sección 6).

**Lo que BGP no hace.** BGP Control Plane solo *anuncia* rutas. No programa el plano de datos local y no instala en el kernel ni en los mapas eBPF las rutas aprendidas de los peers. No puede crear conectividad dentro del clúster ([descripción general upstream](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst)). El enrutamiento Pod a Pod entre nodos corresponde al enrutamiento superpuesto o nativo ([parte 9](09-overlay-native-routing.md)).

## 2. BGP Control Plane v2

**Madurez**: v2 (CRD `cilium.io/v2`) es la única versión de BGP Control Plane en 1.19, 1.20 y la versión preliminar 1.21. `CiliumBGPPeeringPolicy` de v1 se eliminó en 1.19 (sección 2.9).

### 2.1 Arquitectura

```
                     user-authored (cluster-scoped, cilium.io/v2)
   +--------------------+   +-------------------+   +----------------------+
   | CiliumBGPCluster   |-->| CiliumBGPPeer     |   | CiliumBGPAdvertise-  |
   | Config             |   | Config            |<--| ment (matched by     |
   |  nodeSelector      |   |  timers, GR, MD5, |   |  LABEL from PeerCfg) |
   |  bgpInstances[]    |   |  families[]       |   +----------------------+
   |  peers[] -> ref    |   +-------------------+
   +---------+----------+
             | watched by cilium-operator
             v
   +--------------------+   (one per selected node, name == node name,
   | CiliumBGPNodeConfig|    read-only for users; status reports sessions)
   +---------+----------+   +--------------------------+
             | watched by   | CiliumBGPNodeConfig-     |  optional per-node
             | the node's   | Override (name == node)  |  routerID/ASN/source
             v agent        +--------------------------+
   +--------------------------------------------+
   | cilium-agent: BGP "router manager"         |
   |   one embedded GoBGP instance per bgpInstance
   |   inputs: NodeConfig, PeerConfig, Advert., |
   |   Secret, Services/EndpointSlices/backends,|
   |   CiliumNode PodCIDRs / CiliumPodIPPool    |
   +----------------------+---------------------+
                          | TCP/179 (agent dials out; active-only by default)
                          v
                    ToR / upstream router
```

Flujo de control (según [`pkg/bgp/README.md`](https://github.com/cilium/cilium/blob/v1.20.2/pkg/bgp/README.md)): el operador observa `CiliumBGPClusterConfig` y los objetos `CiliumBGPPeerConfig` / `CiliumBGPAdvertisement` a los que hace referencia, y crea, actualiza o elimina un `CiliumBGPNodeConfig` por cada nodo que coincide con `nodeSelector` de la configuración del clúster. Cada agente observa solo su propio `CiliumBGPNodeConfig`, además de las configuraciones de peers y anuncios, Secrets, Services y (con varios pools) `CiliumPodIPPool`, y reconcilia sus instancias de GoBGP. Por eso el operador debe estar ejecutándose para que se propaguen los cambios de configuración.

El speaker es GoBGP integrado en el agente. GoBGP es la única implementación de enrutador compatible. La biblioteca integrada pasó de `gobgp/v3` (1.19) a `gobgp/v4` (1.20.2 y 1.21.0-pre.3; consulta `go.mod` de cada etiqueta). Se admiten IPv4 e IPv6, de pila simple y doble, pero solo se pueden anunciar las familias de direcciones que el propio agente use.

### 2.2 Habilitación

```yaml
bgpControlPlane:
  enabled: true              # default false
  statusReport:
    enabled: true            # default true; disable on very large clusters to cut API load
  routerIDAllocation:
    mode: default            # default | ip-pool
```

```bash
helm upgrade cilium cilium/cilium -n kube-system --reuse-values \
  --set bgpControlPlane.enabled=true
kubectl -n kube-system rollout restart ds/cilium deploy/cilium-operator
```

| Valor de Helm | Indicador del agente/operador | Valor predeterminado | Descripción |
|---|---|---|---|
| `bgpControlPlane.enabled` | `--enable-bgp-control-plane` | `false` | Habilita la función |
| `bgpControlPlane.secretsNamespace.name` / `.create` | `--bgp-secrets-namespace` | `kube-system` / `false` | Namespace desde el que se leen los Secrets de `authSecretRef`; el chart puede crearlo |
| `bgpControlPlane.statusReport.enabled` | `--enable-bgp-control-plane-status-report` | `true` | Escribe el estado de sesión en `CiliumBGPNodeConfig.status`; al deshabilitarlo se borra el estado |
| `bgpControlPlane.routerIDAllocation.mode` / `.ipPool` | `--bgp-router-id-allocation-mode` / `-ip-pool` | `default` / vacío | Estrategia de Router ID (sección 2.7) |
| `bgpControlPlane.legacyOriginAttribute.enabled` | `--enable-bgp-legacy-origin-attribute` | `false` | Las rutas `LoadBalancerIP` llevan ORIGIN `INCOMPLETE` (compatible con MetalLB) en vez de `IGP` |
| `enableNoServiceEndpointsRoutable` | `--enable-no-service-endpoints-routable` | `true` | Determina si se sigue anunciando una VIP con política Cluster cuando no tiene backends (sección 2.5) |

Los valores `bgpControlPlane.*` son idénticos en 1.18.14, 1.19.8, 1.20.2 y 1.21.0-pre.3 (comparación con `values.yaml` de cada etiqueta). **[Versión preliminar 1.21]** los indicadores BGP se trasladaron al módulo `pkg/bgp/config`, por lo que ahora también aparecen en el conjunto de indicadores del operador (incluidos los de Router ID); el uso de Helm no cambia.

Escuchar en TCP/179 es opcional. De forma predeterminada, `bgpInstance` no tiene `localPort`, por lo que el agente solo funciona en modo **activo** e inicia conexiones a los peers. Si configuras `localPort: 179`, el agente necesita `CAP_NET_BIND_SERVICE` en la lista `securityContext.capabilities.ciliumAgent` del chart; con un puerto alto no se necesita esa capacidad.

### 2.3 Las cinco CRD

Todas tienen ámbito de clúster y usan `cilium.io/v2`. Las copias `cilium.io/v2alpha1` de los mismos tipos están **obsoletas** (aún se sirven en 1.20.2 y 1.21.0-pre.3 con `+kubebuilder:deprecatedversion`); escribe todos los manifiestos nuevos con `cilium.io/v2`.

| Tipo | Nombre abreviado | Lo escribe | Propósito |
|---|---|---|---|
| `CiliumBGPClusterConfig` | `cbgpcluster` | usuario | Define qué nodos ejecutan qué instancias y peers BGP |
| `CiliumBGPPeerConfig` | `cbgppeer` | usuario | Parámetros de sesión y anuncios que se envían a un peer |
| `CiliumBGPAdvertisement` | `cbgpadvert` | usuario | Qué anunciar y con qué atributos |
| `CiliumBGPNodeConfig` | `cbgpnode` | operador (solo lectura para usuarios) | Configuración resuelta por nodo y estado de las sesiones |
| `CiliumBGPNodeConfigOverride` | `cbgpnodeoverride` | usuario | Router ID, ASN, puertos y dirección de origen por nodo |

Los recursos se vinculan de dos maneras distintas, lo que suele causar errores:

```
CiliumBGPClusterConfig.spec.bgpInstances[].peers[].peerConfigRef.name  --by NAME-->  CiliumBGPPeerConfig
CiliumBGPPeerConfig.spec.families[].advertisements (label selector)    --by LABELS-> CiliumBGPAdvertisement.metadata.labels
```

La configuración de peer selecciona anuncios al comparar las **etiquetas del objeto `CiliumBGPAdvertisement`**, no sus campos `spec`. Varios objetos de anuncio pueden coincidir con un peer. Si no coincide ninguno, la sesión se establece, pero no se anuncia ninguna ruta.

#### CiliumBGPClusterConfig

| Campo | Tipo / límites | Notas |
|---|---|---|
| `spec.nodeSelector` | LabelSelector | Si es nulo o está vacío, selecciona **todos** los nodos. Cada nodo puede coincidir con una sola `CiliumBGPClusterConfig` |
| `spec.bgpInstances[]` | De 1 a 16 entradas; clave `name` | Una instancia de GoBGP por entrada |
| `.name` | De 1 a 255 caracteres, único | Se referencia desde las anulaciones y aparece en métricas como `instance_name` |
| `.localASN` | De 1 a 4294967295 | Opcional aquí; una anulación puede definirlo por nodo |
| `.localPort` | De 1 a 65535 | Si no se define, la instancia no escucha |
| `.peers[]` | clave `name` | |
| `.peers[].peerAddress` | IPv4 o IPv6 | Solo es opcional cuando se configura `autoDiscovery` |
| `.peers[].peerASN` | De 0 a 4294967295; predeterminado 0 | 0 omite la validación del ASN en el mensaje OPEN del peer |
| `.peers[].autoDiscovery` | `mode: DefaultGateway`, `defaultGateway.addressFamily: ipv4\|ipv6` | El peer es la puerta de enlace predeterminada del nodo (consulta abajo) |
| `.peers[].peerConfigRef.name` | cadena | En `cilium.io/v2` solo existe `name`; `group` / `kind` solo están en la CRD obsoleta v2alpha1 |

Condiciones de estado de la configuración del clúster: `cilium.io/NoMatchingNode`, `cilium.io/MissingPeerConfigs` y `cilium.io/ConflictingClusterConfig` (si dos configuraciones seleccionan el mismo nodo, el operador rechaza la que se procesa después).

**Detección automática (`DefaultGateway`).** El agente establece una sesión con la puerta de enlace predeterminada del nodo en lugar de usar un `peerAddress` fijo. El ToR debe aceptar peers dinámicos (`bgp listen range` en FRR) y usar el mismo ASN local en todos los ToR. No se admite una puerta de enlace predeterminada de enlace local. Si hay varias rutas predeterminadas (multihoming), Cilium establece **una** sesión por familia de direcciones, a través de la ruta con la métrica más baja, y cambia a la otra si falla; no puede mantener dos sesiones de esta manera para la misma familia. Para usar dos sesiones, define entradas estáticas `peerAddress`.

#### CiliumBGPPeerConfig

| Campo | Valor predeterminado / límites | Notas |
|---|---|---|
| `spec.transport.peerPort` | 179 (de 1 a 65535) | Puerto remoto |
| `spec.transport.sourceInterface` | ninguno | IP de origen tomada de esta interfaz. Debe tener como máximo una dirección apta por familia (no loopback, multicast ni IPv6 de enlace local). Si falta la interfaz, Cilium detecta automáticamente la interfaz de salida. No aparece en la documentación de 1.18; sí desde 1.19 |
| `spec.timers.connectRetryTimeSeconds` | 120 (mínimo 1) | Con fluctuación: el intervalo efectivo de reintento es [N, 2N) |
| `spec.timers.holdTimeSeconds` | 90 (de 3 a 65535) | Cambiar el hold o keepalive reinicia la sesión |
| `spec.timers.keepAliveTimeSeconds` | 30 (de 1 a 65535) | Regla de la CRD: keepalive <= holdTime |
| `spec.authSecretRef` | ninguno | Nombre de un Secret en el namespace de Secrets BGP; clave `password` (TCP MD5 según RFC 2385) |
| `spec.gracefulRestart.enabled` | obligatorio si se incluye el bloque | |
| `spec.gracefulRestart.restartTimeSeconds` | 120 (de 1 a 4095) | |
| `spec.ebgpMultihop` | 1 (de 1 a 255) | TTL predeterminado 1; no se aplica a iBGP |
| `spec.families[]` | selector afi + safi + `advertisements` | Solo se admiten `ipv4/unicast` y `ipv6/unicast`. Si se omite `families`, se negocian ambas familias unicast, **sin** anuncios |

Condición de estado: `cilium.io/MissingAuthSecret`.

> **Corrección de la documentación upstream.** La página upstream de configuración indica que los valores mínimos «posibles» son `holdTimeSeconds=9` y `keepAliveTimeSeconds=3`. Los mínimos de la CRD son hold >= 3 y keepalive >= 1 (y keepalive <= hold). 9/3 es un ajuste agresivo recomendado, no un mínimo.

#### CiliumBGPAdvertisement

Entradas de `spec.advertisements[]`:

| Campo | Notas |
|---|---|
| `advertisementType` | `PodCIDR`, `CiliumPodIPPool`, `Service`, `Interface` |
| `service.addresses[]` | Debe incluir al menos uno entre `LoadBalancerIP`, `ClusterIP` y `ExternalIP`. Obligatorio para el tipo `Service` |
| `service.aggregationLengthIPv4` / `IPv6` | De 0 a 31 / de 0 a 127; agrega rutas en vez de usar /32 y /128 |
| `interface.name` | Obligatorio para el tipo `Interface` |
| `selector` | LabelSelector para Services (o pools). Si no se define, no selecciona nada en tipos distintos de PodCIDR. No debe definirse para `PodCIDR` |
| `attributes.communities` | `standard[]`, `wellKnown[]`, `large[]` |
| `attributes.localPreference` | Solo se envía a peers iBGP |

La validación CEL exige: `service` para `Service`, `interface` para `Interface` y ningún `selector` para `PodCIDR`.

#### CiliumBGPNodeConfig (salida del operador)

`spec` refleja la configuración resuelta (incluye `routerID` y `localAddress`). `status.bgpInstances[].peers[]` contiene `name`, `peerAddress`, `peerASN`, `peeringState`, `establishedTime`, `timers.appliedHoldTimeSeconds` / `appliedKeepaliveSeconds` y `routeCount[]` (afi, safi, recibidas y anunciadas). La condición `cilium.io/BGPReconcileError` informa de fallos de reconciliación. Es la fuente adecuada para automatización y alertas porque no requiere ejecutar comandos dentro del agente.

#### CiliumBGPNodeConfigOverride

`metadata.name` **debe ser igual al nombre del nodo**; los nombres de instancias y peers deben coincidir con los de la configuración del clúster.

| Campo | Notas |
|---|---|
| `spec.bgpInstances[].name` | Coincide con el nombre de instancia en la configuración del clúster |
| `.routerID` | Cadena con una dirección IPv4 |
| `.localPort` | Anulación del puerto de escucha |
| `.localASN` | De 1 a 4294967295; permite ASN por nodo o por rack |
| `.peers[].name` | Coincide con el peer de la configuración del clúster |
| `.peers[].localAddress` | Fuerza la dirección de origen y, por tanto, el enlace de salida; de forma predeterminada se consulta la ruta hacia el peer |
| `.peers[].localPort` | Puerto de origen para la conexión |

### 2.4 Ajustes de peer en la práctica

**Temporizadores.** Los valores predeterminados son 120/90/30 (reintento de conexión/hold/keepalive). Sin BFD, el tiempo hold es el único detector de fallos para peers que no están conectados directamente; por eso son habituales valores agresivos como 9/3 en enlaces a ToR. La contrapartida es más tráfico keepalive y mayor sensibilidad a pausas de CPU del agente.

**Graceful Restart.** Con `gracefulRestart.enabled: true`, Cilium actúa como speaker en reinicio (RFC 4724, además de reinicio elegante RFC 8538 con Notification). Cuando se reinicia el agente, el peer conserva las rutas aprendidas hasta que vence `restartTimeSeconds`, por lo que el plano de datos (que sigue funcionando en eBPF) no queda en agujero negro durante una actualización del agente. Define `restartTimeSeconds` por encima del peor tiempo de reinicio del agente, incluida la descarga de la imagen; descarga previamente las imágenes antes de actualizar. Coste: si un nodo deja de funcionar realmente, GR conserva sus rutas hasta que venza ese tiempo, así que durante ese periodo el tráfico de VIP con `externalTrafficPolicy: Cluster` aún puede dirigirse a un nodo caído.

**Multisalto.** `ebgpMultihop: N` define el TTL de las sesiones eBGP con peers a más de un salto (por ejemplo, un ToR con peer por loopback o un servidor de rutas). No afecta a iBGP.

**MD5.**

```bash
kubectl -n kube-system create secret generic bgp-auth \
  --from-literal=password='<value from your secret store>'
```

Haz referencia a él con `authSecretRef: bgp-auth`. Una contraseña incorrecta aparece como `dial: i/o timeout`, no como error de autenticación, porque el kernel descarta los segmentos con firmas incorrectas. Si falta el Secret, la sesión no se detiene: Cilium continúa con una contraseña **vacía**, registra un error y establece `cilium.io/MissingAuthSecret`. MD5 no funciona si la sesión atraviesa NAT.

**Sin BFD.** Ninguna versión de Cilium de 1.18 a 1.21-pre admite BFD. Mitigaciones: temporizadores hold bajos, un enlace conectado directamente (TCP se cierra al caer el enlace), Graceful Restart para reinicios del agente y hashing resiliente/Maglev (más adelante).

### 2.5 Anuncios

#### PodCIDR

Anuncia el PodCIDR asignado al nodo (no el pool entero). Solo tiene efecto con modos IPAM que asignan un PodCIDR a cada nodo: `cluster-pool` y ámbito de host de Kubernetes. **Con ENI, Azure y otros IPAM de nube, el anuncio `PodCIDR` no tiene efecto**: las IP de Pod son direcciones de VPC (o VNet), no prefijos por nodo administrados por Cilium, y la infraestructura de nube ya las enruta. Consulta el [análisis detallado de IPAM](10-ipam-deep-dive.md).

#### CiliumPodIPPool

Se usa con IPAM de varios pools. `selector` coincide con las etiquetas del pool; las claves especiales `io.cilium.podippool.namespace` e `io.cilium.podippool.name` seleccionan por identidad del pool. Solo se anuncian los CIDR asignados realmente a un `CiliumNode`. En 1.20.2, el código BGP observa `v2alpha1.CiliumPodIPPool`; **[Versión preliminar 1.21]** `CiliumPodIPPool` pasa a `cilium.io/v2` y BGP se actualiza también (`pkg/bgp/manager/reconciler/pod_ip_pool.go` en v1.21.0-pre.3).

#### Service

De forma predeterminada, las rutas son exactamente /32 o /128.

| Origen | Se obtiene de | Política de tráfico respetada |
|---|---|---|
| `LoadBalancerIP` | `.status.loadBalancer.ingress[].ip` | Solo `externalTrafficPolicy` |
| `ExternalIP` | `.spec.externalIPs` (con KPR requiere `externalIPs.enabled`) | Solo `externalTrafficPolicy` |
| `ClusterIP` | `.spec.clusterIP(s)` (el acceso externo requiere el ajuste BPF «External access to ClusterIP services») | Solo `internalTrafficPolicy` |

Claves especiales de selector: `io.kubernetes.service.namespace` e `io.kubernetes.service.name`.

**Interacción con la política de tráfico.**

| Política | Desde dónde se anuncia |
|---|---|
| `Cluster` | Desde todos los nodos seleccionados por la configuración del clúster |
| `Local` | Solo desde nodos con al menos un backend local listo; la ruta sigue a los Pods |

Si hay **cero backends**: con `externalTrafficPolicy: Cluster`, la VIP sigue anunciándose desde todos los nodos si `--enable-no-service-endpoints-routable=true` (predeterminado); de lo contrario, se retira. Con `Local`, se retira.

**`loadBalancerClass`.** Cilium anuncia un Service solo si la clase no está definida o es `io.cilium/bgp-control-plane`. Ignora los Services administrados por otra clase (por ejemplo, `service.k8s.aws/nlb`).

**Anuncios superpuestos (1.18 y posteriores).** Si varios anuncios coinciden con un Service, las comunidades se combinan como **unión** y se usa el valor **máximo** de `localPreference`. Antes de 1.18 ganaba la última coincidencia.

**Agregación.** Se ignora `aggregationLengthIPv4/6` con la política de tráfico `Local`. Problemas conocidos: bucle de enrutamiento para VIP sin asignar dentro de un rango agregado y comportamiento indefinido si dos anuncios generan el mismo agregado con atributos distintos ([cilium/cilium#37623](https://github.com/cilium/cilium/pull/37623), [#40585](https://github.com/cilium/cilium/issues/40585)).

**ECMP.** Anuncia la misma VIP desde varios nodos; se aplica el límite de rutas ECMP del enrutador. Si se pierde un nodo, se redistribuyen los flujos, salvo que el enrutador use hashing resiliente. Maglev de Cilium mantiene constante la selección del backend entre nodos con política `Cluster`.

#### Interface (1.19 y posteriores)

Anuncia las direcciones de una interfaz local como rutas /32 y /128. Se excluyen: rango loopback, multicast, IPv6 de enlace local y direcciones v4-mapped. La interfaz debe estar habilitada administrativamente y su estado operativo debe ser `up` o `unknown`. Cilium no configura la dirección; un uso habitual es una interfaz dummy con una dirección estable de nodo o anycast.

#### Atributos

| Atributo | Valores |
|---|---|
| `communities.standard` | `"65000:99"` o un número decimal de 4 bytes |
| `communities.wellKnown` | `internet`, `planned-shut`, `accept-own`, `route-filter-translated-v4`, `route-filter-v4`, `route-filter-translated-v6`, `route-filter-v6`, `llgr-stale`, `no-llgr`, `blackhole`, `no-export`, `no-advertise`, `no-export-subconfed`, `no-peer` |
| `communities.large` | `"A:B:C"` |
| `localPreference` | Solo iBGP; el atributo se omite para peers eBGP |

Cilium crea políticas de exportación de GoBGP por combinación de (peer, familia y tipo de anuncio), por ejemplo `65000-ipv4-PodCIDR`, además de una política de importación `allow-local`. Son internas. **v2 no ofrece CRD de políticas de rutas, listas de prefijos, AS-prepend, MED ni next-hop**; usa comunidades como punto de integración e implementa la política en el ToR (route-maps que seleccionen por comunidad).

### 2.6 Ejemplo completo: eBGP por rack con dos ToR

Las direcciones y los ASN son ejemplos.

```yaml
apiVersion: cilium.io/v2
kind: CiliumBGPClusterConfig
metadata: {name: rack0}
spec:
  nodeSelector: {matchLabels: {rack: rack0}}
  bgpInstances:
  - name: instance-65001
    localASN: 65001
    peers:
    - {name: tor1, peerASN: 65000, peerAddress: 10.10.0.1, peerConfigRef: {name: tor-peer}}
    - {name: tor2, peerASN: 65000, peerAddress: 10.10.0.2, peerConfigRef: {name: tor-peer}}
---
apiVersion: cilium.io/v2
kind: CiliumBGPPeerConfig
metadata: {name: tor-peer}
spec:
  timers: {connectRetryTimeSeconds: 5, holdTimeSeconds: 9, keepAliveTimeSeconds: 3}
  gracefulRestart: {enabled: true, restartTimeSeconds: 120}
  authSecretRef: bgp-auth
  families:
  - afi: ipv4
    safi: unicast
    advertisements: {matchLabels: {advertise: bgp}}
---
apiVersion: cilium.io/v2
kind: CiliumBGPAdvertisement
metadata: {name: svc-and-pods, labels: {advertise: bgp}}
spec:
  advertisements:
  - advertisementType: PodCIDR
    attributes: {communities: {standard: ["65001:100"]}}
  - advertisementType: Service
    service: {addresses: [LoadBalancerIP]}
    selector: {matchLabels: {bgp: "true"}}
    attributes: {communities: {large: ["65001:1:100"]}}
```

Anulación por nodo (el nombre del nodo se coloca en `metadata.name`):

```yaml
apiVersion: cilium.io/v2
kind: CiliumBGPNodeConfigOverride
metadata: {name: <node-name>}
spec:
  bgpInstances:
  - name: instance-65001
    routerID: "192.168.10.1"
    localPort: 1790
    localASN: 65010
    peers:
    - {name: tor1, localAddress: 10.10.0.11}
```

### 2.7 Router ID

| Modo | Cómo se elige el ID |
|---|---|
| `default` | Dirección IPv4 del nodo (IPv4 y doble pila); en nodos solo IPv6, los 32 bits inferiores de la MAC de `cilium_host` |
| `ip-pool` | Se asigna desde `bgpControlPlane.routerIDAllocation.ipPool` (un CIDR IPv4) |
| Manual (`NodeConfigOverride.routerID`) | No se valida en modo `default`; en modo `ip-pool` no debe entrar en conflicto si está dentro del pool |

### 2.8 Inspección

**Primero, consulta el estado** (no es necesario ejecutar comandos dentro del Pod):

```bash
kubectl get ciliumbgpclusterconfigs,ciliumbgppeerconfigs,ciliumbgpadvertisements,ciliumbgpnodeconfigs
kubectl get ciliumbgpnodeconfigs <node> \
  -o jsonpath='{.status.bgpInstances[*].peers[*].peeringState}'
kubectl describe ciliumbgpclusterconfig rack0
```

**CLI.** `cilium bgp peers [-o json|summary] [--node N]` y `cilium bgp routes <available|advertised|received> <afi> <safi>` funcionan en 1.20.2. Llaman a la API REST del agente, obsoleta desde 1.20 (consulta abajo); en las fuentes incluidas de 1.21.0-pre.3, la CLI todavía ejecuta `cilium bgp peers -o json` dentro del Pod del agente.

**Hive shell (preferido desde 1.20).** Las notas de actualización 1.20 de upstream indican que se desaconsejan los comandos `cilium-dbg bgp` y las consultas de peers, rutas y políticas de rutas por la API REST local; se prefieren los comandos BGP de Hive shell. El binario del agente es `cilium-dbg`:

```bash
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/peers
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/routes out ipv4 unicast
kubectl -n kube-system exec ds/cilium -- cilium-dbg shell -- bgp/route-policies
```

| Comando | Significado |
|---|---|
| `bgp/peers [-f table\|table-json\|json\|detailed] [-o file] [--no-uptime]` | Tabla de sesiones |
| `bgp/routes <loc\|in\|out> <afi> <safi> [-a\|--with-attrs] [--no-age] [-f ...]` | `loc` = Loc-RIB, `in` = Adj-RIB-In, `out` = Adj-RIB-Out |
| `bgp/route-policies [-i instance]` | Políticas de exportación/importación generadas por Cilium |

Los mismos tres comandos están en 1.20.2 y 1.21.0-pre.3 (`pkg/bgp/commands/cell.go`). La CLI `cilium` no tiene un subcomando `shell`; usa `cilium-dbg` dentro del Pod del agente.

**Registros.** Agente: `subsys=bgp-control-plane`; operador: `subsys=bgp-cp-operator`.

**Métricas** (agente, prefijo `cilium_bgp_control_plane_`): `session_state` (1 = establecida), `advertised_routes`, `received_routes` (etiquetas `instance_name`, `local_asn`, `neighbor`, `neighbor_asn`, `afi`, `safi`), `reconcile_errors_total{instance_name}` y `reconcile_run_duration_seconds{instance_name}`. Operador: `cilium_operator_bgp_control_plane_reconcile_errors_total{resource_kind,resource_name}` y `..._reconcile_run_duration_seconds`.

> **Cambio de etiqueta de métrica.** La página de métricas de 1.19.8 usa la etiqueta `vrouter`; la de 1.20.2 usa `instance_name`. Las notas de actualización de 1.20 no mencionan el cambio de nombre, por lo que los paneles y las alertas que usan `vrouter` dejan de coincidir silenciosamente tras actualizar de 1.19 a 1.20. Actualízalos como parte de la actualización.

### 2.9 Eliminación de v1 y cronología de las versiones de CRD

| Versión | Estado |
|---|---|
| 1.18 | `CiliumBGPPeeringPolicy` (v1) queda obsoleta; si v1 y v2 coinciden con un nodo, tiene prioridad PeeringPolicy. Las CRD BGP v2alpha1 quedan obsoletas en favor de `cilium.io/v2` |
| 1.19 | Se **eliminan** la CRD v1 y el plano de control (`pkg/bgpv1`); migra antes de actualizar |
| 1.20 | Las copias v2alpha1 de las CRD BGP v2 siguen disponibles, pero están obsoletas |
| 1.21-pre | Igual |

Se eliminó el campo `spec.transport.localPort` de la PeerConfig v2alpha1, disponible antes de 1.19; la configuración del puerto ahora se define en la instancia de configuración del clúster (`localPort`) y en la anulación.

### 2.10 Operaciones y escenarios de fallo

| Evento | Comportamiento | Mitigación |
|---|---|---|
| Reinicio o actualización del agente | Se interrumpe la sesión (el speaker se ejecuta en el agente); el plano de datos sigue reenviando tráfico | Graceful Restart, `restartTimeSeconds` mayor que el arranque del agente; descarga previamente la imagen nueva |
| Caída del nodo | El peer espera el tiempo hold (más el tiempo de reinicio con GR) | Temporizadores hold bajos; ECMP con hashing resiliente |
| Caída del enlace, conexión directa | TCP se cierra de inmediato | n/a |
| Caída del enlace, varios saltos | Temporizador hold (90 s de forma predeterminada) | Reduce el tiempo hold; no hay BFD |
| Caída del operador | No se crea ningún `CiliumBGPNodeConfig`; el operador tampoco asigna PodCIDR ni IP de LB | Alta disponibilidad del operador |
| Un Service pierde todos sus backends | Consulta la sección 2.5 | Elige la política deliberadamente |

**Procedimiento de apagado de nodos.** Drena el nodo; quítalo de la configuración del clúster cambiando su etiqueta para que deje de coincidir con `nodeSelector` (la sesión se cierra con una notificación); espera a que el peer retire la ruta (de inmediato o cuando venza el temporizador de rutas obsoletas de RFC 8538); prevé algunos reinicios por nuevo hashing ECMP.

**[Versión preliminar 1.21]** El controlador BGP espera a que se adjunten los programas BPF del plano de datos del host y se rellenen los mapas LB antes de anunciar rutas (`pkg/bgp/agent/datapath_waiter.go`). Así se cierra el intervalo que existía tras arrancar el agente en que se anunciaban rutas antes de poder atender tráfico. No está en 1.20.

### 2.11 Topología de referencia: ToR local

```
            [ upstream L3 / firewall ]
                 |            |
             ToR-A (AS65000) ToR-B (AS65000)    static neighbors or `bgp listen range`
              |  \  /  |     ECMP, resilient hashing, GR helper
      node1..N (Cilium AS65001, one CiliumBGPClusterConfig per rack)
        advertise: PodCIDR (cluster-pool / host-scope IPAM)
                 + Service LoadBalancerIP (from an LB IPAM pool)
        eTP: Cluster (all nodes; add Maglev) or Local (only nodes with backends)
```

Lista de diseño: una configuración de clúster por rack (cada nodo puede coincidir con una sola); dos peers por rack; hold 9 / keepalive 3 con GR y un tiempo de reinicio superior al arranque del agente; MD5 mediante `authSecretRef`; comunidades que distingan rutas de Pod y de Service para los route-maps del ToR; verifica la cantidad máxima de rutas ECMP del ToR; no hay BFD.

### 2.12 BGP y AWS

En un clúster EKS que usa IPAM ENI, las IP de Pod son direcciones de VPC y la infraestructura de VPC ya las enruta; los nodos no poseen PodCIDR, así que anunciar PodCIDR no tiene efecto y la VPC no tiene un speaker BGP que acepte rutas de nodos. Por tanto, BGP se usa en AWS sobre todo con EKS Hybrid Nodes locales (consulta [configuración de red para nodos híbridos](../../eks-hybrid-nodes/02-network-configuration.md)), donde el peer es el ToR local. Los ejemplos existentes de nodos híbridos de este repositorio usan API `v2alpha1` porque están fijados a una compilación 1.18; en 1.19 y posteriores, usa `cilium.io/v2`.

## 3. LB IPAM

**Madurez**: CRD estable `CiliumLoadBalancerIPPool` de `cilium.io/v2` (v2 es la versión de almacenamiento en 1.18.14, aunque v2alpha1 aún se sirve; v2alpha1 se marca obsoleta por primera vez en 1.19.8). LB IPAM está integrado en el operador y permanece inactivo hasta que se crea el primer pool (`--enable-lb-ipam`, predeterminado `true`). Solo asigna direcciones; no las anuncia.

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata: {name: blue-pool}
spec:
  blocks:
  - cidr: "10.0.10.0/24"
  - start: "10.0.20.100"
    stop: "10.0.20.200"
  serviceSelector:
    matchLabels: {bgp: "true"}
---
apiVersion: v1
kind: Service
metadata: {name: web, namespace: example, labels: {bgp: "true"}}
spec:
  type: LoadBalancer
  loadBalancerClass: io.cilium/bgp-control-plane
  ports: [{port: 80}]
  selector: {app: web}
```

Ten en cuenta que `serviceSelector` está bajo `spec`, no bajo `blocks` (el ejemplo de la documentación upstream tiene una sangría incorrecta).

| Campo del pool | Notas |
|---|---|
| `blocks[]` | `cidr` o la pareja `start` + `stop` |
| `serviceSelector` | Claves especiales `io.kubernetes.service.namespace` / `.name` |
| `disabled` | Predeterminado `false` |
| `allowFirstLastIPs` | `Yes` o `No`; `No` reserva solo la primera y la última dirección de bloques CIDR; se ignora para /31, /32, /127, /128 y bloques `start`/`stop` |

Comportamientos importantes:

- CIDR superpuestos: el pool posterior queda marcado como conflictivo (`cilium.io/PoolConflict`). Las condiciones de estado son `cilium.io/IPsTotal`, `IPsAvailable` e `IPsUsed`; `kubectl get ippools` las muestra.
- Editar un pool puede reasignar IP de Services existentes.
- Gestión de clases: LB IPAM administra de forma predeterminada un Service `LoadBalancer` sin clase. `defaultLBServiceIPAM` de Helm acepta `lbipam` (valor predeterminado), `nodeipam` o `none`; con `none`, solo recibe una IP el Service con clase reconocida. Las clases que Cilium no reconoce se ignoran sin aviso. El Service recibe la condición `cilium.io/IPAMRequestSatisfied`.
- Las familias de IP siguen `ipFamilyPolicy`: SingleStack (IPv4 si ambas están disponibles), PreferDualStack y RequireDualStack.
- Solicita una dirección específica con `lbipam.cilium.io/ips: "a,b"` (se sigue aplicando el selector del pool; `.spec.loadBalancerIP` está obsoleto). No solicites la primera ni la última dirección de un pool.
- **Uso compartido**: `lbipam.cilium.io/sharing-key` y `lbipam.cilium.io/sharing-cross-namespace: "ns1,ns2"|"*"`. En 1.20.2, los Services pueden compartir si no hay conflictos de puerto/protocolo. **[Versión preliminar 1.21]** compatibilidad más estricta: no deben coincidir el puerto y protocolo, debe coincidir `externalTrafficPolicy` y, con `Local`, ambos deben seleccionar los mismos Pods, salvo que cada Service defina `lbipam.cilium.io/sharing-permit-different-pods: "true"` (BGP y L2 no conocen la capa 4, así que se podría descartar tráfico); deben estar en el mismo namespace, salvo que se permita compartir entre namespaces.
- **Cambio del plano de datos en 1.19**: se descarta el tráfico TCP/UDP norte-sur hacia una IP LB IPAM en un puerto que ningún Service define.
- Gateway API: `Gateway.spec.addresses` alimenta LB IPAM; la anotación `io.cilium/lb-ipam-ips` en `spec.infrastructure.annotations` tiene prioridad y se prevé declararla obsoleta más adelante.

La asignación de IP de Pod es independiente: consulta el [análisis detallado de IPAM](10-ipam-deep-dive.md).

## 4. Anuncios L2

**Madurez**: beta en 1.20.2 y 1.21.0-pre.3. La CRD sigue siendo `CiliumL2AnnouncementPolicy` de `cilium.io/v2alpha1`.

Un nodo elegido por Service responde a ARP (IPv4) o NDP (IPv6) por las IP externas o LoadBalancer del Service y luego balancea el tráfico con eBPF. Está dirigido a redes LAN locales sin BGP. **No se aplica dentro de una VPC de AWS**: la VPC no da a las VIP semántica de difusión L2 ni conmutación por error mediante ARP gratuito. Úsalo solo en entornos locales o híbridos.

```yaml
l2announcements:
  enabled: true
  leaseDuration: 3s
  leaseRenewDeadline: 1s
  leaseRetryPeriod: 200ms
kubeProxyReplacement: true
k8sClientRateLimit: {qps: 32, burst: 64}
```

```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumL2AnnouncementPolicy
metadata: {name: policy1}
spec:
  serviceSelector: {matchLabels: {color: blue}}
  nodeSelector:
    matchExpressions:
    - {key: node-role.kubernetes.io/control-plane, operator: DoesNotExist}
  interfaces: ["^eth[0-9]+"]
  externalIPs: true
  loadBalancerIPs: true
```

| Campo | Notas |
|---|---|
| `nodeSelector`, `serviceSelector` | Qué nodos pueden anunciar y qué Services |
| `interfaces[]` | Expresiones regulares de Go (OR). No son un control de seguridad. Los dispositivos también deben estar en el conjunto `--devices` de Cilium |
| `externalIPs`, `loadBalancerIPs` | Booleanos; ambos predeterminados en `false` |

El Service no debe tener `loadBalancerClass` o debe tener `io.cilium/l2-announcer`.

**Elección de líder.** Se usa un Lease `coordination.k8s.io` por Service, llamado `cilium-l2announce-<ns>-<svc>` en el namespace de Cilium; el orden de llegada determina la asignación, por lo que la carga se reparte de manera desigual. El nuevo líder envía un ARP gratuito. Valores predeterminados: `leaseDuration` 15 s, `leaseRenewDeadline` 5 s y `leaseRetryPeriod` 2 s. Restricciones: duration > renewDeadline; renewDeadline debe ser estrictamente mayor que 1.2 (JitterFactor de elección de líder) x retryPeriod; de lo contrario, el agente registra una advertencia y cambia los temporizadores. La conmutación por error tarda entre `leaseDuration - leaseRenewDeadline` y `leaseDuration + leaseRenewDeadline`: de 10 a 20 s con los valores predeterminados, o de 2 a 4 s con 3 s/1 s/200 ms.

**Carga de la API.** El Lease de cada Service se renueva aproximadamente cada `leaseRenewDeadline`, así que calcula `QPS ~ cantidad_de_services x (1 / leaseRenewDeadline)` (estimación aproximada que no cuenta reintentos ni lecturas). El límite predeterminado del cliente del agente es 10 QPS / ráfaga 20 y se comparte con todo el tráfico de API del agente: con el valor predeterminado de 5 s, son unos 0,2 QPS por Service, así que unas decenas de Services con líder ya consumen buena parte del presupuesto; con temporizadores de 1 s, unos 10 Services lo agotan. Aumenta `k8sClientRateLimit` antes de reducir los temporizadores. RBAC necesita permisos create/get/update/list/delete para Lease.

**Límites.** No es compatible con `externalTrafficPolicy: Local` (el nodo elegido podría no tener Pods y descartaría el tráfico). Un nodo recibe todo el tráfico de una IP; no existe balanceo de carga previo al clúster.

Los **anuncios L2 de IP de Pod** son independientes: `l2podAnnouncements.enabled` y `.interfacePattern` (expresión regular) envían GARP/NA para las IP locales de Pod. El indicador antiguo `--l2-pod-announcements-interface` se eliminó en 1.19.

Inspección: `kubectl -n kube-system get lease | grep cilium-l2announce`; `cilium-dbg shell -- db/show l2-announce`; `cilium-dbg shell -- db/show devices`; ejecuta `arping` desde otro host de la LAN.

## 5. Node IPAM

Helm `nodeIPAM.enabled=true` (predeterminado `false`; operador `--enable-node-ipam`; reinicia el operador) publica las direcciones de los nodos en `.status.loadBalancer` para Services con `loadBalancerClass: io.cilium/node` (o `defaultLBServiceIPAM: nodeipam`): `ExternalIP` si existe; de lo contrario, `InternalIP`, respetando `ipFamilies`. La política `Cluster` publica todos los nodos; `Local` solo los que tienen Pods en EndpointSlice. Se omiten los nodos con la etiqueta `node.kubernetes.io/exclude-from-external-load-balancers` o el taint `ToBeDeletedByClusterAutoscaler`; la anotación `io.cilium.nodeipam/match-node-labels` limita los nodos. No funciona con política `Local` en Services de Cilium Ingress/Gateway (usan un EndpointSlice sintético). Úsalo solo cuando BGP y L2 no sean posibles y solo con direcciones privadas de nodo: publicar IP públicas de nodo crearía un punto de entrada público fuera de la regla que exige CloudFront.

## 6. Qué función administra cada Service

| `loadBalancerClass` | Responsable | Requisitos |
|---|---|---|
| sin definir | LB IPAM de forma predeterminada (`defaultLBServiceIPAM`) | Un pool; además, BGP o L2 para que sea accesible |
| `io.cilium/bgp-control-plane` | LB IPAM + anuncio BGP | BGP Control Plane |
| `io.cilium/l2-announcer` | LB IPAM + anuncio L2 | Anuncios L2 |
| `io.cilium/node` | Node IPAM | `nodeIPAM.enabled` |
| `service.k8s.aws/nlb` | AWS Load Balancer Controller | Cilium BGP/LB IPAM lo ignora |

## 7. Egress Gateway

**Madurez**: `CiliumEgressGatewayPolicy` usa `cilium.io/v2` (ámbito de clúster, nombre abreviado `cegp`); la documentación 1.20 no la marca como beta.

El tráfico de los Pods seleccionados hacia los CIDR de destino seleccionados se reenvía a un nodo de gateway y se aplica SNAT a una IP de origen estable, de modo que el firewall externo vea una dirección predecible.

Requisitos: `egressGateway.enabled=true`, `bpf.masquerade=true` y `kubeProxyReplacement=true`; reinicia los agentes **y** el operador. No es compatible con el modo de identidad `kvstore` (usa `crd`), ClusterMesh (el gateway debe estar en el mismo clúster) ni CiliumEndpointSlice. `--enable-ipv4-egress-gateway` se eliminó en 1.19.

```yaml
apiVersion: cilium.io/v2
kind: CiliumEgressGatewayPolicy
metadata: {name: egress-sample}
spec:
  selectors:
  - podSelector:
      matchLabels: {org: empire, class: mediabot, io.kubernetes.pod.namespace: default}
  destinationCIDRs: ["192.0.2.0/24"]
  egressGateway:
    nodeSelector: {matchLabels: {egress-node: "true"}}
    egressIP: 10.168.60.100
```

| Campo | Notas |
|---|---|
| `selectors[]` | `podSelector` y/o `namespaceSelector` (namespace mediante la etiqueta `io.kubernetes.pod.namespace`); no se permite usar solo `nodeSelector` |
| `destinationCIDRs[]`, `excludedCIDRs[]` | IPv4 e IPv6; los CIDR excluidos deben ser subconjuntos. Las direcciones internas (Pods, nodos y servidor de API) siempre se excluyen de EGW |
| `egressGateway.nodeSelector` | Obligatorio. Si hay varias coincidencias, se elige la primera en orden alfabético del nombre de nodo. **Si no coincide ningún nodo, se descarta el tráfico a los CIDR de destino** |
| `egressGateway.interface` / `egressIP` | Son mutuamente excluyentes (si se configuran ambas, se ignora la política). `interface` usa su primera dirección IPv4/IPv6; `egressIP` debe existir en un dispositivo administrado por Cilium; si no se define ninguna, se usa la interfaz de la ruta predeterminada y sus primeras direcciones IPv4/IPv6 |
| `egressGateways[]` | Hasta 64 entradas; si no está vacío, se ignora `egressGateway` |

Limitaciones:

- **No hay alta disponibilidad en 1.20.2 ni 1.21.0-pre.3.** `egressGateways[]` configura varios gateways estáticos: se fija cada endpoint de origen a uno mediante un hash de su UID de CiliumEndpoint. Al cambiar el conjunto, se reasignan endpoints y se interrumpen las conexiones existentes (cilium/cilium#39245). El código fuente de ninguna versión contiene comprobaciones de estado ni conmutación automática por fallo de un gateway (búsqueda en `pkg/egressgateway`). La CRD de 1.21-pre solo difiere de la de 1.20.2 en los tipos de CIDR.
- El gateway no sigue los cambios de IP posteriores a la selección; vuelve a aplicar la política.
- Si no existe la IP configurada, se descarta el tráfico con el motivo «No Egress IP configured».
- Un Pod nuevo puede enviar tráfico brevemente con su propia IP o con la IP del nodo antes de que se programe la política.
- El presupuesto de puertos SNAT por cada combinación de (IP de salida, IP:puerto remoto) es de aproximadamente 65535 menos el límite superior del rango de puertos de nodo (32767 de forma predeterminada), es decir, 32768 conexiones. Consulta `cilium-dbg shell -- db/show nat-stats`.

Inspección: `kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf egress list` (muestra IP de origen, CIDR de destino, IP de salida e IP de gateway).

**En EKS.** El nodo de gateway necesita la dirección de salida en una ENI conectada (otra ENI o una IP privada secundaria). Las IP de salida son direcciones privadas de VPC; para acceder a Internet desde ellas, enruta el tráfico mediante una gateway NAT. No asignes IP públicas ni EIP a los nodos de gateway. Con IPAM ENI, `--egress-multi-home-ip-rule-compat` se eliminó en 1.19; deja de usarlo primero en 1.18.

## 8. Local Redirect Policy

`CiliumLocalRedirectPolicy` (`cilium.io/v2`, con ámbito de namespace) redirige el tráfico destinado a una ClusterIP de Service o a una IP:puerto arbitraria hacia Pods backend locales al nodo.

Habilítala con `localRedirectPolicies.enabled=true` (la clave antigua `localRedirectPolicy` está obsoleta); reinicia el operador y el agente. De forma opcional, se puede configurar una lista de permitidos para todo el clúster con `localRedirectPolicies.addressMatcherCIDRs` (el YAML de la documentación upstream muestra una clave escrita de otra manera; la clave de Helm es `addressMatcherCIDRs`).

```yaml
apiVersion: cilium.io/v2
kind: CiliumLocalRedirectPolicy
metadata: {name: lrp-svc}
spec:
  redirectFrontend:
    serviceMatcher: {serviceName: my-service, namespace: default}
  redirectBackend:
    localEndpointSelector: {matchLabels: {app: proxy}}
    toPorts: [{port: "80", protocol: TCP}]
```

| Selector | Uso |
|---|---|
| `serviceMatcher` | Solo Services ClusterIP; reemplaza la entrada del Service por tipo `LocalRedirect` y usa únicamente backends locales al nodo |
| `addressMatcher{ip, toPorts[]}` | IP que no pertenece a un Service; se niega a anular un frontend ClusterIP existente |

Reglas: los Pods backend deben estar en el namespace de la política; si se usan varios puertos, deben tener nombre; solo se redirigen las conexiones **nuevas** (reinicia los clientes); las políticas no se pueden actualizar (elimínalas y vuelve a crearlas). Configuraciones compatibles de reemplazo de kube-proxy: KPR completo; KPR con `socketLB.hostNamespaceOnly=true`; KPR desactivado con `socketLB.enabled=true`; o KPR desactivado sin más (solo Pod a ClusterIP). El caso de uso principal es DNS local al nodo (el frontend kube-dns se redirige a un Pod node-local-dns en su propio namespace de red). Inspecciona con `cilium-dbg lrp list`.

## 9. Distribución del tráfico de Services

`loadBalancer.serviceTopology` (predeterminado `false`, indicador `--enable-service-topology`) hace que el reemplazo de kube-proxy respete los hints de enrutamiento consciente de la topología **y** `spec.trafficDistribution`. `PreferSameZone` (y el alias obsoleto `PreferClose`) usa los hints de zona de EndpointSlice comparados con la etiqueta de zona `topology.kubernetes.io/zone` del nodo; `PreferSameNode` prefiere backends del nodo local y, si no hay ninguno que cumpla, recurre al comportamiento predeterminado. **[Versión preliminar 1.21]** solo cuentan como candidatos los backends activos (listos). Esto difiere de `externalTrafficPolicy` / `internalTrafficPolicy: Local`, que restringen los destinos en vez de priorizarlos. En EKS de varias zonas de disponibilidad, `serviceTopology: true` más `trafficDistribution: PreferSameZone` reduce el tráfico entre zonas. En Gateway API, `CiliumGatewayClassConfig.spec.service.trafficDistribution` se propaga al Service generado.

## 10. Puntos de entrada de capa 7: Ingress y Gateway API

Requisitos previos: `kubeProxyReplacement=true`, `l7Proxy=true` (valor predeterminado), compatibilidad con TPROXY (iptables de forma predeterminada; `bpf.tproxy=true` es beta y elimina la dependencia de iptables) y compatibilidad con Services LoadBalancer (o modo de red del host, desde 1.16).

**Flujo del tráfico.** eBPF intercepta los paquetes dirigidos al puerto del Service y los redirige mediante TPROXY al Envoy de cada nodo. El tráfico recibe la identidad especial `ingress`, por lo que la política se aplica dos veces: de world a ingress y de ingress al backend. Se conserva la IP de origen con ambos valores de `externalTrafficPolicy`; con `Local`, Cilium hace que todos los nodos superen las comprobaciones de estado en el puerto de health check. La `CiliumNetworkPolicy` debe permitir ambos saltos. Con TLS passthrough, los backends ven la IP de Envoy.

### Ingress

| Valor de Helm | Predeterminado |
|---|---|
| `ingressController.enabled` / `.default` | `false` / `false` |
| `ingressController.loadbalancerMode` | `dedicated` (`shared` o `dedicated`; anotación por Ingress `ingress.cilium.io/loadbalancer-mode`) |
| `ingressController.enforceHttps` | `true` |
| `ingressController.useRemoteAddress`, `.xffNumTrustedHops` | `true`, `0` |
| `ingressController.ingressLBAnnotationPrefixes` | `lbipam.cilium.io`, `nodeipam.cilium.io`, `service.beta.kubernetes.io`, `service.kubernetes.io`, `cloud.google.com` (se propagan de Ingress al Service) |
| `ingressController.service.*` (compartido) | `name: cilium-ingress`, `type: LoadBalancer`, `externalTrafficPolicy: Cluster`, anotaciones, `loadBalancerClass` |
| `ingressController.hostNetwork.*` | `enabled: false`, `sharedListenerPort: 8080` |

### Gateway API

Cilium 1.20.2 y 1.21.0-pre.3 usan **Gateway API v1.6.1** (1.19.8: v1.4.1; 1.18.14: v1.3.0). Tipos admitidos: GatewayClass, Gateway, HTTPRoute, GRPCRoute, TLSRoute, BackendTLSPolicy, ReferenceGrant, ListenerSet, TCPRoute y UDPRoute. CRD necesarias: GatewayClass, Gateway, HTTPRoute, GRPCRoute, ReferenceGrant, BackendTLSPolicy y TLSRoute. TCPRoute, UDPRoute y ListenerSet son opcionales (la función se deshabilita si faltan). Instálalas con `kubectl apply --server-side`.

> **Riesgo durante la actualización: Gateway API v1.6.1 y TLSRoute.** En v1.6.1, TLSRoute pasó de `v1alpha2` a `v1`. Las notas de actualización de 1.20 exigen v1.6.1 como versión mínima. Si ya tienes objetos TLSRoute, instala la CRD TLSRoute del canal **experimental** de v1.6.1 (todavía incluye la versión `v1alpha2`). La CRD TLSRoute del canal **standard** de v1.6 hace que los objetos `v1alpha2` existentes no se puedan leer y parezcan desaparecer de etcd. Haz una copia de seguridad de TLSRoute y actualiza las CRD de Gateway API **antes** de actualizar Cilium a 1.20.

| Valor de Helm | Predeterminado |
|---|---|
| `gatewayAPI.enabled` | `false` |
| `gatewayAPI.gatewayClass.create` | `auto` |
| `gatewayAPI.enableProxyProtocol`, `.enableAppProtocol`, `.enableAlpn` | `false` |
| `gatewayAPI.useRemoteAddress`, `.xffNumTrustedHops` | `true`, `0` |
| `gatewayAPI.externalTrafficPolicy` | `Cluster` (se ignora con la red del host) |
| `gatewayAPI.secretsNamespace` | `create: true`, `name: cilium-secrets`, `sync: true` |
| `gatewayAPI.hostNetwork.enabled` / `.nodes.matchLabels` | `false` / `{}` |

El Service generado se llama `cilium-gateway-<gateway>` y es de tipo `LoadBalancer` de forma predeterminada. Personalízalo con `CiliumGatewayClassConfig` (`cilium.io/v2alpha1`, con ámbito de namespace, referencia desde `GatewayClass.parametersRef`; alfa): `spec.service{type, externalTrafficPolicy, loadBalancerClass, ipFamilies, ipFamilyPolicy, allocateLoadBalancerNodePorts, loadBalancerSourceRanges, loadBalancerSourceRangesPolicy, trafficDistribution}`, `envoy.serverHeaderTransformation` y `httpOptions.grpcWebTranslation.enabled`. Para cada Gateway, `spec.infrastructure.annotations` y `labels` se copian al Service generado; así se pasan anotaciones `service.beta.kubernetes.io/aws-load-balancer-*`. No se admite `spec.infrastructure.parametersRef`.

Modo de red del host (`gatewayAPI.hostNetwork.enabled=true`): Envoy escucha en las interfaces del nodo; usa puertos superiores a 1023 o concede `NET_BIND_SERVICE`; es mutuamente excluyente con el modo Service LoadBalancer e incompatible con TCPRoute/UDPRoute; el Service pasa a ser NodePort; aparecen como máximo 16 direcciones en el estado de Gateway.

### Patrón de EKS: origen VPC de CloudFront a NLB interno y Cilium

CloudFront es el único punto de entrada público. Ningún componente de esta topología está expuesto a Internet.

```
Internet --> CloudFront --(VPC origin)--> INTERNAL NLB (private subnets)
         --> node NodePort --> Cilium Envoy (Ingress or Gateway) --> Pods
```

```yaml
kubeProxyReplacement: true
ingressController:
  enabled: true
  loadbalancerMode: shared
  service:
    type: LoadBalancer
    loadBalancerClass: service.k8s.aws/nlb
    allocateLoadBalancerNodePorts: true
    externalTrafficPolicy: Cluster
    annotations:
      service.beta.kubernetes.io/aws-load-balancer-scheme: internal
      service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: instance
      service.beta.kubernetes.io/aws-load-balancer-security-groups: sg-<nlb-sg>
      service.beta.kubernetes.io/aws-load-balancer-manage-backend-security-group-rules: "true"
```

Para la variante de Gateway API, define `CiliumGatewayClassConfig.spec.service.loadBalancerClass: service.k8s.aws/nlb` y coloca las mismas anotaciones `aws-load-balancer-*` en `Gateway.spec.infrastructure.annotations`.

Reglas de este patrón:

- `scheme: internal` es obligatorio. Nunca uses `internet-facing`.
- Usa `target-type: instance`. El Service Ingress compartido de Cilium usa un EndpointSlice sintético, así que los destinos `ip` no se resuelven a Pods; consulta [Ingress y Gateway API](../../service-mesh/cilium-service-mesh/05-ingress-gateway.md).
- El grupo de seguridad del balanceador solo admite CloudFront: el grupo de seguridad administrado por el servicio `CloudFront-VPCOrigins-Service-SG` (se crea al crear el origen VPC; más restrictivo y preferido; no asignes tú mismo ese prefijo a un grupo) o la lista de prefijos administrada por CloudFront `com.amazonaws.global.cloudfront.origin-facing` (y `com.amazonaws.global.ipv6.cloudfront.origin-facing` para doble pila). No permitas entrada desde `0.0.0.0/0` o `::/0`, ni asignes IP públicas o EIP a los nodos ([AWS: orígenes VPC](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html)).
- Los grupos de seguridad de nodo solo admiten el grupo de seguridad del NLB en el rango NodePort, no un CIDR abierto a Internet.

## 11. SRv6 y enrutamiento estático

SRv6 **no está disponible** como función compatible. Las fuentes de 1.20.2 y 1.21.0-pre.3 no tienen página de documentación, clave Helm ni CRD para ello; solo quedan ocultos el indicador del agente `--enable-srv6`, los hooks BPF y los comandos de inspección `cilium-dbg bpf srv6`, sin plano de control de código abierto. No planifiques usarlo. Para rutas estáticas, usa enrutamiento nativo con `autoDirectNodeRoutes` o tablas de rutas de nube ([parte 9](09-overlay-native-routing.md)).

## Laboratorios

> Los laboratorios 1 a 4 requieren un entorno local (kind o unas pocas máquinas virtuales) con un contenedor de enrutador, como FRR; el laboratorio 5 usa una cuenta de AWS de pruebas desechable mediante `--profile <SANDBOX_PROFILE>`. Los resultados esperados se describen con palabras; no se incluyen salidas capturadas.

### Laboratorio 1: sesión BGP con un ToR FRR

**Requisitos previos**: clúster kind con 2 nodos de trabajo en una red Docker compartida con un contenedor FRR (AS 65000, peers configurados para las IP de los nodos, AS remoto 65001); Cilium con `bgpControlPlane.enabled=true`; manifiestos de la sección 2.6 adaptados a las IP de tus nodos (quita `authSecretRef` o crea primero el Secret).

1. Etiqueta los nodos de trabajo con `rack=rack0`; aplica ClusterConfig, PeerConfig y Advertisement.
2. `kubectl get ciliumbgpnodeconfigs` muestra uno por cada nodo etiquetado.
3. `kubectl get ciliumbgpnodeconfigs <node> -o jsonpath='{.status.bgpInstances[*].peers[*].peeringState}'` y `cilium-dbg shell -- bgp/peers` deben informar `established`; `show bgp summary` de FRR debe mostrar activos los peers.
4. `cilium-dbg shell -- bgp/routes out ipv4 unicast` muestra el PodCIDR del nodo; `show ip route bgp` de FRR confirma que se aprendió.
5. Elimina el Pod del agente de un nodo. Con GR habilitado, FRR debe conservar las rutas (marcadas como obsoletas) hasta el vencimiento del tiempo de reinicio; sin GR, desaparecen enseguida. Compara ambos casos.

**Reversión/limpieza**: elimina los tres recursos BGP y quita las etiquetas de los nodos. Al eliminar ClusterConfig, el operador quita los NodeConfig y cierra las sesiones.

### Laboratorio 2: LB IPAM con BGP e interacción con la política de tráfico

**Requisitos previos**: laboratorio 1 en ejecución.

1. Crea el pool y el Service de la sección 3 (usa un bloque dentro de un rango que acepte tu contenedor FRR).
2. `kubectl get svc web -n example` muestra una EXTERNAL-IP del pool; `kubectl get ippools` muestra `IPsUsed` igual a 1.
3. `bgp/routes out ipv4 unicast` muestra el /32 desde cada nodo seleccionado. Desde el contenedor FRR, ejecuta `curl <VIP>`.
4. Ejecuta `kubectl patch svc web -n example -p '{"spec":{"externalTrafficPolicy":"Local"}}'`. La ruta solo debe permanecer en los nodos con un Pod listo; escala el Deployment y observa cómo cambia.

**Limpieza**: elimina el Service, el Deployment y el pool.

### Laboratorio 3: anuncios L2

**Requisitos previos**: clúster kind sobre un puente Linux, KPR habilitado, `l2announcements.enabled=true` con temporizadores 3 s/1 s/200 ms y límite de tasa del cliente aumentado; un contenedor cliente en el mismo puente.

1. Aplica la política L2 y un Service `LoadBalancer` de un pool.
2. `kubectl -n kube-system get lease | grep cilium-l2announce` muestra un Lease para el Service; `arping` desde el cliente devuelve la MAC del nodo líder.
3. Elimina el Pod del agente de Cilium en el nodo líder (o detén el contenedor de ese nodo) y mide cuánto falla `arping`: con estos temporizadores, espera unos segundos; con los valores predeterminados, de 10 a 20 segundos.

**Limpieza**: elimina la política y el Service. Reversión: restablece los valores predeterminados del Lease.

### Laboratorio 4: Egress Gateway

**Requisitos previos**: KPR y `bpf.masquerade=true`, `egressGateway.enabled=true`, agentes y operador reiniciados; un servidor web externo en un contenedor que registre las IP de los clientes; un nodo etiquetado `egress-node=true` con una dirección secundaria en su dispositivo.

1. Aplica una política similar a la de la sección 7 con esa dirección y el CIDR del servidor.
2. Desde un Pod seleccionado, ejecuta `curl` al servidor; el registro debe mostrar la IP de salida en vez de la IP del nodo o del Pod.
3. `cilium-dbg bpf egress list` en el nodo de origen muestra la entrada. Quita la etiqueta del nodo: se debería descartar el tráfico al CIDR (no habrá gateway).

**Limpieza/reversión**: elimina la política y quita la etiqueta. Mientras esté aplicada, interrumpe el tráfico seleccionado.

### Laboratorio 5: NLB interno de EKS detrás de CloudFront (cuenta de pruebas)

**Requisitos previos**: `aws sts get-caller-identity --profile <SANDBOX_PROFILE>` muestra la cuenta de pruebas esperada `<ACCOUNT_ID>` y el rol asumido previsto; un clúster EKS con Cilium y AWS Load Balancer Controller; ya se creó un origen VPC de CloudFront.

1. Instala con los valores de Helm de la sección 10 (si lo prefieres, usa la variante Gateway API).
2. `aws elbv2 describe-load-balancers --profile <SANDBOX_PROFILE> --query 'LoadBalancers[].[LoadBalancerName,Scheme]'` debe mostrar `internal` para el NLB nuevo.
3. `aws ec2 describe-security-groups --profile <SANDBOX_PROFILE> --group-ids <nlb-sg> --query 'SecurityGroups[].IpPermissions'` debe mostrar como orígenes solo el grupo de seguridad o la lista de prefijos de origen VPC de CloudFront, nunca `0.0.0.0/0` ni `::/0`.
4. Configura el NLB como destino del origen VPC y envía una solicitud mediante el dominio de CloudFront.

**Limpieza**: elimina el Ingress o Gateway (el controlador elimina el NLB); luego verifica que el NLB se haya eliminado con una respuesta real de recurso no encontrado, no solo con estado `deleting`.

## Diferencias entre versiones

| Área | 1.18 | 1.19 | 1.20 | 1.21-pre |
|---|---|---|---|---|
| BGP v1 `CiliumBGPPeeringPolicy` | obsoleta | **eliminada** | eliminada | eliminada |
| CRD de BGP | v2 (y v2alpha1) | almacenamiento `cilium.io/v2`; v2alpha1 obsoleta | igual | igual |
| Anuncio BGP `Interface`, `transport.sourceInterface` | no aparecen en la documentación | disponibles | disponibles | disponibles |
| GoBGP | n/a en esta revisión | gobgp v3 (1.19.8) | gobgp v4 | gobgp v4 |
| Etiqueta de métrica BGP | n/a | `vrouter` (documentación) | `instance_name` | `instance_name` |
| Listado por `cilium-dbg bgp` / REST | compatible | compatible | **obsoleto**; usa Hive shell `bgp/*` | marcado obsoleto |
| Espera a que el plano de datos esté listo antes de anunciar BGP | no | no | no | **sí** |
| `CiliumLoadBalancerIPPool` | v2 (almacenamiento), v2alpha1 aún disponible | `cilium.io/v2` (v2alpha1 obsoleta) | v2 | v2; reglas de uso compartido más estrictas |
| CRD de Gateway API | v1.3.0 | v1.4.1 | **v1.6.1** (riesgo con TLSRoute) | v1.6.1 |
| API `CiliumPodIPPool` | v2alpha1 | v2alpha1 | v2alpha1 | **v2** |
| Egress Gateway | CRD v2 | se eliminan `--enable-ipv4-egress-gateway` y `--egress-multi-home-ip-rule-compat` | sin alta disponibilidad | sin alta disponibilidad |
| Anuncios L2 | beta | beta | beta (CRD v2alpha1) | beta |
| SRv6 | ausente | ausente | ausente | ausente (solo queda un indicador oculto) |

## Solución de problemas

| Síntoma | Causa probable | Comprobación |
|---|---|---|
| No se crea `CiliumBGPNodeConfig` | el operador no se ejecuta o `nodeSelector` no coincide con ningún nodo | Condición de ClusterConfig `NoMatchingNode`; registros del operador `subsys=bgp-cp-operator` |
| Se rechaza la configuración del clúster | otra configuración del clúster selecciona el mismo nodo | `ConflictingClusterConfig` |
| La sesión queda atascada; `dial: i/o timeout` | contraseña MD5 incorrecta, ACL o dirección de origen incorrecta | `authSecretRef`, `cilium.io/MissingAuthSecret`, `localAddress` / `sourceInterface` |
| La sesión está activa, pero no hay rutas | las etiquetas de `families[].advertisements` en PeerConfig no coinciden con las etiquetas del anuncio | Compara las etiquetas; consulta `bgp/route-policies` |
| PodCIDR no anunciado en EKS | IPAM ENI no asigna PodCIDR por nodo | [IPAM](10-ipam-deep-dive.md) |
| VIP de Service no anunciada | `loadBalancerClass` no es `io.cilium/bgp-control-plane` ni está vacío, no coincide el selector o la política `Local` no tiene un backend listo | YAML del Service; `bgp/routes out` |
| Las rutas desaparecen al actualizar el agente | no se habilitó Graceful Restart o el tiempo de reinicio es demasiado breve | GR de PeerConfig; descarga previamente la imagen |
| Los paneles BGP de Grafana quedan vacíos tras 1.20 | la etiqueta `vrouter` cambió a `instance_name` | Actualiza las consultas |
| La IP LB permanece en `<pending>` | no hay pool, no coincide el selector, el pool está en conflicto o la clase es desconocida | `kubectl get ippools`; condición del Service |
| La VIP L2 fluctúa o falla | política `Local` o limitación de solicitudes de API del Lease | Objetos Lease; aumenta `k8sClientRateLimit` |
| Se descarta el tráfico de salida | ningún nodo coincide con `nodeSelector` del gateway o falta la IP en el dispositivo | `bpf egress list`; motivo del descarte |
| TLSRoute desaparece tras actualizar la CRD de Gateway API | se instaló la CRD v1.6 del canal estándar sobre datos v1alpha2 | Restaura desde la copia de seguridad; usa la CRD del canal experimental |
| El Service de Gateway queda atascado | faltan CRD requeridas de Gateway API o KPR está desactivado | Registros del operador; `cilium status` |

## Límites de validación y fuentes

En esta revisión no se ejecutaron los laboratorios en un clúster activo; se contrastaron con el código fuente y la documentación upstream. La sintaxis de `bgp/peers` y `bgp/routes` se verificó en `pkg/bgp/commands`; no se capturó la salida real de las tablas y, por tanto, no se muestra. Se omitieron temas no investigados sobre BGP con clústeres EKS nativos (no híbridos), como Transit Gateway Connect o el peering de VPC Route Server. Sin verificar: si Egress Gateway incorporará conmutación por error según estado en 1.21 GA, y la versión exacta de 1.19 a 1.20 que cambió la etiqueta de métrica (se confirmó en 1.20.2 y no aparece en la documentación de 1.19.8).

Fuentes (etiqueta v1.20.2, salvo que se indique otra):

- [Descripción general de BGP Control Plane](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane.rst), [configuración](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-configuration.rst), [operación](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/bgp-control-plane/bgp-control-plane-operation.rst)
- [Tipos de CRD de BGP](https://github.com/cilium/cilium/tree/v1.20.2/pkg/k8s/apis/cilium.io/v2), [comandos de Hive shell](https://github.com/cilium/cilium/blob/v1.20.2/pkg/bgp/commands/cell.go)
- [LB IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/lb-ipam.rst), [anuncios L2](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/l2-announcements.rst), [Node IPAM](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/node-ipam.rst)
- [Egress Gateway](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/egress-gateway/egress-gateway.rst), [Local Redirect Policy](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/local-redirect-policy.rst)
- [Notas de actualización 1.20](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc), [Gateway API](https://github.com/cilium/cilium/tree/v1.20.2/Documentation/network/servicemesh/gateway-api)
- [Espera del plano de datos BGP en v1.21.0-pre.3](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/pkg/bgp/agent/datapath_waiter.go), [LB IPAM en v1.21.0-pre.3](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/lb-ipam.rst)

## Cuestionario

Pon a prueba tus conocimientos con el [cuestionario de la parte 11](../../quizzes/networking/cilium/11-bgp-lb-egress-edge-quiz.md).
