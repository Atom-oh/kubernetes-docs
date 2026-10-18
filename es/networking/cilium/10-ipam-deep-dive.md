# Parte 10: Análisis detallado de IPAM

> **Base de revisión**: Cilium 1.20.2 (estable, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Los elementos marcados **[versión preliminar 1.21]** proceden de v1.21.0-pre.3 y pueden cambiar antes de la disponibilidad general.
> **Última actualización**: 15 de octubre de 2026

[La parte 4](04-ipam-policy.md) presentó los modos de IPAM y sus fragmentos de Helm. Este capítulo explica qué componente administra cada dirección, qué sucede entre `cilium-cni ADD` y la creación de un endpoint, cómo dimensionar un pool antes de instalar, cómo el asignador ENI decide cuándo llamar a EC2 y en qué se diferencian LB IPAM y Node IPAM de Pod IPAM. Complementa [Enrutamiento superpuesto y nativo](09-overlay-native-routing.md) (cómo se enrutan las direcciones) y [BGP, balanceo de carga, salida y perímetro](11-bgp-lb-egress-edge.md) (cómo se anuncian las direcciones de LB).

## Qué es IPAM y qué no es

En un clúster de Kubernetes, cuatro entidades distintas asignan cuatro familias de direcciones diferentes. Confundirlas es la causa más común de los errores de «IPAM».

| Dirección | Responsable | Participación de Cilium |
|---|---|---|
| Direcciones IP de Pod (endpoint) | Cilium IPAM (este capítulo y las subsecciones de modos) | Las asigna, lleva su seguimiento y las libera |
| ClusterIP de Service | kube-apiserver (`--service-cluster-ip-range`) | Ninguna; Cilium solo las programa en el plano de datos |
| IP de Service de tipo LoadBalancer | LB IPAM (`CiliumLoadBalancerIPPool`) o un controlador de nube | Solo asignación en el operador; el anuncio es independiente (plano de control BGP o anuncios L2) |
| Direcciones de nodos como balanceadores de carga | Node IPAM (`loadBalancerClass: io.cilium/node`) | El operador copia las direcciones de los nodos al estado del Service |

`CiliumPodIPPool` nunca asigna ClusterIP y `CiliumLoadBalancerIPPool` nunca asigna IP de Pod. `CiliumCIDRGroup` (consulta «CiliumCIDRGroup» más abajo) no asigna direcciones: es un conjunto con nombre de CIDR para políticas.

## Vista general: el intercambio con CiliumNode

En casi todos los modos, dos componentes se comunican mediante el recurso personalizado `CiliumNode` (uno por nodo, con el mismo nombre que el nodo):

```
                        +-----------------------------+
                        |        CiliumNode <node>    |
                        |  spec.ipam.podCIDRs         |  cluster-pool
                        |  spec.ipam.pools.requested  |  multi-pool / eni (agent writes)
                        |  spec.ipam.pools.allocated  |  multi-pool / eni (operator writes)
                        |  spec.ipam.pool             |  crd (external allocator writes)
                        |  status.ipam.*              |  used IPs, operator-status.error
                        |  status.eni.enis            |  eni (operator writes)
                        +--------------+--------------+
                 watch/update          |          watch/update
        +------------------------+     |     +--------------------------+
        |  cilium-agent (node)   |<----+---->|  cilium-operator         |
        |  local pod-IP allocator|           |  node CIDRs, EC2/Azure   |
        |  CNI /ipam REST        |           |  API calls, pool alloc   |
        +------------------------+           +--------------------------+
```

El agente asigna IP de Pod individuales a partir del espacio que posee el nodo en ese momento. El operador (o Kubernetes o un sistema externo, según el modo) decide qué direcciones posee el nodo. En los modos `cluster-pool`, `multi-pool` y `eni`, el agente crea su propio `CiliumNode` (opción del agente `auto-create-cilium-node-resource`, cuyo valor predeterminado es `true`). El operador ignora cualquier `CiliumNode` con la anotación `ipam.cilium.io/ignore: "true"`; esto permite excluir nodos administrados por otro sistema.

### Integración del asignador del agente por modo (1.20.2)

| `ipam.mode` | De dónde procede la capacidad del nodo | Asignador del agente |
|---|---|---|
| `kubernetes` | `Node.spec.podCIDRs` (o anotaciones) | Asignador de ámbito de host sobre el CIDR del nodo |
| `cluster-pool` (predeterminado) | Operador, mediante `CiliumNode.spec.ipam.podCIDRs` | Asignador de ámbito de host sobre el CIDR del nodo |
| `multi-pool` | Operador, mediante `spec.ipam.pools.allocated` | Administrador de varios pools |
| `eni` | Operador (API de EC2), mediante `status.eni.enis` convertido en `spec.ipam.pools.allocated` | **Asignador ENI de varios pools (nuevo en 1.20)** |
| `crd`, `azure`, `alibabacloud` | `CiliumNode.spec.ipam.pool` | Asignador basado en CRD |
| `delegated-plugin` | Otro complemento CNI de IPAM | Asignador sin operaciones |

Interacciones con Helm que conviene recordar: `eni.enabled=true` fuerza `ipam: eni`, independientemente de `ipam.mode`; `ipam.mode=eni` sin `eni.enabled` hace que falle la validación del chart. No existe el valor `gke`: GKE autoadministrado usa `kubernetes`.

### Direcciones locales del nodo

Cilium reserva direcciones del rango de cada nodo para su propio uso: la IP del enrutador `cilium_host`, la IP del endpoint de estado y, si está habilitado Ingress, la IP de Ingress. En `cilium-dbg status --all-addresses` aparecen como `(router)`, `(health)` y `(ingress)`. El asignador de ámbito de host también excluye la primera dirección (de red) y la última (de difusión) del CIDR del nodo. Hay que restarlas al calcular la capacidad (consulta «Cálculo de capacidad»).

## Ciclo de vida de las IP de Pod

Flujo desde kubelet hasta un endpoint activo para todos los modos, salvo `delegated-plugin`:

```
kubelet -> CRI -> cilium-cni ADD
                     |
                     | 1. remove stale host-side interface name, if any
                     | 2. POST /ipam   (unix socket to cilium-agent)
                     |       owner = <namespace>/<pod>, expiration = true
                     v
                 cilium-agent: IpamPostIpamHandler
                     | 3. empty pool?  -> pick pool (annotations/selectors, multi-pool)
                     | 4. AllocateNextWithExpiration
                     |       -> response: IPv4/IPv6, pool, cidrs, gateway,
                     |          master-mac, interface-number, skip-masquerade,
                     |          expiration-uuid, host-addressing (router IP)
                     |       -> start 10 minute expiration timer
                     v
                 cilium-cni: create veth (or netkit), set IPs/routes in the pod netns
                     | 5. PUT /endpoint/{id}
                     v
                 cilium-agent: build endpoint, identity, datapath
                     | 6. endpoint creation stops the expiration timer
                     v
                 pod Running

 failure at any point after step 4 -> deferred DELETE /ipam/{ip}?pool=<pool>
 CNI DEL -> endpoint delete -> agent releases the IP (metric ipam_events_total{action="release"})
```

Mecánicas clave, verificadas en el código fuente de 1.20.2:

- **Llamadas REST**: `POST /ipam`, `POST /ipam/{ip}` y `DELETE /ipam/{ip}` en la API del agente (`api/v1/openapi.yaml`). El complemento CNI llama a `IPAMAllocate("", podName, "", true)`; el último argumento es el indicador de expiración.
- **Temporizador de expiración**: una IP asignada con expiración se libera automáticamente después de `defaults.IPAMExpiration` (10 minutos), a menos que la creación del endpoint detenga el temporizador. Así se cierra el intervalo en que el complemento CNI podría fallar después de asignar la IP y antes de crear el endpoint, lo que de otro modo retendría la dirección hasta que se reiniciara el agente.
- **Restauración**: cuando se reinicia el agente, vuelve a reclamar las IP de los endpoints activos (se muestran como `[restored]` en `cilium-dbg status --all-addresses`). La opción `--bypass-ip-availability-upon-restore` solo existe para casos de actualización de ENI/Azure.
- **Modos de tipo ENI** (`eni`, `azure`, `alibabacloud`): la respuesta también incluye la MAC de ENI, la puerta de enlace y los CIDR. El complemento obtiene el índice de la interfaz principal a partir de la MAC (solo ENI), y el agente instala reglas de enrutamiento por endpoint en el host. Por eso estos modos fuerzan las rutas de endpoint.
- **`delegated-plugin`**: el propio complemento CNI ejecuta `DelegateAdd` con el binario de IPAM configurado (por ejemplo, `azure-ipam` de Azure en AKS) y marca el endpoint como `ExternalIpam`, por lo que el agente nunca libera esa IP; el complemento ejecuta `DelegateDel` durante `DEL`. En este modo Cilium no contabiliza las IP de Pod.

Inspección:

```bash
# All addresses the agent knows, with owners (ns/pod); multi-pool shows pool/ip
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg status --all-addresses

# Allocation summary line, for example "IPAM: IPv4: N/M allocated from <cidr>"
kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg status | grep -i ipam
```

Si un Pod queda atascado en `ContainerCreating` y CNI muestra el error `unable to allocate IP via local cilium agent`, significa que fallaron los pasos 2 a 4; la sección de solución de problemas relaciona el error con una causa para cada modo.

## Catálogo de modos y matriz de decisión

### Comparación de funcionalidades

Adaptado de la página de conceptos de IPAM del proyecto upstream para 1.20.2.

| Funcionalidad | Ámbito de host de Kubernetes | Ámbito de clúster (predeterminado) | Varios pools | Basado en CRD | AWS ENI | Azure IPAM | GKE (mediante ámbito de host) |
|---|---|---|---|---|---|---|---|
| Enrutamiento por túnel | sí | sí | sí | no | no | no | no |
| Enrutamiento directo | sí | sí | sí | sí | sí | sí | sí |
| Configuración de CIDR | Kubernetes | Cilium | Cilium | externo | AWS | Azure | GCP |
| Varios CIDR por clúster | no | sí | sí | n/a | n/a | n/a | n/a |
| Varios CIDR por nodo | no | no | sí | n/a | n/a | n/a | n/a |
| Asignación dinámica de CIDR/IP | no | no | sí | sí | sí | sí | no |

Madurez: `cluster-pool`, `kubernetes`, `crd` y `eni` son estables. `multi-pool` tenía la etiqueta «Beta» en 1.18, que desapareció desde 1.19 (este capítulo lo considera estable desde 1.19; upstream no lo denomina «GA»). IPv6 de ENI es **beta** en 1.20. La migración en línea de `cluster-pool` a `multi-pool` es nueva en 1.20.

### Matriz de decisión

Estas recomendaciones sintetizan la documentación upstream y las restricciones de cada plataforma; no se trata de una tabla de upstream.

| Entorno | IPAM recomendado | Motivos y aspectos que vigilar |
|---|---|---|
| EKS; se necesitan IP de Pod enrutable desde la VPC (destinos de grupos de seguridad, destinos IP de ALB/NLB, sin SNAT) | `eni`, más delegación de prefijos en Nitro | Requiere permisos IAM para el operador, enrutamiento nativo y retirar `aws-node`. La densidad está limitada por la cantidad de ENI/IP de la instancia, salvo que se use delegación de prefijos. IPv6 es beta. No se aplica a Fargate ni a nodos de EKS Auto Mode |
| EKS; escasean las IP de VPC o se necesita alta densidad | `cluster-pool` con VXLAN (valor predeterminado de Helm) o `multi-pool` | Los Pods hacen SNAT a la IP del nodo; el plano de control de EKS no puede llegar a las IP de Pod, por lo que los webhooks de admisión deben ejecutarse en la red del host o ser accesibles mediante un Service |
| EKS Hybrid Nodes (nodos locales) | `cluster-pool` con VXLAN; la lista de pools equivale a las «remote pod networks» de EKS; máscara dimensionada según los Pods por nodo | La configuración compatible con AWS usa solo IPv4, VXLAN, IPAM de ámbito de clúster y BGP Control Plane. No cambies la lista de pools ni la máscara después del despliegue. `eni` no se puede usar en nodos locales |
| Local, sencillo | `cluster-pool` con túnel | Lo administra el operador y no depende de los CIDR de nodo de kube-controller-manager |
| Local; Pods enrutables y varios rangos por sitio o inquilino | `multi-pool` + anuncios BGP de `CiliumPodIPPool`; pool predeterminado por sitio mediante `CiliumNodeConfig` | Requiere `kubeProxyReplacement=true` y `bpf.masquerade=true`; los CIDR de los pools no deben superponerse |
| Clúster cuyo plano de control ya asigna CIDR a los nodos (kubeadm con `--allocate-node-cidrs`, GKE) | `kubernetes` | Estático: un CIDR por familia y nodo |
| Direcciones suministradas por un sistema externo | `crd` | Solo direcciones IP individuales y enrutamiento directo |
| AKS | Azure CNI Powered by Cilium (`delegated-plugin`) o BYOCNI con cualquier IPAM de Cilium | No uses en AKS el IPAM `azure` de upstream |
| Máquinas virtuales de Azure autoadministradas | `azure` | Indicadores del grupo de recursos y de identidad; se rediseñó en la versión preliminar 1.21 |

### Cambio de modo en un clúster activo

La recomendación de upstream es no cambiar el modo IPAM de un clúster en funcionamiento salvo mediante una migración documentada; «la opción más segura es crear un clúster nuevo». La única ruta en línea documentada es **de `cluster-pool` a `multi-pool`** (consulta la subsección de migración). Para cualquier otro cambio (de `kubernetes` a `cluster-pool`, a ENI o de superposición a ENI) se necesita un clúster nuevo o un grupo de nodos blue/green, porque cambian los rangos de IP de Pod, el enrutamiento y, en EKS, la accesibilidad de los webhooks. Upstream no documenta mezclar modos IPAM por grupo de nodos con `CiliumNodeConfig`, y este capítulo no lo recomienda.

## Ámbito de host y ámbito de clúster de Kubernetes

### Ámbito de host de Kubernetes (`ipam.mode=kubernetes`)

Al iniciarse, el agente espera el PodCIDR del nodo para cada familia habilitada, obtenido de `Node.spec.podCIDRs` / `spec.podCIDR` o de las anotaciones `network.cilium.io/ipv4-pod-cidr` y `network.cilium.io/ipv6-pod-cidr` (además de `ipv4/6-cilium-host`, `ipv4/6-health-ip` e `ipv4/6-Ingress-ip`). `kube-controller-manager` debe ejecutarse con `--allocate-node-cidrs` (y `--cluster-cidr`, `--node-cidr-mask-size`).

```yaml
ipam:
  mode: kubernetes
k8s:
  requireIPv4PodCIDR: true     # only effective with ipam.mode=kubernetes
  requireIPv6PodCIDR: false
```

En este modo, el agente habilita automáticamente `k8s-require-ipv4-pod-cidr` cuando IPv4 está habilitado, así que el ajuste explícito sirve sobre todo como documentación. Límites: un CIDR por nodo y familia, fijado al registrar el nodo, sin crecimiento dinámico. GKE autoadministrado usa este modo con `ipv4NativeRoutingCIDR` definido como el CIDR del clúster.

### Ámbito de clúster / cluster-pool (predeterminado)

El operador administra la asignación de prefijos a los nodos. A cada nodo se le asigna un CIDR que se escribe en `CiliumNode.spec.ipam.podCIDRs`; al iniciarse, el agente espera hasta que ese campo tenga un valor para cada familia habilitada y luego usa el mismo asignador de ámbito de host sobre ese rango. Después de reiniciarse, el operador vuelve a adoptar las asignaciones existentes; un conflicto produce `node has CIDRs allocated (...) that conflict with requested CIDRs`.

Valores de Helm (valores predeterminados de 1.20.2):

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.0.0.0/8"]   # default
    clusterPoolIPv4MaskSize: 24                  # default
    clusterPoolIPv6PodCIDRList: ["fd00::/104"]   # default
    clusterPoolIPv6MaskSize: 120                 # Helm default (operator flag default is 112)
```

Las claves de ConfigMap generadas son `cluster-pool-ipv4-cidr` (lista separada por espacios), `cluster-pool-ipv4-mask-size`, `cluster-pool-ipv6-cidr` y `cluster-pool-ipv6-mask-size`. El operador no inicia si IPv4 está habilitado y la lista está vacía («cluster-pool-ipv4-cidr must be provided when using ClusterPool») o si se configura una lista para una familia deshabilitada.

### Cálculo de capacidad

El asignador de CIDR de nodo está en `pkg/ipam/cidrset`. Para cada CIDR de pool con longitud de prefijo `P` y máscara de nodo `M`:

```
nodes per pool CIDR      = 2^(M - P)
addresses per node       = 2^(32 - M)          (IPv4)     2^(128 - M) (IPv6)
usable Pod IPs per node  = addresses - 2 (network, broadcast) - up to 3 (router, health, ingress)
```

Restricciones derivadas del código fuente: para IPv6, `M - P` no puede superar 16 (`clusterSubnetMaxDiff = 16`, error `ErrCIDRSetSubNetTooBig`), porque el asignador mantiene un mapa de bits sin comprimir; para IPv4 solo se exige `M <= 32`. Upstream recomienda una máscara de nodo mínima de `/30` y recomienda `/29` o un prefijo mayor.

| CIDR del pool | Máscara de nodo | Nodos | Direcciones por nodo | Nota |
|---|---|---|---|---|
| `10.0.0.0/8` (predeterminado) | `/24` | 65 536 | 256 | `2^(24-8)`; unas 251 utilizables |
| `10.244.0.0/16` | `/24` | 256 | 256 | clúster pequeño típico |
| `10.244.0.0/16` | `/26` | 1 024 | 64 | `2^(26-16)`; unas 59 utilizables |
| `10.244.0.0/16` | `/28` | 4 096 | 16 | dimensionamiento para laboratorio; unas 11 utilizables |
| `fd00::/104` (predeterminado) | `/120` | 65 536 | 256 | valor IPv6 predeterminado; la diferencia es exactamente 16 |
| `fd00:10:244::/96` | `/112` | 65 536 | 65 536 | diferencia máxima permitida: 16 |

Las primeras cuatro filas se calculan con la fórmula anterior; «utilizables» resta las dos direcciones reservadas y las tres direcciones que usa Cilium, así que es un límite superior. La densidad de Pods por nodo también depende de `maxPods` en kubelet: dimensiona la máscara para `maxPods` más margen para las actualizaciones graduales (los Pods antiguos y nuevos coinciden durante el proceso).

Reglas de modificación (de upstream; se hacen cumplir mediante el comportamiento, no mediante validación):

- No edites ni elimines entradas existentes de `clusterPoolIPv4PodCIDRList`. Para ampliar el espacio, añade otro CIDR.
- `clusterPoolIPv4MaskSize` no se puede cambiar en un clúster activo.
- Los errores del asignador (`allocator full`) aparecen en `CiliumNode.status.ipam.operator-status.error`.

```bash
kubectl get ciliumnodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.ipam.podCIDRs}{"\t"}{.status.ipam.operator-status}{"\n"}{end}'
```

Riesgo de superposición: el valor predeterminado `10.0.0.0/8` coincide con la mayoría de los rangos corporativos y de VPC. Si coincide con la red de los nodos, perderás conectividad con ellos. Define siempre la lista explícitamente.

**`nativeRoutingCIDRFromClusterPool`** (Helm, predeterminado `false`; nuevo en 1.20: no figura en `values.yaml` de 1.18.14 ni 1.19.8, pero sí en 1.20.2 y 1.21): deriva el CIDR de enrutamiento nativo a partir del pool. Solo es válido con `cluster-pool` y exactamente un CIDR por familia habilitada; de lo contrario, falla la plantilla.

### Doble pila

```yaml
ipam:
  mode: cluster-pool
  operator:
    clusterPoolIPv4PodCIDRList: ["10.244.0.0/16"]
    clusterPoolIPv4MaskSize: 24
    clusterPoolIPv6PodCIDRList: ["fd00:10:244::/96"]
    clusterPoolIPv6MaskSize: 112       # 112 - 96 = 16, the maximum allowed
