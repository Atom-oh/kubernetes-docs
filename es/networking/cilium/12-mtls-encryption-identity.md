# Parte 12: mTLS, cifrado transparente e identidad

> **Base de revisión**: Cilium 1.20.2 (estable, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Los elementos marcados **[versión preliminar 1.21]** proceden de v1.21.0-pre.3 y pueden cambiar antes de la disponibilidad general.
> **Última actualización**: 15 de octubre de 2026

El modelo de seguridad de Cilium tiene tres capas que se confunden fácilmente. **La identidad y las políticas** determinan quién puede comunicarse con quién, en función de etiquetas y no de direcciones IP. **El cifrado transparente** (WireGuard, IPsec) protege los bytes que circulan entre nodos. **mTLS de cargas de trabajo** (ztunnel) vincula un canal cifrado con la identidad de una carga de trabajo. Este capítulo explica el mecanismo de cada capa y, después, cubre la función eliminada Mutual Authentication, las opciones de malla de servicios, Hubble/Tetragon y la administración de certificados.

Capítulos relacionados: [detalles internos del plano de datos eBPF](08-ebpf-datapath-internals.md), [enrutamiento superpuesto y nativo](09-overlay-native-routing.md) (interacción entre túneles y MTU), [IPAM](10-ipam-deep-dive.md), [BGP, balanceo de carga y salida](11-bgp-lb-egress-edge.md), [ClusterMesh, instalación y actualización](13-clustermesh-install-upgrade.md). Los conceptos básicos de políticas están en [IPAM y políticas de red](04-ipam-policy.md); este capítulo profundiza en el tema. La introducción a la visibilidad está en [Seguridad y visibilidad](06-security-visibility.md).

## Madurez y cronología de un vistazo

| Función | 1.18 | 1.19 | 1.20 (estable) | Versión preliminar 1.21 |
|---|---|---|---|---|
| Mutual Authentication (SPIFFE/SPIRE, `authentication.mode: required`) | Beta | Beta; `authentication.enabled` tiene `false` como valor predeterminado | **Obsoleta** (la página de documentación aún dice «Beta» en el título) | **Eliminada** |
| Cifrado transparente de ztunnel (`encryption.type=ztunnel`) | - | Beta (incorporado) | Beta; se añade `ca.type` | Beta |
| WireGuard | Estable | Estable | Estable | Estable |
| IPsec | Estable | Estable | Estable | Estable |
| WireGuard `encryption.nodeEncryption` | no verificado | no verificado | Beta | **Obsoleta; se elimina en 1.22** |
| Migración de identidad Double Write | documentada | documentada | documentada | `cilium-dbg preflight migrate-identity` se declara obsoleto en favor de esta opción |
| `identityManagementMode` | no verificado | no verificado | Beta | Beta |
| CiliumEndpointSlice | no verificado | no verificado | Beta | Beta |
| Compatibilidad con Kubernetes ClusterNetworkPolicy | - | - | Nueva, API alfa (v1alpha2) | alfa |

La fila de Mutual Authentication es la que más se informa mal. Declaración exacta:

- Fue **Beta** durante 1.18, 1.19 y 1.20 (la página de documentación 1.20 aún se titula «Mutual Authentication (Beta)»).
- Quedó **obsoleta en 1.20**: las notas de actualización de 1.20 dicen que «ahora está obsoleta y se eliminará en una versión futura», y remiten a ztunnel.
- Se **eliminó en 1.21**: las notas de actualización de 1.21 indican que «se eliminó tras quedar obsoleta» y piden quitar la configuración antes de actualizar.
- El campo `authentication` de la API de políticas **se conserva por compatibilidad con las CRD, pero no se usa** en 1.21.

## Modelo de identidad

### De las etiquetas a una identidad numérica

Cilium no aplica políticas sobre las direcciones IP. A cada endpoint (Pod) se le asigna una **identidad de seguridad**, un ID numérico derivado de las etiquetas relevantes para la identidad. Los endpoints con el mismo conjunto de etiquetas comparten un ID, de modo que una entrada del mapa de políticas cubre todas las réplicas de un Deployment y la decisión de la política sobrevive a los cambios de IP del Pod.

```
Pod labels (k8s:app=web, k8s:io.kubernetes.pod.namespace=shop, ...)
        |  filter by identity-relevant labels
        v
label set  -->  allocator (CRD or kvstore)  -->  numeric identity, e.g. 31337
        |
        +--> CiliumEndpoint.status.identity (published)
        +--> ipcache:  podIP -> identity   (every node learns it)
        +--> source node stamps identity into the packet (tunnel metadata)
                or the destination node resolves srcIP via ipcache
        +--> destination node: policy map lookup (local endpoint, remote identity, port, proto)
```

En el destino, la clave de búsqueda es el endpoint local, la identidad remota, el puerto y el protocolo. La identidad viaja con el paquete (en metadatos del túnel en el modo superpuesto) o se recupera a partir de la IP de origen mediante ipcache (en el enrutamiento nativo); por eso una entrada ipcache obsoleta o ausente puede indicar un problema con la política.

### Distribución de la identidad numérica de 32 bits

El ámbito se almacena en los bits 24 a 31:

| Ámbito | Valor | Uso |
|---|---|---|
| Global | 0 | Identidades asignadas mediante el asignador CRD/kvstore; los bits 0 a 23 se dividen entre la identidad y el ID del clúster |
| Local | `1<<24` | Identidades presentes solo en un nodo: identidades derivadas de CIDR y FQDN |
| Nodo remoto | `2<<24` | Identidades de nodo usadas para seleccionar políticas por nodo |

Con ClusterMesh, los 24 bits inferiores se comparten entre la identidad y el ID del clúster: `max-connected-clusters` 255 da 16 bits de identidad más 8 bits de ID de clúster; 511 da 15 más 9. Las identidades inferiores a 256 están reservadas (`MinimalIdentity=256`). Consulta las constantes en `pkg/identity/numericidentity.go` de v1.21.0-pre.3. El dimensionamiento de ClusterMesh se explica en la [parte 13](13-clustermesh-install-upgrade.md).

### Identidades reservadas y conocidas

Identidades reservadas, según las constantes del plano de datos (`pkg/datapath/types/types_generated.go`, v1.21.0-pre.3):

| ID | Nombre | Significado |
|---|---|---|
| 0 | unknown | Identidad sin resolver |
| 1 | host | Nodo local |
| 2 | world | Todo lo que está fuera del clúster (también identidad de CIDR de `0.0.0.0/0`) |
| 3 | unmanaged | Endpoint que Cilium no administra |
| 4 | health | Endpoints de estado de Cilium |
| 5 | init | Endpoint cuyas etiquetas aún se desconocen (inicio del Pod) |
| 6 | remote-node | Otros nodos del clúster |
| 7 | kube-apiserver | Servidor de API de Kubernetes |
| 8 | ingress | Ingress/Envoy administrados por Cilium |
| 9 / 10 | world-ipv4 / world-ipv6 | División de `world` por familia de direcciones |
| 11-14 | identidades agregadas (cluster, clustermesh, world, remote-node) | Se usan para agregar el mapa de políticas; no se asignan al tráfico |

La página de terminología upstream solo enumera los ID 0-8, por lo que 9 y 10 solo aparecen en el código fuente. Algunas identidades conocidas están disponibles sin ninguna operación de ida y vuelta a kvstore o CRD: `kube-dns` (102), `kube-dns` en EKS (103), `coredns` (104), `cilium-operator` (105) y `coredns` en EKS (106), según la página de terminología y `numericidentity.go`. Esto importa en EKS, porque los Pods DNS predeterminados reciben un ID fijo.

Comportamiento que conviene recordar: un Pod permanece como `reserved:init` hasta que se resuelven sus etiquetas; el tráfico norte-sur de un Service que llega a un backend aparece como `reserved:world` en modo túnel, mientras que con enrutamiento nativo aparece como `world` si el paquete llega al nodo que aloja el backend, y `remote-node` en caso contrario (por eso `fromEntities: cluster` coincide). Consulta `Documentation/security/policy/caveats.rst`.

### Etiquetas relevantes para la identidad y cambios de identidad

De forma predeterminada, todas las etiquetas son relevantes para la identidad salvo las que están en una lista de exclusión (por ejemplo, `io.kubernetes`, `kubernetes.io`, el nombre de Pod de StatefulSet, `pod-template-hash`, `controller-revision-hash`, `annotation.*` y `topology.kubernetes.io`). Los patrones son expresiones regulares ancladas al inicio de la etiqueta.

- Al añadir cualquier patrón **inclusivo**, el agente pasa al modo de lista permitida y agrega automáticamente `reserved:`, el namespace del Pod, las etiquetas del namespace, `policy.cluster`, la cuenta de servicio y `app.kubernetes.io`.
- `labels:` de Helm **se añade** a los valores predeterminados. Para reemplazar la lista completa, usa `--label-prefix-file` (indicadores del agente `--labels` y `--label-prefix-file`).
- Las identidades existentes no cambian hasta que se reinicia el agente; después, el operador elimina mediante recolección de basura las antiguas.
- Una etiqueta que cambia en cada versión o Pod (un SHA de compilación o una marca de tiempo) crea una identidad por valor. Esto multiplica las identidades, las entradas de ipcache y las entradas del mapa de políticas. Excluye esas etiquetas de la identidad.

Fuente: `Documentation/operations/performance/scalability/identity-relevant-labels.rst`.

### Modos de asignación

| `identityAllocationMode` de Helm | Almacén subyacente | Notas |
|---|---|---|
| `crd` (valor predeterminado del chart) | `CiliumIdentity` (`cilium.io/v2`, ámbito de clúster) | No tiene dependencias externas |
| `kvstore` | etcd | Clústeres grandes que ya ejecutan etcd |
| `doublewrite-readkvstore` | escribe en ambos; lee de kvstore | Paso de migración |
| `doublewrite-readcrd` | escribe en ambos; lee de CRD | Paso de migración |

Trampa para quien configura: el valor predeterminado del **indicador del agente** es `kvstore`, pero el **chart de Helm** configura `crd`. Lee siempre el valor efectivo del ConfigMap, no `cilium-agent --help`.

La migración Double Write (beta) permite cambiar de backend sin dejar un hueco de identidad. De kvstore a CRD: configura `doublewrite-readkvstore`, luego `doublewrite-readcrd` y, por último, `crd`. Despliega primero el operador y después los agentes (al volver a `crd` como paso final, primero los agentes y luego el operador, según la guía de actualización). La secuencia se puede revertir. La convergencia se observa con los gauges del operador `doublewrite_{crd,kvstore,crd_only,kvstore_only}_identities`, publicados como `cilium_operator_doublewrite_crd_identities`, `cilium_operator_doublewrite_kvstore_identities`, `cilium_operator_doublewrite_crd_only_identities` y `cilium_operator_doublewrite_kvstore_only_identities` (v1.20.2 `operator/doublewrite/metrics.go:13-33`; `Documentation/observability/metrics.rst` lista los mismos nombres). La guía de actualización de v1.20.2 (`Documentation/operations/upgrade.rst`) todavía menciona los nombres antiguos `cilium_operator_identity_*_count`, que el código ya no registra; no crees alertas para ellos. Espera hasta que los dos valores `*_only_identities` lleguen a cero antes del paso siguiente. En 1.21, `cilium-dbg preflight migrate-identity` se declara obsoleto en favor de Double Write. Fuente: `Documentation/operations/upgrade.rst`.

### Identidades administradas por el operador (beta)

`identityManagementMode` de Helm admite `agent` (valor predeterminado), `operator` o `both` (este último solo durante la migración). Con `operator`, el operador asigna identidades, lo que evita que muchos agentes creen a la vez identidades CIDR duplicadas.

1. De agente a operador: configura `both` y reinicia el operador; luego configura `operator` y reinicia los agentes.
2. Reversión: cambia los agentes a `both` y luego el operador a `agent`.
3. Después de cambiar los patrones de etiquetas relevantes para la identidad, reinicia tanto el operador como los agentes.

Relacionado: `operator.identityGCInterval` (15m0s) e `identityHeartbeatTimeout` (30m0s) en el chart; indicadores del agente `identity-allocation-timeout` (2m), `identity-change-grace-period` (5s) e `identity-restore-grace-period` (30s).

### CiliumEndpoint, CiliumEndpointSlice e ipcache

- **CiliumEndpoint (CEP)**: uno por cada Pod administrado por Cilium, con el mismo nombre y namespace. El estado contiene etiquetas, ID de identidad y política aplicada. Los CEP `cilium-health-<node>` residen en `kube-system`.
- **CiliumEndpointSlice (CES, beta; la CRD sigue siendo `cilium.io/v2alpha1`)**: el operador agrupa CEP reducidos en objetos CES y los agentes observan esos CES. Reduce la carga del servidor de API a cambio de un retraso en el descubrimiento de identidades nuevas de endpoint. Helm `ciliumEndpointSlice.enabled` (predeterminado `false`) y `rateLimits`; la anotación del namespace `cilium.io/ces-namespace: priority` da prioridad a un namespace. No es compatible con Egress Gateway. Migra primero el operador y luego los agentes; para una reversión, primero los agentes. El indicador `--ces-slice-mode` se eliminó en 1.20.
- **ipcache**: el mapa BPF `cilium_ipcache_v2` asocia IP o CIDR con una identidad. Inspección: `cilium-dbg bpf ipcache list|get|match` y `cilium-dbg identity list|get`.
- Cada endpoint tiene un mapa de políticas cuyo tamaño define `--bpf-policy-map-max` (predeterminado: 16384).

Muchos CIDR distintos en una política crean muchas identidades de ámbito local (una por selector CIDR); por eso conviene preferir `CiliumCIDRGroup`, explicado más adelante.

### Inspección del estado de identidad

```bash
kubectl get ciliumidentities
kubectl get cep -A -o wide
kubectl -n kube-system exec ds/cilium -- cilium-dbg identity list
kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf ipcache list
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint list
```

## Modelo de políticas en profundidad

### Recursos de políticas

| Recurso | Ámbito | Notas |
|---|---|---|
| Kubernetes `NetworkPolicy` | namespace | L3/L4 |
| `CiliumNetworkPolicy` (CNP, cilium.io/v2) | namespace | L3-L7, entidades, FQDN y denegación |
| `CiliumClusterwideNetworkPolicy` (CCNP) | clúster | También permite políticas de host mediante `nodeSelector` |
| `ClusterNetworkPolicy` (`policy.networking.k8s.io`, v1alpha2) | clúster | **Nueva en 1.20**, API alfa; requiere habilitación explícita |
| `CiliumCIDRGroup` | clúster | Conjunto de CIDR con nombre al que hacen referencia las reglas |

Semántica: las reglas forman una lista permitida y se combinan mediante unión; la aplicación tiene estado (se permite el tráfico de respuesta); la dirección cambia a denegación predeterminada cuando existe al menos una regla que selecciona el endpoint para esa dirección.

### Modo de aplicación, denegación predeterminada y modo de auditoría

| Control | Configuración | Efecto |
|---|---|---|
| `policyEnforcementMode` (indicador `enable-policy`) | `default` / `always` / `never` | `default`: el endpoint queda abierto hasta que se selecciona; `always`: denegación predeterminada en todas partes; `never`: políticas desactivadas |
| `enableDefaultDeny: {ingress, egress}` en una regla | por regla | Una regla que selecciona el endpoint no cambia esa dirección a denegación predeterminada |
| `enableNonDefaultDenyPolicies` de Helm | `true` | Habilitación en el nivel del chart para ese tipo de reglas |
| Modo de auditoría | Indicador del agente `--policy-audit-mode=true` (ConfigMap `policy-audit-mode`) o configuración por endpoint | Los descartes previstos se registran con el veredicto `AUDIT`, en lugar de descartarse |
| `policyDenyResponse` | `none` / `icmp` | `icmp` es experimental y solo se aplica a la salida |

Importante: `enableDefaultDeny: false` **no** se aplica a L7. Una regla L7 sin una regla complementaria que permita todo el tráfico sigue descartando cualquier otro tráfico de ese puerto.

Modo de auditoría para todo el clúster y por endpoint:

```bash
kubectl -n kube-system patch cm cilium-config --type merge \
  -p '{"data":{"policy-audit-mode":"true"}}'
kubectl -n kube-system rollout restart ds/cilium
# or for one endpoint (host endpoint included):
kubectl -n kube-system exec ds/cilium -- cilium-dbg endpoint config <ID> PolicyAuditMode=Enabled
hubble observe --verdict AUDIT
```

Usa el modo de auditoría como primer paso de cualquier despliegue de denegación predeterminada; el veredicto `AUDIT` en Hubble muestra qué tráfico se habría descartado. Fuente: `Documentation/security/policy-creation.rst`.

### Entidades

`host`, `remote-node`, `kube-apiserver`, `ingress`, `cluster`, `cluster-mesh`, `init`, `health`, `unmanaged`, `world`, `all`. `world` equivale a `0.0.0.0/0`. El ingreso `kube-apiserver` puede no funcionar en algunas plataformas administradas (AKS y GKE, según upstream). El indicador del agente `--allow-localhost=policy` desactiva la autorización implícita del host hacia Pods locales.

### Selección por nodo y CIDR

- `fromNodes` / `toNodes` requieren `nodeSelectorLabels: true` (indicador `--enable-node-selector-labels`). Los nodos reciben entonces identidades de ámbito `remote-node`. Dimensionamiento de upstream: aproximadamente 1 MB por cada 1000 nodos con `policy-cidr-match-mode=nodes`.
- De forma predeterminada, las reglas CIDR (`fromCIDR`, `toCIDR`, `fromCIDRSet`, `toCIDRSet` con `except`) **no** coinciden con Pods ni nodos. `policyCIDRMatchMode` (`--policy-cidr-match-mode`, beta) habilita `pods` y/o `nodes`; `pods` consume identidades adicionales. El comentario en línea de `values.yaml` solo menciona `nodes`; la documentación permite ambas opciones, así que sigue la documentación. La configuración de conformidad de Kubernetes ClusterNetworkPolicy usa `pods,nodes`.
- **CiliumCIDRGroup** agrupa muchos CIDR en un objeto con nombre, usando aproximadamente una identidad por grupo, y anota los flujos de Hubble con el nombre del grupo. La versión de almacenamiento de la CRD es `cilium.io/v2` en 1.18-1.21 (v2alpha1 todavía se sirve); el ejemplo de la página de documentación upstream aún usa `v2alpha1`, así que usa v2:

```yaml
apiVersion: cilium.io/v2
kind: CiliumCIDRGroup
metadata:
  name: vpn-example-1
  labels:
    role: vpn
spec:
  externalCIDRs:
  - 10.48.0.0/24
  - 10.16.0.0/24
---
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: from-vpn-example
  namespace: demo
spec:
  endpointSelector: {}
  ingress:
  - fromCIDRSet:
    - cidrGroupRef: vpn-example-1
```

Haz referencia con `cidrGroupRef: <name>` o con `cidrGroupSelector.matchLabels`.

### Políticas FQDN y proxy DNS

`toFQDNs` usa `matchName` o `matchPattern` (`*` coincide con una etiqueta; `**.` es un prefijo de varias etiquetas; `*.cilium.io` no coincide con `cilium.io` en sí). Mecanismo: el proxy DNS del agente, que se ejecuta en cada agente, observa las respuestas DNS e instala las IP resueltas como identidades derivadas de FQDN (de ámbito local). Por tanto:

- Se necesita una regla DNS de salida (`toPorts.rules.dns`) hacia el DNS del clúster para que el proxy vea las respuestas.
- `toFQDNs` no se puede combinar con otros selectores L3 en la misma regla.
- Si se reinicia el agente, no se puede acceder al proxy DNS durante ese intervalo.
- FQDN es una lista de nombres permitidos, no una comprobación de reputación. IPsec con el proxy L7 requiere `--dnsproxy-enable-transparent-mode=true`.
- Hay discrepancia entre la documentación y el código sobre el límite de IP por nombre de host por endpoint. En vez de confiar en una cifra de la prosa, consulta el valor efectivo del indicador `tofqdns-endpoint-max-ip-per-hostname` del agente y de Helm `dnsProxy.endpointMaxIpPerHostname` en tu versión.
- `dnsProxy.preCache` / `--tofqdns-pre-cache` se declara obsoleto en 1.20 y su eliminación está prevista para 1.21. El proxy DNS independiente es alfa.

### Políticas de denegación y precedencia

`ingressDeny` / `egressDeny` tienen prioridad sobre todas las reglas de permiso de CNP, CCNP y Kubernetes NetworkPolicy. No existe denegación L7 ni denegación `toFQDNs`. Orden práctico de evaluación:

| Orden | Tipo de regla | Resultado |
|---|---|---|
| 1 | Coincide una regla de denegación | Descartar, independientemente de cualquier permiso |
| 2 | Coincide una regla de permiso | Reenviar |
| 3 | Endpoint seleccionado para esta dirección; no coincide ninguna regla | Descartar (denegación predeterminada) |
| 4 | Endpoint no seleccionado para esta dirección | Reenviar (salvo que el modo de aplicación sea `always`) |

Con Kubernetes ClusterNetworkPolicy, los niveles son: primero Admin, luego NetworkPolicy (Kubernetes NetworkPolicy, CNP y CCNP) y, por último, Baseline. Habilítala con `k8sClusterNetworkPolicy.enabled=true` (predeterminado `false`; indicador `--enable-k8s-cluster-network-policy`) e instala la CRD del proyecto network-policy-api, `release-0.2`. En Cilium 1.20 es una API alfa.

### Ejemplos de patrones de políticas

**Denegación predeterminada con DNS y salida FQDN** (namespace `demo`). Al seleccionar el endpoint con una regla de salida, la salida pasa a denegación predeterminada; por eso el DNS debe permitirse de forma explícita y mediante una regla DNS para que el proxy vea las respuestas:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: egress-fqdn
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: client
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: "53"
        protocol: ANY
      rules:
        dns:
        - matchPattern: "*"
  - toFQDNs:
    - matchName: "api.example.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```

En EKS, los Pods DNS son `coredns` con la etiqueta `k8s-app: kube-dns`; ajusta el selector si tu distribución usa otras etiquetas.

**Permitir tráfico solo desde dentro del clúster, nunca desde `world`** (esto también cierra la ventana de fuga de texto sin cifrar que se describe en «Cifrado transparente»):

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: cluster-only-ingress
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: server
  ingress:
  - fromEntities:
    - cluster
```

**Interceptar todo el DNS sin denegación predeterminada** (patrón literal de la página introductoria upstream): una `CiliumClusterwideNetworkPolicy` con `enableDefaultDeny: {egress: false, ingress: false}` selecciona todos los Pods salvo los de `kube-system` y `kube-dns`, y permite el DNS hacia `kube-dns` con `matchPattern: "*"`. Introduce el proxy DNS en la ruta (para que Hubble vea los nombres DNS) sin activar denegación predeterminada para el resto del tráfico.

**Denegar una identidad independientemente de los permisos:**

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: deny-untrusted
  namespace: demo
spec:
  endpointSelector:
    matchLabels:
      app: server
  ingressDeny:
  - fromEndpoints:
    - matchLabels:
        trust: low
```

**Estructura básica de una política de host** (requiere `hostFirewall.enabled=true`; empieza en modo de auditoría para el endpoint de host y permite primero SSH/SSM, kubelet y la ruta al servidor de API):

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: host-ingress-from-cluster
spec:
  nodeSelector:
    matchLabels:
      node-role: worker
  ingress:
  - fromEntities:
    - cluster
    toPorts:
    - ports:
      - port: "10250"
        protocol: TCP
```

Como la denegación predeterminada se aplica al endpoint de host en cuanto una regla de ingreso lo selecciona, una política como esta descarta todo lo demás (incluido SSH) en los nodos coincidentes. Obtén el ID del endpoint de host con `cilium-dbg endpoint get -l reserved:host -o jsonpath='{[0].id}'`, configura primero `PolicyAuditMode=Enabled` en él y observa `hubble observe --verdict AUDIT` antes de aplicar la política.

### Lectura de la decisión de una política

```
cilium-dbg endpoint list                       # endpoint ID, identity, ingress/egress enforcement
cilium-dbg endpoint get <ID> -o json           # labels, identity, policy revision
cilium-dbg bpf policy get <ID>                 # the per-endpoint policy map (identity, port, proto, deny flag)
cilium-dbg policy selectors                    # which identities each selector currently matches
hubble observe --pod demo/server --verdict DROPPED -o json   # drop reason and (with correlation) the policy that matched
```

Si un selector coincide con menos identidades de las esperadas, lo habitual es una discrepancia en las etiquetas relevantes para la identidad (por ejemplo, una etiqueta excluida de la identidad) o una CNP con ámbito de namespace que añade implícitamente el namespace a sus selectores.

### Rechazo CEL de políticas vacías (1.20)

En 1.20, las CRD CNP y CCNP incluyen la regla CEL `has(self.spec) || has(self.specs)` con el mensaje «spec or specs must be provided». Se rechaza en admisión la creación o actualización de una política que no tenga ninguno de esos campos. Las políticas vacías existentes no se ven afectadas hasta que se actualizan. Cambios relacionados anteriores: `FromRequires` / `ToRequires` deben estar vacíos desde 1.19, y la política L7 de Kafka/proxylib se eliminó en 1.20.

### Políticas de host

Una `CiliumClusterwideNetworkPolicy` con `nodeSelector` se convierte en una política de host. Requiere `hostFirewall.enabled=true` (y, de forma opcional, `devices`). Se aplica al namespace de host y a los Pods que usan la red del host, y admite L3/L4 además de DNS L7 (beta). `--enable-extended-ip-protocols` es necesario para VRRP, IGMP, GRE, IPIP, IPV6, ESP y AH. Problemas conocidos de upstream: las políticas de host no funcionan con IPsec, no se aplican a las interfaces WireGuard del host y, al habilitarlas, se descartan los protocolos L2 desconocidos. Las políticas DNS L7 de host pueden interrumpir la descarga de imágenes de kubelet y los reinicios del agente; empieza con el modo de auditoría.

### Incorporaciones de la versión preliminar 1.21 **[versión preliminar 1.21]**

`toPorts[].listener` de salida CNP redirige un puerto a un listener Envoy de CEC/CCEC (no se puede combinar con reglas L7 en el mismo puerto; upstream recomienda Gateway API/GAMMA en su lugar). `--fixed-identity-mapping` se declara obsoleto.

## Cronología de autenticación: Mutual Authentication (eliminada)

### Cómo funcionaba (1.18-1.20)

Una regla incluía `authentication: {mode: required}`. En el plano de datos, una coincidencia de política con ese indicador consulta el mapa BPF `cilium_auth_map` (524288 entradas; clave = identidad local, identidad remota, nodo remoto y tipo de autenticación). Si no hay una entrada vigente, se descarta el paquete (`DROP_POLICY_AUTH_REQUIRED`, -189) y se envía una señal al agente. El administrador `pkg/auth` del agente abría, fuera de banda, una conexión TLS 1.3 **hacia el agente del nodo remoto** por el puerto 4250 (`authentication.mutual.port`), presentaba SVID SPIFFE obtenidos de un socket del agente SPIRE (identidades `spiffe://spiffe.cilium/identity/<numeric-id>`), verificaba el certificado del peer y guardaba en el mapa auth la fecha de vencimiento más temprana. Los paquetes retransmitidos pasaban entonces. Punto clave: el handshake era **entre agentes**, no por conexión ni en el plano de datos; el tráfico de aplicaciones no se cifraba a menos que también se habilitara WireGuard o IPsec. Límites conocidos: no admitía ClusterMesh, solo se probó con SPIRE y no interoperaba con mTLS externo.

### Cronología y pasos siguientes

| Versión | Estado | Acción |
|---|---|---|
| 1.18, 1.19 | Beta; en 1.19, `authentication.enabled` tiene `false` como valor predeterminado y las políticas con `authentication` reenvían silenciosamente sin autenticar (con una advertencia de validación) | Déjalo como está o migra |
| 1.20 | Obsoleta (la documentación aún la etiqueta como Beta) | Planifica la migración a ztunnel (`encryption.type=ztunnel`) o a cifrado de red junto con políticas de identidad |
| 1.21 | Eliminada; desaparecieron `pkg/auth` del agente y los indicadores `mesh-auth-*`; se acepta el campo de política `authentication`, pero no se usa | Quita los valores Helm `authentication.*` y la configuración de autenticación mutua de SPIRE **antes** de actualizar |

Guía de migración:

1. Enumera las políticas que usan `authentication`: `kubectl get cnp,ccnp -A -o yaml | grep -n "authentication"`.
2. Decide cuál era realmente el requisito. Si era «cifrado en tránsito», usa WireGuard o IPsec ([más abajo](#transparent-encryption)). Si era «identidad autenticada de la carga de trabajo», usa mTLS de ztunnel o una malla (Istio).
3. No des por hecho que el campo sigue aplicando la política en 1.21: upstream dice que se acepta por compatibilidad, pero no se usa; por tanto, una política que dependía de `required` ya no exige autenticación. No se verificó cómo lo notifica el agente durante la ejecución.
4. En 1.21, los valores Helm `authentication.mutual.spire.*` solo se conservan porque la instalación de SPIRE y el cliente SPIRE del operador también los usa ztunnel con `ca.type=spire`. Ya no configuran autenticación mutua.
5. `dropEventEmitter.reasons` de Hubble ya no incluye `auth_required` en 1.21.

## mTLS de cargas de trabajo con ztunnel (beta desde 1.19)

### Arquitectura

`encryption.type=ztunnel` hace que Cilium ejecute el proxy L4 de Istio por nodo (concepto ztunnel), con Cilium como plano de control.

```
 enrolled Pod A (netns)                         enrolled Pod B (netns)
  app --> iptables (in-pod) --> :15001           :15008 (HBONE in) --> ztunnel --> :15006 --> app
                                   |                  ^
                                   v                  |
                    node A ztunnel (DaemonSet, hostNetwork)  ==HBONE: HTTP/2 CONNECT over mTLS, TCP 15008==> node B ztunnel
                                   ^   xDS (workloads)   ^ CSR to Cilium CA
                                   |                     |
                     Cilium agent: xDS/ADS server, ZDS unix socket (/var/run/cilium/ztunnel.sock),
                                   built-in CA (IstioCertificateService), enrollment reconciler
```

- En cada nodo se ejecuta un DaemonSet `ztunnel-cilium` (hostNetwork, contenedor `istio-proxy`); en 1.20 y 1.21 la imagen es `quay.io/cilium/ztunnel:v1.0.0` (en 1.19 se usaba `docker.io/istio/ztunnel` 1.28.0-distroless).
- El agente sirve los datos de cargas de trabajo (de CEP) mediante xDS, pasa descriptores de archivos de los namespaces de red de Pods y metadatos por el socket Unix ZDS, y firma CSR de cargas con URI SAN `spiffe://<trust domain>/ns/<ns>/sa/<sa>` para las cuentas de servicio que tienen endpoints en ese nodo.
- Se instalan reglas iptables **dentro del namespace de red de cada Pod inscrito**: la salida se dirige al puerto 15001, el ingreso sin cifrar al 15006 y el ingreso HBONE en 15008 no se redirige (marca 0x539). El protocolo en la red es HBONE (HTTP/2 CONNECT sobre mTLS) por **TCP 15008**.
- Diferencias con Istio ambient: no hay istiod, waypoint ni funciones L7; la inscripción usa la etiqueta `io.cilium/mtls-enabled=true`, no `istio.io/dataplane-mode=ambient`; la CA es la CA interna de Cilium o SPIRE. No ejecutes ambas soluciones en los mismos Pods.

### Secrets, tipo de CA e inscripción

Genera el material de claves de arranque y de la CA antes de instalar (script upstream `examples/kubernetes-ztunnel/generate-secrets.sh`). El Secret `cilium-ztunnel-secrets` de `kube-system` contiene `bootstrap-private.key`, `bootstrap-root.crt`, `ca-private.key` y `ca-root.crt`. Según upstream, el par de arranque protege la conexión de ztunnel al servidor xDS y de certificados de Cilium; el par de la CA sirve como raíz de los certificados efímeros de las cargas de trabajo, guardados en memoria.

```yaml
# values-ztunnel.yaml
encryption:
  enabled: true
  type: ztunnel
  ztunnel:
    ca:
      type: internal   # default; "spire" is new in 1.20
```

| `encryption.ztunnel.ca.type` | Comportamiento |
|---|---|
| `internal` (predeterminado) | La CA integrada de Cilium firma los certificados de las cargas; no se ejecuta un reconciliador de SPIRE |
| `spire` (desde 1.20) | Un servidor SPIRE externo emite las identidades; el operador registra entradas (parent `/ztunnel`, ruta `/ns/<ns>/sa/<sa>`) para las cuentas de servicio de los namespaces inscritos |

El modo `spire` no se describe en la guía de cifrado upstream; en esta revisión solo se verificó la ruta de código del operador, no una implementación integral. Considéralo una opción avanzada y pruébalo por separado.

Inscribir o quitar un namespace:

```bash
kubectl label namespace demo io.cilium/mtls-enabled=true
kubectl label namespace demo io.cilium/mtls-enabled-      # disenroll
```

Se inscriben todos los Pods existentes (salvo los de ztunnel) y futuros del namespace. La inscripción solo se realiza en el nivel del namespace; se omiten los Pods que usan la red del host.

### Límites

| Límite | Detalle |
|---|---|
| Ambos peers inscritos | No se admite tráfico de un peer inscrito a otro que no lo esté |
| Solo TCP | No se redirigen UDP ni otros protocolos |
| Interacción con políticas | El tráfico se cifra antes de salir del Pod, así que la política L4 no puede ver los puertos internos; solo se puede seleccionar el puerto HBONE 15008 |
| Kernel | Requiere compatibilidad con iptables |
| ClusterMesh | Incompatible; al habilitar ambos se produce un error de validación |
| Inscripción | Solo mediante etiqueta de namespace; no se inscriben Pods individuales |

En EKS, los peers están en la misma VPC, así que los grupos de seguridad de nodo deben permitir TCP 15008 entre nodos (con referencia al propio grupo de seguridad de nodo; nunca a un CIDR público).

### Verificación

```bash
kubectl -n kube-system describe cm cilium-config | grep enable-ztunnel -A2
kubectl get namespaces -l io.cilium/mtls-enabled=true
kubectl -n kube-system exec ds/cilium -- cilium-dbg statedb dump | jq '.["mtls-enrolled-namespaces"]'
# inside a Cilium Pod on the node hosting an enrolled Pod (install tcpdump first)
tcpdump -i eth0 port 15008      # use cilium_vxlan when tunnelling
```

## Cifrado transparente {#transparent-encryption}

Reglas comunes: de forma predeterminada solo se cifra el tráfico de Pods administrados por Cilium que cruza nodos; el tráfico entre Pods del mismo nodo nunca se cifra. El tráfico de salida hacia un endpoint que el nodo aún no ha aprendido puede salir sin cifrar, porque la decisión usa el mismo mecanismo de ipcache/políticas. Mitígalo con el modo estricto o una política de salida que deniegue `world`.

### Recorrido del paquete cifrado

```
Pod A (node 1) -> Pod B (node 2), WireGuard, tunnel mode

 Pod A veth --> bpf_lxc: policy ok, ipcache says dst is remote Cilium endpoint
            --> encryption marks the packet (dst is a managed remote endpoint)
            --> VXLAN/Geneve encapsulation (cilium_vxlan / cilium_geneve)
            --> routed into cilium_wg0 (WireGuard: UDP 51871, peer chosen by CiliumNode pubkey)
            --> NIC (outer IP: node 1 -> node 2)
 NIC (node 2) --> cilium_wg0 decrypt --> tunnel decapsulation --> bpf_lxc ingress policy --> Pod B

Native routing: the VXLAN/Geneve steps are absent; the inner packet is Pod A -> Pod B directly
inside WireGuard. IPsec uses the same decision point but the XFRM state for (src node, dst node)
applies ESP after encapsulation.
```

Este es un resumen conceptual, no una traza del orden exacto de los programas BPF; consulta la [parte 8](08-ebpf-datapath-internals.md) para ver su estructura. Se desprenden dos consecuencias. Primero, la decisión «¿el destino es un endpoint remoto administrado?» se basa en ipcache, así que un destino no aprendido se considera externo (la ventana de fuga). Segundo, como el cifrado ocurre después de la política y la encapsulación, una captura en el host sobre la NIC física solo ve texto cifrado, mientras que una captura en `cilium_wg0` ve el paquete interno.

### WireGuard (estable)

Mecanismo: cada agente genera un par de claves, publica la clave pública en la anotación `network.cilium.io/wg-pub-key` de `CiliumNode` y configura un peer de WireGuard para cada otro nodo en el dispositivo `cilium_wg0`. Usa el puerto UDP **51871** en cada nodo. Requiere WireGuard en el kernel (`CONFIG_WIREGUARD`, Linux 5.6 o posterior, o el módulo externo). En modo túnel, el tráfico de Pod se encapsula dos veces: primero VXLAN/Geneve y luego WireGuard, por lo que importa la MTU ([parte 9](09-overlay-native-routing.md)).

```yaml
encryption:
  enabled: true
  type: wireguard
  wireguard:
    persistentKeepalive: 0s
```

- Con encadenamiento CNI (AWS VPC CNI), configura `cni.enableRouteMTUForCNIChaining=true`; de lo contrario, el tráfico cifrado de los Pods puede fragmentarse.
- ClusterMesh requiere WireGuard en todos los clústeres y UDP 51871 entre ellos.
- Los descartes de paquetes mientras se configura el dispositivo son un problema conocido (gh-33159 upstream).
- **Nodo a nodo** (`encryption.nodeEncryption`, beta): amplía el cifrado al tráfico del host. Los nodos del plano de control se excluyen mediante `node-encryption-opt-out-labels`. Hay brechas en las rutas norte-sur con XDP o DSR sin Geneve. **[Versión preliminar 1.21]** obsoleto; se elimina en 1.22.

### Modo estricto

| Valor de Helm | Significado |
|---|---|
| `encryption.strictMode.egress.enabled` | Descarta el tráfico sin cifrar que sale de un nodo hacia el CIDR estricto |
| `encryption.strictMode.egress.cidr` | CIDR de Pod que se debe proteger (solo IPv4; IPv6 queda desprotegido) |
| `encryption.strictMode.egress.allowRemoteNodeIdentities` | Necesario con túneles o cuando se superponen los CIDR de nodo y Pod |
| `encryption.strictMode.ingress.enabled` | Descarta el tráfico de ingreso interno del clúster que no llegó mediante WireGuard; **solo WireGuard** |

El modo estricto de ingreso (desde 1.19) es compatible tanto con túnel como con enrutamiento nativo según la documentación 1.20.2 (las notas de actualización 1.19 indicaban que se requería túnel). Límites: incompatible con el encadenamiento CNI, no protege el tráfico nodo a nodo y depende de que el programa BPF de Cilium esté conectado a todas las interfaces que puedan transportar tráfico de Pods.

**Cambio de indicadores en 1.20**: se **eliminaron** los antiguos indicadores `--enable-encryption-strict-mode`, `--encryption-strict-mode-cidr` y `--encryption-strict-mode-allow-remote-node-identities` (obsoletos desde 1.19). Usa `--enable-encryption-strict-mode-egress`, `--encryption-strict-egress-cidr`, `--encryption-strict-egress-allow-remote-node-identities` y `--enable-encryption-strict-mode-ingress`. Helm cambió de `encryption.strictMode.{enabled,cidr,allowRemoteNodeIdentities}` a `encryption.strictMode.egress.*`. La nota de actualización 1.20 escribe `cidrs` para el valor CIDR, pero `values.yaml` del chart 1.20.2 usa `cidr`; prevalece el chart.

### IPsec (estable)

Mecanismo: el agente configura estados y políticas XFRM de Linux a partir de una clave precompartida en un Secret. Los paquetes se encapsulan en ESP después de cualquier encapsulación superpuesta (desde 1.18 este orden es fijo; ya no existe la opción `encryptedOverlay`).

```bash
kubectl create -n kube-system secret generic cilium-ipsec-keys \
  --from-literal=keys="3+ rfc4106(gcm(aes)) $(dd if=/dev/urandom count=20 bs=1 2>/dev/null | xxd -p -c 64) 128"
```

```yaml
encryption:
  enabled: true
  type: ipsec
  ipsec:
    secretName: cilium-ipsec-keys
    keyWatcher: true
    keyRotationDuration: 5m
```

- Formato del valor del Secret: `key-id algorithm PSK-hex key-size`. El signo `+` después del ID de clave fuerza **claves derivadas por túnel**; las claves globales quedaron obsoletas en 1.16 (GHSA-pwqm-x5x6-5586).
- Rotación: los ID de clave van del 1 al 15 y deben aumentar con cada nueva clave; al llegar a 15 se vuelve al 1 (`encryption-ipsec.rst:206-218`; el fragmento upstream establece `KEYID` en 0 cuando es 15 o superior). Por eso, un simple «parche con un ID más alto» falla al llegar al límite: después del ID 15, el siguiente Secret debe usar el ID 1. Aplica el Secret con el ID siguiente; los agentes lo observan (`keyWatcher`) y quitan la clave anterior después de `keyRotationDuration` más una fluctuación de hasta una décima parte de ese tiempo. No rotes durante una actualización. Con ClusterMesh, rota en todos los clústeres.
- El enrutamiento directo requiere `ipv4NativeRoutingCIDR`. No se admite con encadenamiento CNI. Máximo: 65535 nodos; el descifrado de un túnel está vinculado a un único núcleo de CPU.
- Verifica con `cilium-dbg encrypt status` (claves en uso y contadores de errores XFRM) y `tcpdump -l -n -i eth0 esp`. Los grupos de seguridad deben permitir ESP (protocolo IP 50) entre nodos, mediante una referencia a sí mismos; en esta revisión no se verificó el requisito de UDP 500/4500.
- **Eliminados en 1.20**: `encryption.ipsec.interface` (`--encrypt-interface`, sin efecto desde 1.18) y `encryption.ipsec.encryptedOverlay`. `values.yaml` del chart 1.20.2 y la guía IPsec todavía mencionan `interface`, una inconsistencia upstream; no lo configures.
- **Las políticas de host no funcionan con IPsec** (gh-41854 upstream).

### Sobrecarga de MTU

El cifrado añade bytes de cabecera, que reducen la MTU utilizable del Pod; el modo túnel suma además la cabecera del túnel. Cilium deriva automáticamente la MTU de las rutas; con encadenamiento CNI, configura `cni.enableRouteMTUForCNIChaining`. La parte 9 calcula los bytes usando `pkg/mtu/mtu.go` (v1.20.2): WireGuard 95, IPsec 77 con el tamaño de clave predeterminado y VXLAN sobre infraestructura IPv4 50; consulta su [sección sobre el cálculo de MTU](09-overlay-native-routing.md). Son cálculos, no mediciones; confirma con `ping -M do -s <size>` entre Pods y `ip link` en los dispositivos de Cilium.

### Cómo elegir

| Necesidad | Elegir |
|---|---|
| Cifrado sencillo de la red Pod a Pod, sin administrar claves | WireGuard |
| FIPS/cumplimiento o kernel sin WireGuard; se acepta la gestión de rotación de claves | IPsec |
| Identidad de carga vinculada al canal cifrado, habilitación por namespace, solo TCP | ztunnel |
| Entre clústeres (ClusterMesh) | WireGuard o IPsec (ztunnel es incompatible) |
| mTLS con conocimiento de L7, autorización y waypoints | Istio |

## Opciones TLS de mallas de servicios

| Opción | Qué proporciona | Notas |
|---|---|---|
| Sidecar de Istio | mTLS entre sidecars y política L7 de Istio | No deben aplicarse reglas HTTP a la vez con políticas L7 de Cilium e Istio; para usar L7 de Cilium en esos Pods, configura `PeerAuthentication` de Istio con mTLS en `DISABLE` |
| Istio ambient | ztunnel/HBONE 15008 y waypoint opcional | Cilium solo ve L4 cifrado en 15008; para aplicar L7 de Cilium, quita `istio.io/dataplane-mode` o anota el Pod con `ambient.istio.io/redirection: disabled` |
| ztunnel de Cilium | Solo mTLS L4 | Consulta arriba |
| TLS de Envoy en Cilium (CEC/Gateway API) | Terminación/origen TLS en Envoy | Para visibilidad de ingreso/salida, no para mTLS de malla este-oeste |

Coexistencia con Istio (upstream `network/servicemesh/istio.rst`): se recomienda `kubeProxyReplacement=false`; si el reemplazo está habilitado, configura `socketLB.hostNamespaceOnly=true` y `cni.exclusive=false`. Con sidecars en una red superpuesta, istiod necesita `hostNetwork: true`. Consulta también la [parte 5](05-l2-l7-networking.md).

**Intercepción TLS** (`terminatingTLS` / `originatingTLS` en `toPorts` de CNP): Envoy termina el TLS del cliente con un certificado de una CA interna en la que los clientes deben confiar y vuelve a iniciar TLS hacia el destino. Los Secrets se envían mediante SDS (valor predeterminado desde 1.17); `tls.secretsNamespace.name` de Helm tiene `cilium-secrets` como valor predeterminado y `tls.readSecretsOnlyFromSecretsNamespace` es `true`, así que el operador copia allí los Secrets referenciados. Esto permite aplicar políticas L7 a la salida cifrada; no sustituye el mTLS de malla.

**TLS de Gateway API**: la terminación del listener HTTPS usa un Secret; `BackendTLSPolicy` (`gateway.networking.k8s.io/v1`; `targetRefs` Service, `validation.caCertificateRefs` ConfigMap, `hostname`) cifra el tráfico de Envoy al backend. Cilium 1.20 requiere las CRD Gateway API v1.6.1; TLSRoute usa v1 y, si se usó anteriormente, requiere el canal experimental; de lo contrario, los objetos existentes desaparecen. cert-manager se integra mediante la anotación `cert-manager.io/issuer`. **Regla de exposición**: los ejemplos upstream de Gateway/Ingress crean Services de tipo `LoadBalancer`. En EKS, usa un esquema interno (`service.beta.kubernetes.io/aws-load-balancer-scheme: internal`) detrás de un origen VPC de CloudFront; nunca uses un balanceador con acceso directo a Internet. Esto no se verificó con el chart de Cilium en esta revisión. Consulta la [parte 11](11-bgp-lb-egress-edge.md).

## Hubble y Tetragon

### Componentes de Hubble

El servidor Hubble se ejecuta dentro de cada agente (gRPC en `hubble.listenAddress`, `:4244` de forma predeterminada, y socket Unix `/var/run/cilium/hubble.sock`). **Relay** (`hubble.relay.enabled`, predeterminado `false`; escucha en 4245) agrega todos los nodos en una API. La **interfaz de usuario** (`hubble.ui.enabled`, predeterminado `false`) se conecta a Relay. De forma predeterminada, el servidor y Relay usan mTLS (`hubble.tls.enabled: true`). Mantén Relay y la interfaz como ClusterIP (o balanceador interno detrás de un origen VPC de CloudFront); no los publiques.

Ruta de los eventos: eventos del plano de datos, luego el búfer circular por agente (`hubble.eventBufferCapacity`, predeterminado 4095; los valores permitidos son 2^n-1 hasta 65535) y, por último, los observadores (CLI, Relay, exportadores y métricas). `hubble.networkPolicyCorrelation.enabled` (predeterminado `true`) añade a los flujos la política que los permite o deniega.

### Métricas

`hubble.metrics.enabled` recibe una lista de manejadores (por ejemplo, `dns`, `drop`, `tcp`, `flow`, `port-distribution`, `icmp`, `httpV2`, `flows-to-world`, `policy`; `sctp` es nuevo en 1.20; el manejador no aparece en v1.19.8). Puerto del endpoint: 9965. Las métricas dinámicas (`hubble.metrics.dynamic.enabled`, ConfigMap `cilium-dynamic-metrics-config`) se reconfiguran sin reiniciar el agente. Los manejadores L7 solo generan datos para Pods con visibilidad L7. El manejador Kafka se eliminó en 1.20. `hubble.metrics.portName` es nuevo **[versión preliminar 1.21]**.

### Exportadores

- Estático: `hubble.export.static.enabled`, `filePath` (predeterminado `/var/run/cilium/hubble/events.log`; se permite `stdout`), `fileMaxSizeMb`, `fileMaxBackups`, `fileCompress`, `allowList`, `denyList` y `fieldMask`; `fieldAggregate` con `aggregationInterval` desde 1.19. Su ciclo de vida depende del agente.
- Dinámico: `hubble.export.dynamic.enabled` con entradas `config.content[]` (`name`, `filePath`, `fieldMask`, `includeFilters`, `excludeFilters`, `end` y campos de rotación) guardadas en el ConfigMap `cilium-flowlog-config`; se aplican sin reiniciar (los cambios surten efecto aproximadamente en un minuto).

### Redacción de datos (L7)

`hubble.redact.enabled` (deshabilitado de forma predeterminada), `http.urlQuery` (`false`), `http.userInfo` (`true`) y `http.headers.allow` **o** `deny` (no ambos). Ejemplo: deniega `Authorization` y `Proxy-Authorization`. La redacción de `apiKey` de Kafka se eliminó en 1.20 junto con la compatibilidad con Kafka.

```yaml
hubble:
  redact:
    enabled: true
    http:
      urlQuery: true
      userInfo: true
      headers:
        deny:
        - Authorization
        - Proxy-Authorization
```

### Eventos de descarte

`hubble.dropEventEmitter` (alfa) genera Events de Kubernetes para el tráfico descartado; `interval` es 2m; los valores predeterminados de `reasons` en 1.20.2 son `auth_required` y `policy_denied`; en 1.21 ya no se enumera `auth_required`.

### Tetragon (solo descripción general)

Tetragon es un proyecto independiente (no forma parte del repositorio de Cilium): proporciona observabilidad y aplicación de seguridad en tiempo de ejecución mediante eBPF para la ejecución de procesos y la actividad de archivos y redes, y se configura con recursos `TracingPolicy`. La documentación del modelo de amenazas de Cilium lo recomienda para visibilidad en tiempo de ejecución. En esta revisión **no se verificaron** los detalles de las versiones de sus CRD ni las acciones de aplicación; esta sección es solo una introducción. Consulta los detalles en la documentación del proyecto Tetragon.

## Administración de certificados

| Componente | Origen del certificado | Rotación |
|---|---|---|
| Servidor Hubble, Relay y métricas | `hubble.tls.auto.method`: `helm` (predeterminado), `cronJob` o `certmanager` | `helm`: solo se regenera al renderizar Helm (no hay renovación automática); `cronJob`: tarea certgen programada para `0 0 1 */4 *`; `certmanager`: cert-manager renueva; configura `certManagerIssuerRef` |
| Servidor API de ClusterMesh | los mismos tres métodos bajo `clustermesh.apiserver.tls.auto` | consulta la [parte 13](13-clustermesh-install-upgrade.md) |
| Cargas de ztunnel | CA interna o SPIRE | corta duración, en memoria |
| IPsec / WireGuard | Secret PSK / pares de claves automáticos | rotación manual de claves (IPsec); automática (WireGuard) |

Valores que conviene conocer (`values.yaml` de 1.20.2): `hubble.tls.auto.certValidityDuration` tiene 365 días como valor predeterminado y la CA autogenerada compartida (`tls.ca.certValidityDuration`) 1095 días. En otros textos, upstream indica que el certificado final tiene una validez predeterminada de tres años; prevalece el valor del chart. Los certificados del servidor y Relay, y la CA, se recargan en caliente.

Cambios en 1.20:

- Los certificados automáticos de ClusterMesh pasan a tener una validez predeterminada de 1 año (`clustermesh.apiserver.tls.auto.certValidityDuration: 365`; era 1095 en 1.19). Con el método `helm`, se renuevan solo al renderizar el chart, así que actualiza al menos una vez al año; `cronJob` y `certmanager` los renuevan automáticamente (la tarea cron de ClusterMesh los regenera cada cuatro meses).
- `certgen.enforceCAValidityThroughoutLeavesDuration` tiene `true` como valor predeterminado: certgen falla si la CA caducaría antes que un certificado final. Configura `false` para deshabilitarlo.
- Se eliminó la compatibilidad con certificados suministrados manualmente como valores de Helm: crea previamente los Secrets y configura `tls.auto.enabled=false`.
- `clustermesh.apiserver.tls.server.{extraDnsNames,extraIpAddresses}` se trasladó a `...tls.auto.server.*`.

Los certificados Hubble proporcionados por el usuario necesitan estos SAN: `*.<cluster>.hubble-grpc.cilium.io` (servidor), `*.hubble-relay.cilium.io` (Relay), `*.hubble-ui.cilium.io` y `<cluster>.hubble-metrics.cilium.io`; los Secrets contienen `tls.crt`, `tls.key` y `ca.crt`. **[Versión preliminar 1.21]** certificados por Pod: `hubble.tls.disableDefaultVolumes`, `hubble.relay.tls.disableDefaultVolumes`, `hubble.ui.tls.disableDefaultVolumes` y `extraInitContainers` permiten usar Vault, cert-manager CSI o fuentes SPIFFE; el valor predeterminado de `clustermesh.apiserver.tls.authMode` pasa a ser `cluster`.

```yaml
hubble:
  tls:
    auto:
      enabled: true
      method: certmanager
      certManagerIssuerRef:
        group: cert-manager.io
        kind: ClusterIssuer
        name: hubble-issuer
```

## Laboratorios

En esta revisión no se ejecutó ninguno de estos laboratorios en un clúster activo (consulta «Límites de validación»). Usa un clúster desechable. Las notas de grupos de seguridad presuponen reglas entre nodos que hacen referencia al propio grupo de seguridad de nodo; nunca abras un puerto a `0.0.0.0/0` o `::/0`.

### Laboratorio 1: identidades, ipcache y exclusión de etiquetas

Requisitos previos: clúster Cilium 1.20.2, kubectl y `cilium-dbg` mediante el Pod del agente.

1. Crea un namespace y dos Deployments `web` (`app=web`) y `db` (`app=db`), cada uno con 2 réplicas.
2. `kubectl get ciliumidentities`: se espera una identidad para el conjunto de etiquetas `web` y otra para `db`, compartidas por las réplicas de cada uno.
3. Ejecuta `kubectl -n kube-system exec ds/cilium -- cilium-dbg identity list` y anota los ID de `web` y `db`.
4. Elige la IP de un Pod `web` y ejecuta `cilium-dbg bpf ipcache list | grep <podIP>`: la identidad de la entrada debe coincidir con la identidad de `web`.
5. Cambia la etiqueta de un Pod `web` con `kubectl label pod <pod> release=r2 --overwrite`. Resultado esperado: aparece una identidad nueva para ese Pod y `kubectl get ciliumidentities` aumenta en uno, lo que demuestra el cambio de identidad por etiqueta.
6. Limpieza: elimina el namespace. Si cambiaste mediante Helm etiquetas relevantes para la identidad, revierte el cambio con `helm upgrade` (`--reuse-values` solo es válido si el clúster ya ejecuta esta versión del chart, 1.20.2; en caso contrario, pasa explícitamente los valores guardados) y reinicia los agentes (las identidades solo cambian después de reiniciar el agente).

### Laboratorio 2: WireGuard con ingreso estricto

Requisitos previos: nodos con WireGuard en el kernel; el grupo de seguridad de nodo permite UDP 51871 desde sí mismo.

1. Ejecuta `helm upgrade cilium cilium/cilium --version 1.20.2 -n kube-system --reuse-values --set encryption.enabled=true --set encryption.type=wireguard`; reinicia los agentes si la actualización gradual no lo hace. `--reuse-values` solo es válido si el clúster ya usa el chart 1.20.2 (la versión del chart no puede cambiar; upstream `upgrade.rst:206-221`). Si el clúster usa otra versión, guarda `helm get values cilium -n kube-system -o yaml`, revisa los valores renombrados y pásalos con `-f`.
2. `kubectl -n kube-system exec ds/cilium -- cilium-dbg status | grep Encryption`. Resultado esperado: una línea `Wireguard [cilium_wg0 (...Port: 51871, Peers: N)]` con N igual al número de nodos menos uno.
3. Genera tráfico entre Pods de nodos distintos y ejecuta `tcpdump -n -i cilium_wg0` en un Pod de agente. Resultado esperado: el flujo Pod a Pod sin cifrar se ve en `cilium_wg0`; la captura en la interfaz física para UDP 51871 solo muestra paquetes cifrados.
4. Habilita el modo estricto: `--set encryption.strictMode.egress.enabled=true --set encryption.strictMode.egress.cidr=<podCIDR> --set encryption.strictMode.ingress.enabled=true`. Configura `allowRemoteNodeIdentities=true` si se usan túneles.
5. Resultado esperado: el tráfico normal de Pods continúa; se descarta el tráfico de Pod sin cifrar que evita WireGuard (inyectar ese tráfico requiere una herramienta en el host y es opcional).
6. Reversión: primero define en `false` los valores del modo estricto, luego `encryption.enabled=false` y reinicia los agentes. Prevé descartes breves mientras se reconfigura el dispositivo (problema conocido de upstream).

### Laboratorio 3: inscripción de ztunnel

Requisitos previos: sin ClusterMesh; nodos con iptables; el grupo de seguridad de nodo permite TCP 15008 entre nodos.

1. Desde el árbol de código de Cilium de la misma etiqueta, ejecuta `bash examples/kubernetes-ztunnel/generate-secrets.sh` (crea `cilium-ztunnel-secrets` en `kube-system`).
2. Actualiza con `encryption.enabled=true` y `encryption.type=ztunnel`. Comprueba `kubectl -n kube-system get ds ztunnel-cilium` y `describe cm cilium-config | grep enable-ztunnel -A2`.
3. Crea los namespaces `mtls-on` y `mtls-off`, cada uno con un servidor HTTP y un cliente curl. Etiqueta solo `mtls-on`: `kubectl label ns mtls-on io.cilium/mtls-enabled=true`. Los Pods existentes se inscriben automáticamente; no es necesario reiniciarlos.
4. `cilium-dbg statedb dump | jq '.["mtls-enrolled-namespaces"]'` debe mostrar `mtls-on`.
5. Desde el cliente de `mtls-on` hacia un servidor de `mtls-on` en otro nodo: `tcpdump -i eth0 port 15008` en el nodo muestra paquetes HBONE.
6. Desde el cliente de `mtls-on` hacia el servidor de `mtls-off`: se espera que falle, porque no se admite el tráfico entre Pods inscritos y no inscritos.
7. Limpieza: ejecuta `kubectl label ns mtls-on io.cilium/mtls-enabled-`, elimina los namespaces, configura `encryption.enabled=false` y elimina `cilium-ztunnel-secrets`.

### Laboratorio 4: políticas en modo auditoría y CiliumCIDRGroup

1. Crea el namespace `pol` con Pods `client` y `server` (HTTP en 8080).
2. Activa el modo de auditoría para el endpoint del servidor: `cilium-dbg endpoint config <ID> PolicyAuditMode=Enabled`.
3. Aplica una CNP que permita el ingreso a `server` solo desde `app=client` en el puerto 8080. Desde un tercer Pod, ejecuta curl al servidor y ejecuta `hubble observe --verdict AUDIT -n pol`: se espera el veredicto `AUDIT` para el tercer Pod y que la solicitud siga funcionando.
4. Deshabilita el modo de auditoría con `PolicyAuditMode=Disabled` y repite la prueba: ahora se descarta la solicitud (`hubble observe --verdict DROPPED`).
5. Añade un `CiliumCIDRGroup` (el manifiesto anterior) y una regla de salida `toCIDRSet` con `cidrGroupRef`; comprueba que `cilium-dbg identity list` muestre una identidad derivada de CIDR y que los flujos incluyan el nombre del grupo.
6. Añade una regla `ingressDeny` para `app=client`; se espera que el tráfico del cliente se descarte aunque exista una regla de permiso (la denegación tiene prioridad).
7. Limpieza: elimina el namespace y el CCG.

### Laboratorio 5: exportación de Hubble, redacción y cert-manager

Requisitos previos: cert-manager y un ClusterIssuer instalados.

1. Habilita Relay y la exportación dinámica: `hubble.relay.enabled=true`, `hubble.export.dynamic.enabled=true`, `hubble.redact.enabled=true`, `hubble.redact.http.urlQuery=true` y `hubble.tls.auto.method=certmanager` con `certManagerIssuerRef`.
2. Edita el ConfigMap `cilium-flowlog-config` para añadir un exportador con una entrada `includeFilters`, por ejemplo `source_pod: ["kube-system/"]`. Resultado esperado: aparece un archivo en el directorio de exportación de Hubble dentro del Pod del agente, sin reiniciarlo (espera alrededor de un minuto).
3. Genera tráfico HTTP visible para L7 con una cadena de consulta y una cabecera `Authorization` (la visibilidad requiere una política L7 en el Pod). Resultado esperado: `hubble observe -o json` muestra los valores de consulta y cabecera redactados.
4. `kubectl get certificate -n kube-system`: ClusterIssuer emitió los certificados de Hubble.
5. Reversión: quita la entrada del exportador, configura `hubble.redact.enabled=false` y revierte el método de certificados.

## Diferencias entre versiones

| Tema | 1.18 | 1.19 | 1.20 | Versión preliminar 1.21 |
|---|---|---|---|---|
| Mutual Authentication | Beta | Beta; deshabilitada de forma predeterminada (`authentication.enabled=false`) | Obsoleta | Eliminada; el campo de política `authentication` no se usa |
| ztunnel | - | Incorporado (beta); la validación al inicio ya rechaza ClusterMesh (`pkg/ztunnel/cell.go:46`) | `ca.type` internal/spire; imagen `quay.io/cilium/ztunnel` | Beta; se reutiliza el chart SPIRE para `ca.type=spire` |
| Indicadores del modo estricto | solo `strictMode.{enabled,cidr,allowRemoteNodeIdentities}` | se añaden `strictMode.egress.*` y `strictMode.ingress.*`; indicadores antiguos obsoletos | se eliminan los indicadores antiguos (nombres `...-egress-*`) | sin cambios |
| IPsec | `encryptedOverlay` sin efecto | - | se eliminan `encryptedOverlay` e `ipsec.interface` | - |
| WireGuard `nodeEncryption` | no verificado | no verificado | beta | obsoleto; se elimina en 1.22 |
| Políticas | Kafka/proxylib obsoletos | `FromRequires` / `ToRequires` deben estar vacíos | se eliminan Kafka/proxylib; CEL rechaza CNP/CCNP vacías; ClusterNetworkPolicy | redirección mediante `toPorts[].listener` |
| Hubble | - | se añade exportación `fieldAggregate` / `aggregationInterval` | se eliminan métricas y redacción de Kafka; certificados con validez predeterminada de 1 año (ClusterMesh); comprobación de validez de CA de certgen | certificados por Pod, `portName`, `httpRoute` de UI |
| Identidad | Double Write documentado | documentado | documentado | se declara obsoleto `preflight migrate-identity` |

## Solución de problemas

| Síntoma | Causa probable | Comprobación |
|---|---|---|
| Las políticas descartan brevemente el tráfico de un Pod nuevo | Pod aún en `reserved:init` o ipcache todavía sin propagar | `cilium-dbg endpoint list`, `cilium-dbg bpf ipcache get <ip>` |
| `fromEntities: cluster` coincide (o no) con tráfico NodePort de forma inesperada | La identidad de origen es `world` o `remote-node`, según el modo de enrutamiento | Consulta la nota sobre entidades; comprueba la identidad con `hubble observe` |
| El recuento de identidades aumenta sin límite | Las etiquetas variables son relevantes para la identidad | `kubectl get ciliumidentities \| wc -l`; excluye la etiqueta |
| Se rechaza `kubectl apply` de una CNP con «spec or specs must be provided» | Regla CEL de 1.20 | Proporciona `spec` o `specs` |
| Recuento de peers WireGuard incorrecto o no existe `cilium_wg0` | Falta el módulo del kernel o UDP 51871 está bloqueado entre nodos | `cilium-dbg status \| grep Encryption`, grupo de seguridad del nodo |
| Los paquetes grandes se atascan al cifrar | MTU demasiado alta para el cifrado y el túnel | Prueba con `ping -M do`; comprueba el indicador de encadenamiento CNI |
| Aumentan los contadores de errores IPsec | Clave no coincidente o estado XFRM obsoleto | `cilium-dbg encrypt status`; la rotación de claves elimina los estados obsoletos |
| La política de host no tiene efecto con IPsec | Combinación no compatible | Usa WireGuard o elimina las políticas de host |
| Namespace inscrito, pero no hay paquetes HBONE | Los dos peers no están inscritos, el Pod usa la red del host o se usa UDP | `statedb dump`, tipo de Pod y protocolo |
| El agente no se inicia después de habilitar ztunnel | ClusterMesh está habilitado | Deshabilita uno de los dos |
| Errores de certificado de Hubble Relay después de un año | El método `helm` no renueva automáticamente | Cambia a `cronJob` o `certmanager`, o actualiza Helm cada año |
| Una política con `authentication` deja de autenticar después de 1.21 | Función eliminada | Migra según se explicó arriba |

## Límites de validación y fuentes

En esta revisión no se ejecutaron los laboratorios en un clúster activo; se contrastaron con el código fuente y la documentación upstream de las etiquetas indicadas abajo. No se verificaron los datos de Tetragon, el flujo integral de ztunnel `ca.type=spire`, los requisitos de firewall IPsec ESP/UDP ni el comportamiento durante la ejecución de los campos `authentication` restantes en políticas; estos casos se señalan en el texto. Los elementos marcados **[versión preliminar 1.21]** proceden de v1.21.0-pre.3 y pueden cambiar antes de la disponibilidad general. No se copiaron discrepancias upstream: el límite de IP por nombre FQDN (valores predeterminados distintos en documentación y código), la validez predeterminada de certificados Hubble indicada en prosa y `values.yaml`, `CiliumCIDRGroup` en documentación con `v2alpha1` aunque la versión de almacenamiento es `v2`, y el comentario de valores de `policyCIDRMatchMode`.

- [Notas de actualización 1.20](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc), [Mutual Authentication (1.20)](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/servicemesh/mutual-authentication/mutual-authentication.rst), [valores Helm](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml), [descripción general de políticas](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/kubernetes/policy.rst)
- [Cifrado transparente](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption.rst), [WireGuard](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption-wireguard.rst), [IPsec](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/security/network/encryption-ipsec.rst), [regla CEL de CNP](https://github.com/cilium/cilium/blob/v1.20.2/pkg/k8s/apis/cilium.io/v2/cnp_types.go)
- [Notas de actualización 1.21 (versión preliminar)](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc), [guía ztunnel (versión preliminar)](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/security/network/encryption-ztunnel.rst), [asignación de identidades y Double Write](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade.rst), [identidad numérica](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/pkg/identity/numericidentity.go), [capa 3 de políticas](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/security/policy/layer3.rst), [TLS de Hubble](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/observability/hubble/configuration/tls.rst), [exportación de Hubble](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/observability/hubble/configuration/export.rst)

## Cuestionario

[Comprueba tus conocimientos sobre mTLS, cifrado e identidad](../../quizzes/networking/cilium/12-mtls-encryption-identity-quiz.md).

[Volver a la página principal](README.md)