ipv4: { enabled: true }
ipv6: { enabled: true }
```

Definir `ipv6.enabled` no crea un CIDR de Service IPv6 ni conectividad IPv6 de infraestructura. Según el modo: el ámbito de host necesita las dos entradas de `podCIDRs` y `k8s.requireIPv6PodCIDR`; los pools de varios pools pueden incluir `ipv4`, `ipv6` o ambos, y existen las anotaciones por familia `ipam.cilium.io/ipv4-pool` y `ipam.cilium.io/ipv6-pool`; IPv6 de ENI es beta (consulta «Versión, use-primary-address e IPv6»); LB IPAM sigue `ipFamilyPolicy` del Service (consulta «LB IPAM» más abajo). La configuración de EKS Hybrid Nodes compatible con AWS solo usa IPv4.

## IPAM de varios pools

### Concepto

`multi-pool` sustituye «una lista de CIDR para todo el clúster» por **pools** con nombre, cada uno definido como `CiliumPodIPPool`. Un nodo puede tener bloques de varios pools a la vez, solicitados por el agente cuando los necesita. Se usa para asignar rangos separados a distintos inquilinos, subconjuntos de Pods enrutables (con anuncios BGP por pool), rangos por sitio y pools que conservan la IP de origen.

### Requisitos previos e instalación

El tutorial de upstream requiere `kubeProxyReplacement=true` y `bpf.masquerade=true`. Limitación conocida: la suplantación de IP basada en iptables requiere `egressMasqueradeInterfaces` (problema 22273 de upstream), por lo que la opción compatible es la suplantación eBPF. Los CIDR de los pools no deben superponerse (la caché de IP asigna una identidad a cada prefijo).

```yaml
ipam:
  mode: multi-pool
  multiPoolPreAllocation: "default=8,mars=4"
  operator:
    autoCreateCiliumPodIPPools:
      default:
        ipv4: { cidrs: ["10.10.0.0/16"], maskSize: 27 }
      mars:
        ipv4: { cidrs: ["10.20.0.0/16"], maskSize: 27 }
kubeProxyReplacement: true
bpf: { masquerade: true }
```

`autoCreateCiliumPodIPPools` solo crea pools inexistentes; nunca los actualiza. Corresponde al indicador del operador `--auto-create-cilium-pod-ip-pools <pool>=ipv4-cidrs:...;ipv4-mask-size:...[;allow-first-ip:...][;allow-last-ip:...]`, cuya sintaxis no permite expresar `podSelector`, `namespaceSelector` ni (en 1.21) `pool[].reservedRanges`. Crea esos pools como recursos personalizados.

### CiliumPodIPPool

```yaml
apiVersion: cilium.io/v2alpha1      # 1.20.x; use cilium.io/v2 from 1.21 [1.21 pre-release]
kind: CiliumPodIPPool
metadata:
  name: mars
spec:
  # allowFirstIP / allowLastIP are fields of spec (not of spec.ipv4); default false,
  # ignored for /31 /32 /127 /128
  ipv4:
    cidrs: ["10.20.0.0/16"]
    maskSize: 27
  podSelector:
    matchLabels:
      io.kubernetes.pod.namespace: tenant-mars   # synthetic label
  namespaceSelector:
    matchLabels:
      tenant: mars
```

Tiene ámbito de clúster y nombre abreviado `cpip`. `maskSize`, `allowFirstIP` y `allowLastIP` son inmutables (CEL: `self == oldSelf`). Se reservan la primera y la última dirección de cada *bloque asignado por nodo*, salvo que se definan `allowFirstIP` / `allowLastIP`. Si un pool no tiene bloques para una familia, se omite para esa familia.

**Nota sobre la versión de la API.** 1.20.2 sirve `cilium.io/v2alpha1`. **[Versión preliminar 1.21]** `cilium.io/v2` pasa a ser la versión de almacenamiento y `v2alpha1` queda obsoleta; además, v2 limita `cidrs` a 32 elementos y añade `spec.ipv4.pool[]` / `spec.ipv6.pool[]` (consulta «Actualización segura de pools»). Actualiza los manifiestos y las herramientas a v2 al pasar a 1.21.

### Selección del pool

Se evalúa una sola vez, al crear el Pod (cambiar la anotación de un Pod activo no tiene efecto). Precedencia indicada por el código (`pkg/ipam/metadata/manager.go`) y la documentación:

1. **Anotación del Pod**: `ipam.cilium.io/ipv4-pool` / `ipam.cilium.io/ipv6-pool` (por familia) tienen prioridad sobre `ipam.cilium.io/ip-pool`.
2. **Anotación del namespace**: las mismas claves en el namespace del Pod.
3. **Selectores de `CiliumPodIPPool`**: `podSelector` y `namespaceSelector` (si se definen ambos, ambos deben coincidir). Debe coincidir exactamente un pool por familia; de lo contrario, la asignación **falla** y genera un error y un evento.
4. **Pool predeterminado**: `ipam-default-ip-pool` (valor predeterminado `default`), a menos que el Pod o el namespace tenga `ipam.cilium.io/require-pool-match: "true"`; en ese caso, se bloquea la asignación.

La clave de anotación correcta es `ipam.cilium.io/ip-pool` (`pkg/annotation/k8s.go`). En algunos tutoriales upstream aparece `ipam.cilium.io/ipam-pool`, pero esa clave no tiene efecto.

```bash
kubectl annotate namespace tenant-mars ipam.cilium.io/ip-pool=mars
```

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pinned
  annotations:
    ipam.cilium.io/ip-pool: mars
spec:
  containers:
  - name: app
    image: registry.k8s.io/pause:3.10
```

### Cómo solicita capacidad el agente

El agente escribe la demanda en `CiliumNode.spec.ipam.pools.requested[] {pool, needed{ipv4-addrs, ipv6-addrs}}`. El operador asigna bloques por nodo del tamaño `maskSize` del pool hasta que las direcciones disponibles en el nodo cubren `needed`, y los añade a `spec.ipam.pools.allocated[] {pool, cidrs[], allowFirstIP, allowLastIP}`. El agente quita los bloques que están completamente libres y superan la demanda. Los errores se registran en `status.ipam.operator-status.error`.

La fórmula documentada es `neededIPs = roundUp(inUse + pending + preAlloc, preAlloc)`. El código (`neededIPCeil` en `pkg/ipam/multipool_manager.go`) redondea al siguiente múltiplo más uno, así que con `preAlloc = P`, una demanda de 0 solicita `P`, de 1 a `P` solicita `2P`, y `P+1` solicita `3P`. Esto deja un margen de al menos una unidad de preasignación. El indicador del agente es `--ipam-multi-pool-pre-allocation` (Helm `ipam.multiPoolPreAllocation`); si está vacío, `default=8` y los demás pools tienen un valor predeterminado de 0. El recuento se aplica por cada familia habilitada.

Como los bloques se asignan en incrementos de `maskSize`, elige un tamaño para que cada bloque tenga varias veces el valor de `preAlloc` (por ejemplo, `/27` = 32 direcciones con `preAlloc=8`); de lo contrario, los nodos adquirirán y liberarán repetidamente muchos bloques pequeños.

### Pool predeterminado por nodo, suplantación y enrutamiento

**Pool predeterminado por nodo** mediante `CiliumNodeConfig` (`cilium.io/v2`, namespace `kube-system`). Los cambios solo se aplican cuando se reinicia el Pod del agente.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNodeConfig
metadata:
  name: ip-pool-dc1
  namespace: kube-system
spec:
  defaults:
    ipam-default-ip-pool: dc1-pool
  nodeSelector:
    matchLabels:
      topology.kubernetes.io/zone: dc1
```

No uses esta anulación para el pool con nombre que se emplea en una migración de `cluster-pool` (consulta la subsección de migración de `cluster-pool` a `multi-pool`).

**Suplantación de IP (masquerade).** La opción del agente `--only-masquerade-default-pool` (requiere suplantación eBPF) o la anotación por pool `ipam.cilium.io/skip-masquerade="true"` en `CiliumPodIPPool` conservan la IP de origen del Pod en los pools distintos del predeterminado; el cambio solo afecta a Pods nuevos. No hay una clave de Helm específica para esa opción del agente: usa `extraConfig.only-masquerade-default-pool: "true"` (esta ruta exacta no se probó en esta revisión).

**Enrutamiento.** Los CIDR de los pools se pueden anunciar mediante BGP Control Plane (`advertisementType: CiliumPodIPPool`; consulta la [parte 11](11-bgp-lb-egress-edge.md)) o alcanzar con `autoDirectNodeRoutes` en un segmento L2 compartido.

### Actualización segura de pools y `reservedRanges` [versión preliminar 1.21]

Reglas: se pueden añadir pools y CIDR adicionales en un clúster activo; no se debe quitar un CIDR que use un nodo ni eliminar un pool en uso (el operador registra `CIDR from pool still in use by node`). En 1.20, para sustituir un CIDR, edita el pool y reinicia el operador; luego, grupo por grupo, marca los nodos como no programables, evacúa sus cargas, elimina los objetos `CiliumNode`, reinicia los agentes y vuelve a habilitar la programación.

**[Versión preliminar 1.21]** `cilium.io/v2` permite configurar `reservedRanges` por CIDR, para poder retirar un CIDR sin dejar asignaciones huérfanas:

```yaml
apiVersion: cilium.io/v2
kind: CiliumPodIPPool
metadata:
  name: default
spec:
  ipv4:
    cidrs: ["10.10.0.0/16", "10.20.0.0/16"]
    maskSize: 24
    pool:
    - cidr: 10.10.0.0/16
      reservedRanges:
      - start: 10.10.0.0
        end: 10.10.255.255
```

Los bloques existentes de los nodos en `10.10.0.0/16` siguen funcionando; los bloques nuevos solo se asignan desde `10.20.0.0/16`. Cuando todos los grupos de nodos hayan migrado, elimina el CIDR antiguo de `cidrs` y la entrada correspondiente de `pool`. Cada `pool[].cidr` debe ser uno de los valores de `cidrs` (validado por CEL).

### Migración en línea de cluster-pool a multi-pool (1.20+)

No disponible en 1.19 ni versiones anteriores. Opciones del operador: `enable-cluster-pool-to-multi-pool-migration` (predeterminado `false`), `multi-pool-migration-workers` (predeterminado `16`) e `ipam-default-ip-pool`.

Requisitos previos: la migración es unidireccional (no se puede revertir); todos los Pods existentes pasan al **pool predeterminado**; el pool predeterminado debe existir antes de reiniciar el operador (como recurso personalizado o mediante `autoCreateCiliumPodIPPools`), cubrir todos los CIDR asignados a los nodos y usar el mismo tamaño de máscara; no anules el nombre del pool predeterminado por nodo.

```bash
helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values \
  --set ipam.mode=multi-pool \
  --set ipam.operator.autoCreateCiliumPodIPPools.default.ipv4.cidrs='{10.0.0.0/8}' \
  --set ipam.operator.autoCreateCiliumPodIPPools.default.ipv4.maskSize=24 \
  --set-string extraConfig.enable-cluster-pool-to-multi-pool-migration=true \
  --set operator.rollOutPods=true \
  --set rollOutCiliumPods=false
```

Después, espera hasta que cada `CiliumNode` muestre su PodCIDR actual bajo `spec.ipam.pools.allocated`. Si BGP Control Plane anuncia PodCIDR, cambia `CiliumBGPAdvertisement` de `advertisementType: PodCIDR` a `CiliumPodIPPool` con un selector para el pool predeterminado **antes** de reiniciar los agentes (espera una retirada temporal de rutas, porque los agentes que aún usan `cluster-pool` dejan de anunciar las asignaciones migradas). Luego reinicia los agentes, todos a la vez o de forma gradual. Los agentes en modo `cluster-pool` y `multi-pool` mantienen la conectividad durante la actualización progresiva. No programes Pods en pools distintos del predeterminado hasta que se hayan reiniciado todos los agentes.

### Límites e interacción con BGP

Los CIDR de los pools no deben superponerse; la suplantación con iptables no es compatible sin `egressMasqueradeInterfaces`; para pools sin solapamiento, considera `ip-masq-agent`. Para cambiar un CIDR que esté en uso se debe seguir el procedimiento anterior de evacuación.

## IPAM basado en CRD (`ipam.mode=crd`)

El agente observa el `CiliumNode` con el nombre de su nodo. `spec.ipam.pool` es un mapa `ip -> {owner, resource}` de **direcciones IP individuales** disponibles (no se admiten CIDR); las IP utilizadas se informan en `status.ipam.used`, con actualizaciones de estado como máximo cada 15 segundos (Helm `ipam.ciliumNodeUpdateRate`). Para IPv6 se usan `spec.ipam.ipv6-pool` y `status.ipam.ipv6-used`. Solo permite enrutamiento directo.

Al iniciarse, el agente registra `Waiting for initial IP to become available in '<node>' custom resource` y necesita al menos una IP (dos si está habilitada la comprobación de estado). RBAC debe conceder acceso completo a `ciliumnodes` y `ciliumnodes/status`. La prosa de upstream aún usa `available` / `inuse`; el esquema usa `pool` / `used`, así que sigue la CRD instalada.

## IPAM de AWS ENI

### Arquitectura (1.20.2)

El operador es el único componente que llama a la API de EC2. Escribe el inventario de ENI en `CiliumNode.status.eni.enis`. El agente convierte ese inventario en CIDR de `spec.ipam.pools.allocated` para el pool `default`: una IP secundaria se convierte en `/32` y un prefijo delegado en `/28` (IPv4) o `/80` (IPv6). El agente asigna localmente las IP de Pod e informa la demanda en `spec.ipam.pools.requested`. En el modo ENI de 1.20 no se usa `CiliumPodIPPool` ni la anotación `ip-pool`. En 1.19 y 1.18, ENI usaba en su lugar el asignador basado en CRD (`spec.ipam.pool`, `status.ipam.used`). Se admite una actualización progresiva de 1.19 a 1.20: el operador reconoce los agentes nuevos por `spec.ipam.pools.requested` y porque no tienen `status.ipam.used`.

El modo ENI fuerza el enrutamiento nativo y las rutas por endpoint (`eni.enabled=true` ya los configura, así que `routingMode: native` y `endpointRoutes.enabled` en un archivo de valores son redundantes), y el agente rechaza combinar ENI con túneles. Desde 1.18, `enableIPv4Masquerade` es `false` de forma predeterminada en modo ENI. **[Versión preliminar 1.21]** `enableIPv6Masquerade` también tiene el valor predeterminado `false` en este modo.

### Instalación y preparación de nodos

Retira el CNI de VPC (`aws-node`) aplicando a su DaemonSet un `nodeSelector` imposible (upstream usa `io.cilium/aws-node-enabled=true`) e instala con `eni.enabled=true`. Crea los grupos de nodos con el taint de inicio `node.cilium.io/agent-not-ready=true:NoExecute` para que las cargas esperen al agente. Desactiva la administración de las interfaces `eth*` (salvo `eth0`) por parte de NetworkManager / systemd-networkd; de lo contrario, el sistema operativo podría quitar las IP secundarias (relevante en Amazon Linux 2023). Si sustituyes el CNI de VPC, vacía las cadenas de iptables `AWS-SNAT-CHAIN-*` y `AWS-CONNMARK-CHAIN-*`.

Permisos IAM para el operador (todos figuran en upstream; limita el alcance mediante etiquetas de recursos cuando sea posible): `ec2:DeleteNetworkInterface`, `DescribeInstanceTypes`, `DescribeNetworkInterfaces`, `DescribeSubnets`, `DescribeVpcs`, `DescribeRouteTables` (necesario desde 1.18), `DescribeSecurityGroups`, `CreateNetworkInterface`, `AttachNetworkInterface`, `ModifyNetworkInterfaceAttribute`, `AssignPrivateIpAddresses` y `CreateTags`; además, `DescribeTags` (recolección de basura de ENI, habilitada de forma predeterminada), `UnassignPrivateIpAddresses` (liberación), `AssignIpv6Addresses` (IPv6) y `DescribeInstances` (cuando se usa `--instance-tags-filter`). **[Versión preliminar 1.21]** también son opcionales `GetSecurityGroupsForVpc` (si falla, recurre a la alternativa con una advertencia) y `DescribeManagedPrefixLists` / `GetManagedPrefixListEntries`. Upstream solo documenta las acciones de asignación y liberación de IP privadas para operaciones con prefijos; confirma las acciones IAM exactas en la documentación de AWS antes de crear una política de privilegio mínimo. Proporciona credenciales mediante `eni.iamRole` (IRSA) o el secreto `cilium-aws`.

### Valores de Helm

```yaml
eni:
  enabled: true
  iamRole: arn:aws:iam::<account-id>:role/cilium-operator
  awsEnablePrefixDelegation: true
  awsReleaseExcessIPs: true
  eniTags:
    team: platform
  gcInterval: 5m                        # "0s" disables ENI garbage collection
  nodeSpec:                             # per-node settings, since 1.19
    firstInterfaceIndex: 1              # keep eth0 for node traffic
    subnetTags: ["pod-subnet=true"]
    securityGroupTags: ["cilium-pod-sg=true"]
    excludeInterfaceTags: ["no-cilium=true"]
    deleteOnTermination: true
ipam:
  nodeSpec:
    ipamMinAllocate: 16
    ipamPreAllocate: 8
  operator:
    externalAPILimitQPS: 8
    externalAPILimitBurstSize: 40
```

Las entradas de las listas de etiquetas se representan en el ConfigMap como cadenas `clave=valor` separadas por comas (por ejemplo, `eni-subnet-tags`). Hay dos tipos de filtro, y no son intercambiables: `eni.subnetIDsFilter`, `eni.subnetTagsFilter` y `eni.instanceTagsFilter`, a nivel del operador, limitan las instancias/subredes que administra el operador y presuponen que cada instancia ya tiene una ENI en una subred coincidente en el momento del despliegue; para orientar solo las ENI que **crea** Cilium, usa los valores por nodo de `eni.nodeSpec` (o la sección `eni` de una configuración CNI personalizada, que tiene prioridad sobre Helm para el mismo campo). El limitador de la API del operador tiene como valores predeterminados 4 QPS y una ráfaga de 20.

Indicadores del operador que conviene conocer (cmdref `cilium-operator-aws`): `--aws-enable-prefix-delegation`, `--aws-release-excess-ips`, `--excess-ip-release-delay` (predeterminado: 180 segundos), `--eni-gc-interval` (5 minutos), `--eni-tags`, `--parallel-alloc-workers` (50), `--limit-ipam-api-qps`, `--limit-ipam-api-burst` y `--aws-max-results-per-call`.

### Algoritmo de asignación

Parámetros por nodo (en `CiliumNode.spec.ipam`): `min-allocate`, `pre-allocate` (se considera 8 si vale 0), `max-allocate`, `max-above-watermark` (sin indicador del agente ni clave de Helm: defínelo en `CiliumNode` o en la sección `ipam` de la configuración CNI) y `static-ip-tags`. Fórmulas de `operator/pkg/ipam/nodemanager/node.go`:

```
deficit (needed) = max( preAllocate + used - available ,  minAllocate - available )
                   clamped to maxAllocate if set;  floor 0
excess  (only with --aws-release-excess-ips)
                 = max( available - used - preAllocate - maxAboveWatermark , 0 )
                   (while used is small, keep available >= minAllocate + maxAboveWatermark)
per-cycle allocation on the chosen ENI
                 = min( AvailableOnSubnet,
                        min( AvailableOnENI, needed + maxAboveWatermark + surgeAllocate ) )
   where surgeAllocate = pendingPods - needed
```

Ejemplo: `preAllocate=8`, `minAllocate=16`, un nodo con 10 direcciones disponibles y 4 en uso: déficit = max(8 + 4 - 10, 16 - 10) = 6, por lo que el operador asigna al menos 6 más. En instancias pequeñas se reduce automáticamente la preasignación a `min(8, (adapters - firstIndex) x (ipsPerENI - 1))`. El valor predeterminado de `max-allocate` es el límite de la instancia: `(adapters - firstInterfaceIndex) x (ipv4PerENI - 1)`, multiplicado por 16 con delegación de prefijos. Con `usePrimaryAddress`, cada ENI aporta una dirección adicional.

Planificación: se evalúa el déficit con cada actualización de `CiliumNode` y se hace un examen completo cada minuto; la cola de trabajo se procesa cuando hace falta, como máximo una vez por segundo, empezando por el mayor déficit. Las asignaciones se ejecutan antes que las liberaciones.

Origen de las IP: el operador recorre las ENI conectadas cuyo índice sea >= `first-interface-index` y que tengan capacidad e IP de subred disponibles; si no hay ninguna, crea una ENI. Las subredes candidatas deben estar en la misma VPC y zona de disponibilidad. Se filtran con `subnet-ids` (tiene prioridad) o `subnet-tags` (deben coincidir todas) y se elige la que tenga más direcciones libres. Si no se configura ninguno, usa la subred de la ENI principal del nodo; después, una subred de la misma tabla de rutas y, por último, la subred más grande de esa VPC/zona. Para los grupos de seguridad usa `spec.eni.security-groups`; si no está definido, `security-group-tags`; en su defecto, hereda los grupos de `eth0`. Las ENI se describen como `Cilium-CNI (<instance-id>)` y llevan las etiquetas del clúster más `--eni-tags`. Llamadas a la API: `CreateNetworkInterface`, `AttachNetworkInterface`, `ModifyNetworkInterfaceAttribute` (eliminación al terminar, predeterminada en `true`) y `AssignPrivateIpAddresses`.

### Delegación de prefijos

`eni.awsEnablePrefixDelegation=true` (anulación por nodo: `eni.nodeSpec.disablePrefixDelegation`) hace que el operador asigne prefijos `/28` (16 direcciones) en vez de IP secundarias individuales, multiplicando por 16 la capacidad de cada ENI. Restricciones indicadas por el código fuente:

- Solo funciona con tipos de instancia **Nitro o bare metal**.
- No se puede combinar con el modo de IP individuales: no se usa en un nodo que ya tenga IP secundarias `/32` en alguna ENI (se ignora la IP de la ENI principal para esta comprobación).
- La asignación usa `AssignENIPrefixes` con el recuento `ceil(needed / 16)`. Si la subred devuelve `InsufficientPrefixesInSubnet`, el operador registra que dejará de asignar prefijos en ese nodo y vuelve a usar IP secundarias `/32`.
- La subred necesita bloques `/28` contiguos disponibles; una subred fragmentada puede quedarse sin prefijos antes que sin direcciones (comportamiento del lado de AWS; consulta la documentación de AWS sobre delegación de prefijos).

### Liberación, use-primary-address e IPv6

**Liberación** (solo IPv4; requiere `--aws-release-excess-ips=true`): el agente quita de `spec.ipam.pools.allocated` los CIDR completamente libres; el operador espera `--excess-ip-release-delay` (180 segundos de forma predeterminada) y luego llama a `UnassignPrivateIpAddresses` (`/32`) o desasigna el prefijo (`/28`). La liberación **no** desconecta ni elimina ENI; la recolección de basura de ENI elimina las antiguas (etiquetas `io.cilium/cilium-managed=true` e `io.cilium/cluster-name=<name>`). El intercambio `status.ipam.release-ips` propio de 1.19 solo se aplica a agentes antiguos basados en asignador CRD.

**`usePrimaryAddress`** permite asignar a los Pods la IP privada principal de la ENI (una adicional por ENI). **[Versión preliminar 1.21]** se **elimina** el indicador del operador `--aws-use-primary-address`; configura `eni.nodeSpec.usePrimaryAddress=true` (indicador del agente `--eni-use-primary-address`, almacenado en `CiliumNode.spec.eni.use-primary-address`). Los usuarios de Helm no se ven afectados, porque el chart solo configuraba el lado del agente.

**IPv6 (beta en 1.20; el agente registra una advertencia de beta)**: configura `ipam.mode=eni`, `eni.enabled=true` e `ipv6.enabled=true`. Cada nodo recibe exactamente un prefijo delegado `/80`, asignado al crear la ENI o mediante `AssignIpv6Addresses`, y nunca se libera; no hay marcas de agua. La subred debe ser de doble pila; no se admiten subredes solo IPv6 porque cada ENI necesita una dirección IPv4 principal. La página de requisitos de EKS de upstream todavía indica que ENI solo admite IPv4; la página de ENI y la advertencia beta en tiempo de ejecución son fuentes más recientes.

### Consideraciones de ENI

La densidad de Pods está limitada por `(ENIs - firstIndex) x (IPs per ENI - 1)` (x16 con prefijos). Los Pods comparten los grupos de seguridad ENI del nodo, salvo que configures `spec.eni.security-groups` por grupo de nodos. Los clústeres con Cluster Mesh, ID de clúster entre 128 y 255 y ENI tienen un problema conocido de descarte de políticas (consulta la [parte 13](13-clustermesh-install-upgrade.md)). Se eliminaron en 1.20 (seguían presentes en 1.19): `CiliumNode.spec.eni.min-allocate`, `pre-allocate`, `max-above-watermark` e `instance-id`; los mismos valores ahora están en `spec.ipam`. Encadenar Cilium sobre el CNI de VPC es otro diseño y no se trata aquí.

## Azure, AKS y Alibaba Cloud

**AKS.** Azure CNI Powered by Cilium está administrado: usa `ipam: delegated-plugin` con la configuración CNI `"ipam": {"type": "azure-ipam"}` y `local-router-ipv4: 169.254.23.0`. Cilium no asigna IP de Pod. Los clústeres BYOCNI pueden usar cualquier IPAM de Cilium; `azure.enabled` de Helm no es compatible con BYOCNI; usa `aksbyocni.enabled`.

**Azure autoadministrado (upstream `--ipam=azure`).** Indicadores del operador: `--azure-subscription-id`, `--azure-resource-group` (para VMSS, es el grupo de recursos que contiene el VMSS; un grupo incorrecto no produce direcciones), `--azure-user-assigned-identity-id` (un ID de cliente, no un ID de recurso) y `--azure-use-primary-address`; la autenticación usa la cadena DefaultAzureCredential. Por nodo: `azure.nodeSpec.azureInterfaceName`. En 1.20, el operador publica `status.azure.interfaces[]` con un nuevo objeto `subnet{id,cidr}` (el campo plano `cidr` y `addresses[].subnet` están obsoletos). **[Versión preliminar 1.21]** Azure pasa al marco compartido de varios pools de nube (el mismo que ENI): cada dirección `succeeded` se convierte en un prefijo de host en el pool predeterminado, ya no se liberan las IP sobrantes y el agente espera hasta 5 minutos para obtener un CIDR válido de subred IPv4. Si `--ipv4-native-routing-cidr` no está definido, usa ese CIDR como CIDR de enrutamiento nativo.

**Alibaba Cloud.** Usa `ipam.mode=alibabacloud`, `alibabacloud.enabled` y, por nodo, `alibabacloud.nodeSpec.{vSwitches,vSwitchTags,securityGroups,securityGroupTags}`; el asignador se basa en CRD. La guía de instalación reemplaza Terway/Flannel y usa el secreto `cilium-alibabacloud`. Este capítulo no profundiza más: no se examinaron los límites de Alibaba ni su comportamiento con IPv6.

## Más allá de las IP de Pod: LB IPAM, Node IPAM y CiliumCIDRGroup

### LB IPAM y `CiliumLoadBalancerIPPool`

LB IPAM asigna direcciones a los Services `type: LoadBalancer`. Se ejecuta en el operador (`operator/pkg/lbipam`), siempre está compilado (Helm `enableLBIPAM`, predeterminado `true`) y permanece inactivo hasta que existe el primer pool. **Solo asigna** las direcciones: para hacerlas accesibles también necesitas BGP Control Plane (`loadBalancerClass: io.cilium/bgp-control-plane`) o L2 Announcements (`io.cilium/l2-announcer`), que se explican en la [parte 11](11-bgp-lb-egress-edge.md).

> **Ámbito de seguridad.** Los pools de LB IPAM deben usar rangos privados. Las VIP de LB IPAM no son accesibles dentro de una VPC sin integración con BGP o con el enrutamiento; en EKS, usa un balanceador de carga interno de AWS. El tráfico público debe seguir la ruta CloudFront hacia un ALB/NLB interno. LB IPAM es adecuado para entornos locales e híbridos con anuncios BGP o L2. Los ejemplos de upstream usan rangos que parecen públicos, como `20.0.0.0/8`; este capítulo usa rangos RFC 1918.

```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: blue-pool
spec:
  blocks:
  - cidr: 10.0.10.0/24
  - start: 10.0.20.100        # start and stop form ONE block; keep them in one list item
    stop: 10.0.20.200
  serviceSelector:
    matchLabels:
      color: blue
  allowFirstLastIPs: "No"     # default "Yes"; "No" reserves network/broadcast; cidr blocks only
  # disabled: true            # stop new allocations, keep existing ones
```

Datos: API `cilium.io/v2` (`v2alpha1` se marcó obsoleta por primera vez en 1.19.8), ámbito de clúster, nombres abreviados `ippools`, `ippool`, `lbippool` y `lbippools`; columnas de salida Disabled, Conflicting e IPs Available. `serviceSelector` acepta etiquetas normales y las etiquetas sintéticas `io.kubernetes.service.namespace` e `io.kubernetes.service.name`. Si los pools se superponen, el segundo queda marcado como Conflicting (condición `cilium.io/PoolConflict`) y no asigna nada. Las condiciones del pool también incluyen `cilium.io/IPsTotal`, `IPsAvailable` e `IPsUsed`. Editar un pool puede reasignar IP existentes de Services (problema upstream 40358), así que es preferible añadir otro pool o definir `disabled: true`.

Gestión de Services: LB IPAM administra los Services `LoadBalancer` sin `loadBalancerClass`, salvo que `defaultLBServiceIPAM` de Helm sea `none` (valores: `lbipam`, `nodeipam`, `none`); ignora un Service que tenga una clase desconocida. La condición del Service `cilium.io/IPAMRequestSatisfied` indica el motivo `satisfied` o `no_pool`. Familias de direcciones: de pila única de forma predeterminada (IPv4 si ambas están habilitadas); `PreferDualStack` intenta usar ambas y `RequireDualStack` queda insatisfecho si una familia está deshabilitada.

Para solicitar direcciones específicas, usa la anotación `lbipam.cilium.io/ips: "10.0.10.100,10.0.10.101"` (el campo heredado `.spec.loadBalancerIP` está obsoleto). Se sigue aplicando `serviceSelector` del pool y no debes solicitar la primera ni la última dirección de un pool cuyo `allowFirstLastIPs` sea `"No"`.

Compartir una IP entre Services:

```yaml
metadata:
  annotations:
    lbipam.cilium.io/sharing-key: "web-vip"
    lbipam.cilium.io/sharing-cross-namespace: "ns1,ns2"   # or "*"
```

En 1.20, dos Services con la misma clave para compartir pueden usar una IP si sus puertos/protocolos no entran en conflicto; si hay conflictos, reciben IP distintas del conjunto asociado a esa clave. **[Versión preliminar 1.21]** la comprobación de compatibilidad es más estricta: los Services deben usar el mismo `externalTrafficPolicy` y, si vale `Local`, ambos deben seleccionar los mismos Pods. La nueva anotación `lbipam.cilium.io/sharing-permit-different-pods: "true"` desactiva esa comprobación de seguridad y no es segura con BGP o anuncios L2 de Cilium (no conocen la capa 4, por lo que distintos nodos podrían responder por la misma IP).

Métricas (documentadas con el prefijo `cilium_`; el controlador se ejecuta en el operador, cuyo registro puede cambiar el namespace, así que el prefijo en tiempo de ejecución podría ser `cilium_operator_lbipam_*`. Esto no se verificó en ejecución: comprueba los nombres reales en tus métricas): `cilium_lbipam_conflicting_pools`, `cilium_lbipam_ips_available{pool}`, `cilium_lbipam_ips_used{pool}`, `cilium_lbipam_services_matching` y `cilium_lbipam_services_unsatisfied`.

Nota sobre el plano de datos (1.19): se descarta el tráfico TCP/UDP norte-sur a una dirección LB IPAM o ClusterIP cuando el puerto no coincide con un Service configurado.

### Node IPAM

`nodeIPAM.enabled=true` (predeterminado `false`; configura `enable-node-ipam`) permite que un Service con `loadBalancerClass: io.cilium/node` (o `defaultLBServiceIPAM: nodeipam`) publique direcciones de nodo como ingreso de su balanceador de carga. Si lo habilitas en una instalación existente, reinicia el operador (`kubectl -n kube-system rollout restart deployment/cilium-operator`). El operador rellena `status.loadBalancer.ingress` con la `ExternalIP` de cada nodo seleccionado si existe; de lo contrario, usa `InternalIP`, respetando `ipFamilies`. `externalTrafficPolicy: Cluster` usa todos los nodos; `Local` usa los nodos que alojan Pods seleccionados (requiere EndpointSlices; no se puede usar con los endpoints ficticios de Cilium Ingress/Gateway). Se excluyen los nodos con la etiqueta `node.kubernetes.io/exclude-from-external-load-balancers` o el taint `ToBeDeletedByClusterAutoscaler`; la anotación del Service `io.cilium.nodeipam/match-node-labels` limita los nodos por etiqueta.

Node IPAM publica las direcciones de los nodos como direcciones de Service. Úsalo solo si las IP de nodo son privadas; en AWS no sirve para exponer servicios públicamente.

### CiliumCIDRGroup

`CiliumCIDRGroup` es una lista con nombre de CIDR (`spec.externalCIDRs`) a la que las políticas hacen referencia con `cidrGroupRef` o `cidrGroupSelector`, en lugar de incluir los CIDR directamente. El grupo recibe una identidad de seguridad, independientemente de su tamaño, lo que mejora el escalado con listas grandes; Hubble también anota los flujos con el nombre del grupo. Tiene ámbito de clúster y nombre abreviado `ccg`. Usa `cilium.io/v2`; `v2alpha1` está obsoleta (aunque algunos ejemplos upstream todavía la usan).

```yaml
apiVersion: cilium.io/v2
kind: CiliumCIDRGroup
metadata:
  name: corp-ranges
  labels:
    tier: internal
spec:
  externalCIDRs:
  - 10.30.0.0/16
  - 192.168.100.0/24
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: egress-corp
spec:
  endpointSelector:
    matchLabels:
      app: batch
  egress:
  - toCIDRSet:
    - cidrGroupRef: corp-ranges
```

## Operaciones: inspección, métricas y actualizaciones

```bash
# per-node view of what each node owns
kubectl get ciliumnodes -o custom-columns=NAME:.metadata.name,CIDRS:.spec.ipam.podCIDRs
kubectl get ciliumnode <node> -o yaml        # .spec.ipam, .status.ipam, .status.eni.enis
kubectl get ciliumpodippools                 # multi-pool; short name cpip
kubectl get ippools                          # LB IPAM pools
kubectl -n kube-system logs deploy/cilium-operator | grep -i ipam
```

**Métricas del agente:** `cilium_ipam_capacity{family,cidr}` (la etiqueta `cidr` es el CIDR del nodo en los modos `cluster-pool` y `kubernetes`; en los demás queda vacía), `cilium_ipam_events_total{action,family}` y `cilium_ip_addresses{family}`.

**Métricas del operador** (prefijo `cilium_operator_`; habilítalas con `operator.prometheus.enabled`): `ipam_available_ips{target_node}`, `ipam_used_ips`, `ipam_needed_ips`, `ipam_ip_allocation_ops{subnet_id}`, `ipam_ip_release_ops`, `ipam_interface_creation_ops`, `ipam_interface_candidates`, `ipam_empty_interface_slots`, `ipam_available_ips_per_subnet{subnet_id,availability_zone}`, `ipam_nodes{category=total|in-deficit|at-capacity}`, `ipam_resync_total`, `ipam_allocation_duration_seconds`, `ipam_release_duration_seconds` e `ipam_background_sync_duration_seconds`. La tabla de métricas de upstream está desactualizada: omite `interface_candidates`, `empty_interface_slots`, `available_ips_per_subnet` y `background_sync_duration_seconds`; la lista anterior sigue el código fuente. Las métricas de llamadas a la API de nube no usan el prefijo `ipam_`: el subsistema toma el nombre de la nube, así que en AWS son `cilium_operator_ec2_api_duration_seconds{operation,response_code}` y `cilium_operator_ec2_api_rate_limit_duration_seconds{operation}` (Azure y Alibaba Cloud usan sus propios subsistemas). En 1.20 se eliminaron `ipam_ips` e `ipam_available_interfaces`.

Alertas sugeridas: `ipam_nodes{category="at-capacity"} > 0`, aumento de `ipam_nodes{category="in-deficit"}`, `ipam_available_ips_per_subnet` por debajo del umbral de cada zona de disponibilidad, `ec2_api_rate_limit_duration_seconds` persistentemente elevado y `lbipam_conflicting_pools > 0`.

**Notas de actualización.** Se admiten actualizaciones progresivas de ENI de 1.19 a 1.20. **[Versión preliminar 1.21]** se añaden permisos de lista/parche para `ciliumpodippools` al ClusterRole del operador (migración de versión de almacenamiento) y se elimina el indicador del operador `--aws-use-primary-address` (consulta «Liberación, use-primary-address e IPv6»). Si lo pasas directamente al operador y no mediante Helm, reemplázalo con `eni.nodeSpec.usePrimaryAddress=true` antes de actualizar.

## Laboratorios

> En esta revisión no se ejecutaron los laboratorios en un clúster activo. Se contrastaron con el código fuente y la documentación upstream (consulta «Límites de validación»). Describe con palabras lo que observas y compáralo con el comportamiento esperado; el formato exacto puede variar.

### Laboratorio 1: dimensionamiento y agotamiento de cluster-pool (kind)

Requisitos previos: kind con un clúster de dos nodos de trabajo, Cilium instalado desde Helm con el `cluster-pool` predeterminado, kubectl y Helm.

1. Instala con una máscara de nodo deliberadamente pequeña:

   ```bash
   helm upgrade --install cilium cilium/cilium --version 1.20.2 -n kube-system \
     --set ipam.mode=cluster-pool \
     --set ipam.operator.clusterPoolIPv4PodCIDRList='{10.244.0.0/16}' \
     --set ipam.operator.clusterPoolIPv4MaskSize=28
   ```
2. Consulta el bloque de cada nodo: `kubectl get ciliumnodes -o custom-columns=NAME:.metadata.name,CIDRS:.spec.ipam.podCIDRs`. Cada nodo posee un `/28` (16 direcciones).
3. Fija un Deployment a un nodo de trabajo mediante `nodeSelector` y escálalo a 20 réplicas.
4. Resultado esperado: los primeros Pods se ejecutan; cuando se ocupen las direcciones utilizables del nodo (16 menos las direcciones de red, difusión, enrutador, estado e Ingress), los Pods restantes permanecerán en `ContainerCreating` con el error de asignación de CNI. `cilium-dbg status` mostrará que se asignó todo el rango del nodo.
5. Calcula el límite esperado con la fórmula de «Cálculo de capacidad» y compáralo con el recuento observado.

Limpieza: elimina el Deployment. Reversión: la máscara es inmutable en un clúster activo, así que vuelve a instalar el clúster en lugar de editar el valor.

### Laboratorio 2: selección de varios pools (kind)

Requisitos previos: kind; Cilium 1.20.2 con `ipam.mode=multi-pool`, `kubeProxyReplacement=true`, `bpf.masquerade=true` y los pools `default` y `mars` configurados con los valores de instalación de varios pools.

1. Crea dos namespaces. Anota uno: `kubectl annotate namespace ns-a ipam.cilium.io/ip-pool=mars`.
2. Ejecuta un Pod en cada namespace y consulta `kubectl get pods -A -o wide`. Resultado esperado: el Pod del namespace anotado recibe una dirección de `10.20.0.0/16` y el otro de `10.10.0.0/16`.
3. Ejecuta un Pod en el namespace sin anotación y asígnale la anotación de Pod `ipam.cilium.io/ip-pool: mars`. Resultado esperado: la anotación del Pod tiene prioridad sobre el valor predeterminado del namespace.
4. Anota un tercer namespace con `ipam.cilium.io/require-pool-match: "true"` sin que haya un pool coincidente e inicia un Pod. Resultado esperado: queda pendiente con un error de coincidencia de pool.
5. Inspecciona `kubectl get ciliumnode <n> -o yaml` y consulta `spec.ipam.pools.requested` y `allocated`; `cilium-dbg status --all-addresses` muestra entradas `pool/ip`.

Limpieza: elimina los namespaces y, si quieres, el clúster.

### Laboratorio 3: migración en línea de cluster-pool a multi-pool (kind)

Requisitos previos: un clúster kind en 1.20.2 con `cluster-pool` y Pods en ejecución. Esta migración es unidireccional; usa un clúster desechable.

1. Guarda la salida de `kubectl get ciliumnodes -o yaml | grep -A3 podCIDRs`.
2. Ejecuta la actualización de Helm de la subsección de migración de `cluster-pool` a `multi-pool`, con un pool predeterminado que cubra los CIDR registrados y use la misma máscara.
3. Espera hasta que el PodCIDR de cada nodo aparezca en `spec.ipam.pools.allocated`.
4. Reinicia los agentes (`kubectl -n kube-system rollout restart ds/cilium`). Resultado esperado: los Pods existentes conservan sus direcciones y aparecen como restaurados; durante la actualización progresiva, los Pods siguen comunicándose entre nodos.

Reversión: no se admite. Vuelve a crear el clúster.

### Laboratorio 4: LB IPAM con anuncios L2 (kind, rango privado)

Requisitos previos: kind con `l2announcements.enabled=true` y `kubeProxyReplacement=true`; elige un rango libre dentro de la red Docker de kind (espacio privado RFC 1918).

1. Aplica un `CiliumLoadBalancerIPPool` con un bloque pequeño `start`/`stop` y un `serviceSelector`.
2. Aplica una política de anuncios L2 (consulta la parte 11) y un Service `LoadBalancer` cuyas etiquetas coincidan.
3. Resultado esperado: `kubectl get ippools` muestra que disminuyen las IP disponibles, el Service recibe una IP externa del bloque y su condición `cilium.io/IPAMRequestSatisfied` indica `satisfied`.
4. Crea un segundo pool con un bloque superpuesto. Resultado esperado: se marca como Conflicting y no asigna direcciones.
5. Define `disabled: true` en el primer pool y crea otro Service. Resultado esperado: no recibe una dirección nueva de ese pool, mientras el Service existente conserva la suya.

Limpieza: elimina los Services, los pools y la política.

### Laboratorio 5: modo EKS ENI con delegación de prefijos (cuenta de pruebas)

Requisitos previos: un clúster EKS desechable en una VPC con solo subredes privadas, nodos de tipos de instancia Nitro, sin IP públicas en los nodos, y un grupo de seguridad de nodo que solo admita referencias a grupos de seguridad de la VPC/clúster (sin `0.0.0.0/0` ni `::/0`). También se necesita IAM del operador según la subsección de instalación y preparación de nodos, y el perfil de AWS CLI de la cuenta de pruebas de destino.

1. Crea el grupo de nodos con el taint `node.cilium.io/agent-not-ready=true:NoExecute`. Deshabilita el CNI de VPC (no instales el complemento administrado o aplica a `aws-node` el selector de nodo imposible).
2. Instala Cilium con `eni.enabled=true`, `eni.awsEnablePrefixDelegation=true`, `eni.awsReleaseExcessIPs=true`, `eni.iamRole` configurado y los demás valores de la subsección de Helm.
3. Verifica el inventario: `kubectl get ciliumnode <n> -o jsonpath='{.status.eni.enis}'` muestra ENI con prefijos; `aws ec2 describe-network-interfaces --filters Name=description,Values='Cilium-CNI*'` devuelve las mismas ENI. Resultado esperado: `spec.ipam.pools.allocated` contiene bloques `/28`.
4. Escala un Deployment hasta superar un `/28` (más de 16 Pods en un nodo). Resultado esperado: el operador asigna otro prefijo; `cilium_operator_ipam_available_ips` permanece por encima de `used + preAllocate`.
5. Reduce la escala y espera más de 180 segundos. Resultado esperado: se liberan los prefijos no utilizados y la ENI permanece conectada.

Limpieza: escala a cero, desinstala Cilium, elimina el grupo de nodos y cualquier ENI `Cilium-CNI` restante (si está habilitada, la recolección de basura de ENI elimina las huérfanas etiquetadas). Reversión: vuelve a habilitar el complemento CNI de VPC en un grupo de nodos nuevo; no cambies IPAM en esos mismos nodos activos.

### Laboratorio 6: Node IPAM (kind)

Requisitos previos: kind con Cilium y `nodeIPAM.enabled=true` (reinicia el operador después de habilitarlo).

1. Crea un Service `LoadBalancer` con `loadBalancerClass: io.cilium/node`.
2. Resultado esperado: `status.loadBalancer.ingress` muestra las IP internas de los nodos (los nodos de kind no tienen `ExternalIP`).
3. Etiqueta un nodo con `node.kubernetes.io/exclude-from-external-load-balancers`. Resultado esperado: su dirección desaparece de la lista.

Limpieza: elimina el Service y la etiqueta.

## Diferencias entre versiones

| Tema | 1.18 | 1.19 | 1.20 | Versión preliminar 1.21 |
|---|---|---|---|---|
| Madurez de multi-pool | Etiqueta Beta | se quita la etiqueta | estable | estable |
| Selección de pool | solo anotación `ip-pool` | + anotaciones `ipv4-pool`/`ipv6-pool` y `podSelector`/`namespaceSelector` (ya disponibles en 1.18.14); aparecen por primera vez `require-pool-match`, `skip-masquerade` y `--only-masquerade-default-pool` | + `allowFirstIP`/`allowLastIP` | lo mismo + `pool[].reservedRanges` |
| API `CiliumPodIPPool` | v2alpha1 | v2alpha1 | v2alpha1 | almacenamiento en v2; v2alpha1 obsoleta; `cidrs` máximo 32 |
| Migración de cluster-pool a multi-pool | no | no | nuevo (`enable-cluster-pool-to-multi-pool-migration`) | igual |
| Modelo del agente ENI | asignador CRD | asignador CRD | asignador de varios pools; IPv6 beta (`/80`); liberación mediante `pools.allocated` | marco de varios pools de nube compartido con Azure |
| Helm de ENI por nodo (`eni.nodeSpec`, `ipam.nodeSpec`) | solo configuración CNI | añadido | igual | igual |
| Valores predeterminados de suplantación de ENI | `enableIPv4Masquerade` en `false` (nuevo) | | | `enableIPv6Masquerade` en `false` (nuevo) |
| IAM de ENI | + `DescribeRouteTables` | | | + opcionales `GetSecurityGroupsForVpc`, `DescribeManagedPrefixLists`, `GetManagedPrefixListEntries` |
| Operador `--aws-use-primary-address` | presente | presente | presente | **eliminado** |
| `CiliumNode.spec.eni.{min,pre}-allocate`, `max-above-watermark`, `instance-id` | presente | presente | eliminado | eliminado |
| Métricas IPAM del operador | ya están disponibles las métricas por nodo `available/used/needed_ips` e `interface_candidates` | igual | se eliminan `ipam_ips` e `ipam_available_interfaces` | |
| Azure IPAM | asignador CRD | asignador CRD | `status.azure.interfaces[].subnet` | protocolo de varios pools; no libera IP sobrantes |
| API `CiliumLoadBalancerIPPool` | v2 | v2alpha1 obsoleta | v2 | v2 |
| API `CiliumCIDRGroup` | v2alpha1 obsoleta | v2 | v2 | v2 |
| Uso compartido de LB IPAM | clave + entre namespaces | | regla de conflicto de puertos | compatibilidad más estricta + `sharing-permit-different-pods` |

## Solución de problemas

Síntoma: el Pod permanece en `ContainerCreating`; `kubectl describe pod` muestra `unable to allocate IP via local cilium agent`.

| Modo | Causa probable | Comprobación | Solución |
|---|---|---|---|
| cluster-pool / kubernetes | rango del nodo agotado (`IPAM: IPv4: N/M allocated`) | `cilium-dbg status`, `--all-addresses` | reduce la densidad o añade nodos; la máscara es inmutable, así que planifica un pool o clúster nuevo para usar una mayor |
| cluster-pool | pool agotado | `status.ipam.operator-status.error` = `allocator full` | añade un CIDR a la lista (nunca edites las entradas existentes) |
| cluster-pool | el agente no llega a iniciarse | al CiliumNode le falta `spec.ipam.podCIDRs` | revisa los registros del operador, los CIDR superpuestos y los errores de conflicto |
| kubernetes | el nodo no tiene PodCIDR | `kubectl get node -o jsonpath='{.spec.podCIDRs}'` | habilita `--allocate-node-cidrs` |
| multi-pool | `needed` supera las direcciones libres del pool | `operator-status.error`: `failed to allocate ipv4 address for node ... from pool ...` | añade un CIDR al pool o añade otro pool |
| multi-pool | no se encuentra el pool o aún no se sincronizó | `kubectl get cpip`; errores `ErrPoolNotReadyYet`, `ErrManagerPoolsNotSynced` | crea el pool antes que los Pods y comprueba que exista el pool predeterminado |
| multi-pool | coinciden dos pools | error `multiple CiliumPodIPPools match pod` | restringe los selectores |
| multi-pool | `require-pool-match` | anotación en el Pod o namespace | añade un pool coincidente o la anotación |
| ENI | límite de ENI/IP de la instancia | `ipam_nodes{category="at-capacity"}` | usa una instancia mayor o delegación de prefijos |
| ENI | subred sin IP disponibles | `ipam_available_ips_per_subnet` | añade una subred mediante etiquetas/ID; si usas delegación de prefijos, comprueba la fragmentación (se puede recurrir a `/32`) |
| ENI | limitación de solicitudes de EC2 | `ec2_api_rate_limit_duration_seconds` | ajusta `externalAPILimitQPS` / `externalAPILimitBurstSize` |
| ENI | falta una acción IAM | registro del operador | añade la acción indicada en la subsección de instalación y preparación de nodos |
| ENI | el sistema operativo quitó IP secundarias | registros de NetworkManager / systemd-networkd | excluye de la administración `eth*`, salvo `eth0` |
| cualquiera | un fallo de CNI dejó una IP asignada | la IP sigue ocupada, pero no está en ningún endpoint | espera a que expire el temporizador de 10 minutos o reinicia el agente para reconciliar el estado |

Para LB IPAM: si un Service no tiene IP externa, comprueba el indicador Conflicting del pool, la condición `cilium.io/IPAMRequestSatisfied`, la coincidencia de `serviceSelector` y que algún mecanismo (BGP o L2) anuncie la dirección. Recuerda que los modos IPAM no son interruptores: si el modo activo no coincide con el valor de Helm tras un cambio, detente y planifica una migración; no edites el ConfigMap.

## Límites de validación y fuentes

En esta revisión no se ejecutaron los laboratorios en un clúster activo. Se contrastaron los comandos, campos, valores predeterminados, fórmulas e indicadores con el código fuente y la documentación de Cilium en las etiquetas citadas. No se verificaron: los nombres de las acciones IAM para asignar y liberar prefijos (upstream solo enumera las acciones de IP privadas); la ruta de Helm para `only-masquerade-default-pool` (usa `extraConfig`); los límites de Alibaba Cloud; ni los elementos de 1.21, que proceden de la etiqueta preliminar v1.21.0-pre.3. Las etiquetas de versión de Azure, `reservedRanges` y el marco compartido de varios pools de nube pueden cambiar antes de la disponibilidad general. Los ejemplos de ENI usan una cuenta de pruebas en una VPC con subredes privadas; ninguno abre un grupo de seguridad a Internet, crea un balanceador de carga público ni asigna una IP pública a los recursos de cómputo.

Fuentes (v1.20.2, salvo que se indique otra versión):

- Conceptos de IPAM: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/index.rst
- Ámbito de clúster: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool.rst
- Varios pools: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/multi-pool.rst
- Migración de cluster-pool a multi-pool: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/cluster-pool-to-multi-pool.rst
- AWS ENI: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst
- LB IPAM: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/lb-ipam.rst
- Node IPAM: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/node-ipam.rst
- Anotaciones (clave `ip-pool`): https://github.com/cilium/cilium/blob/v1.20.2/pkg/annotation/k8s.go
- Asignador CIDR de nodo: https://github.com/cilium/cilium/blob/v1.20.2/pkg/ipam/cidrset/cidr_set.go
- Administrador de varios pools: https://github.com/cilium/cilium/blob/v1.20.2/pkg/ipam/multipool_manager.go
- Fórmulas del administrador de nodos ENI: https://github.com/cilium/cilium/blob/v1.20.2/operator/pkg/ipam/nodemanager/node.go
- Métricas: https://github.com/cilium/cilium/blob/v1.20.2/Documentation/observability/metrics.rst
- [Versión preliminar 1.21] varios pools y `reservedRanges`: https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/concepts/ipam/multi-pool.rst
- [Versión preliminar 1.21] notas de actualización: https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc
- [Versión preliminar 1.21] uso compartido de LB IPAM: https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/network/lb-ipam.rst
- AWS, CNI de EKS Hybrid Nodes: https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html

## Cuestionario

Pon a prueba tus conocimientos con el [cuestionario de la parte 10](../../quizzes/networking/cilium/10-ipam-deep-dive-quiz.md).
