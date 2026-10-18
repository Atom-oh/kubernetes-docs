# Parte 13: Versiones, instalación y actualización, y Cluster Mesh

> **Versión de referencia**: Cilium 1.20.2 (estable, 2026-09-16); Cilium CLI 0.20.1; Hubble CLI 1.20.2. Los elementos marcados **[versión preliminar 1.21]** provienen de v1.21.0-pre.3 y pueden cambiar antes de la versión GA.
> **Última actualización**: 15 de octubre de 2026

Este capítulo responde a tres preguntas operativas que las partes anteriores solo tratan brevemente: qué funciones incluye cada versión de Cilium y con qué nivel de madurez, cómo instalarlo y actualizarlo de forma segura (con detalles específicos de EKS), y cómo funciona Cluster Mesh desde el plano de control. Antes, el repositorio solo incluía una breve sección sobre Cluster Mesh en [IPAM y políticas de red](04-ipam-policy.md); este capítulo es la guía detallada.

Partes relacionadas: [Introducción](01-introduction.md), [Redes](03-networking.md), [IPAM](10-ipam-deep-dive.md), [BGP, balanceo de carga y egreso](11-bgp-lb-egress-edge.md), [mTLS, cifrado e identidad](12-mtls-encryption-identity.md).

## Tabla de contenido

1. Ciclo de versiones y versiones de herramientas
2. Matriz de funciones por versión (de 1.17 a la versión preliminar 1.21)
3. Cambios de 1.20.1 a 1.20.2
4. Compatibilidad y requisitos
5. Instalación con Helm (chart OCI y verificación)
6. Particularidades de la instalación en EKS
7. Procedimiento de actualización y reversión
8. Configuración del día 2: detección de desviaciones, CiliumNodeConfig y migración de identidades
9. Arquitectura de Cluster Mesh
10. Configuración de Cluster Mesh
11. Servicios globales, afinidad y sincronización de EndpointSlice
12. MCS-API (servicios multiclúster)
13. Políticas entre clústeres
14. Cluster Mesh en EKS
15. Laboratorios
16. Diferencias entre versiones, solución de problemas, límites de validación y fuentes

---

## 1. Ciclo de versiones y versiones de herramientas

Cilium publica tres artefactos con versiones independientes que se pueden confundir fácilmente.

| Artefacto | Versión vigente en esta revisión | Notas |
|---|---|---|
| Cilium (agente, operador y chart de Helm) | 1.20.2 (2026-09-16) | En el árbol v1.20.2, los campos `version` y `appVersion` del chart son ambos 1.20.2 (`install/kubernetes/cilium/Chart.yaml`) |
| Cilium CLI (`cilium`) | 0.20.1 (2026-09-24) | Los cambios de 0.20.1 son solo de dependencias/CI y actualizan la dependencia de Cilium a v1.20.2 |
| Hubble CLI (`hubble`) | 1.20.2 (2026-10-07) | La etiqueta anterior era 1.19.4; no existen etiquetas 1.20.0/1.20.1 para Hubble CLI. La versión 1.20.2 corrige la salida `compact` para eventos de veredicto de políticas con la máscara de campos predeterminada |
| Ramas de backport | 1.19.8 y 1.18.14 (ambas del 2026-09-16) | También se publicaron el mismo día que 1.20.2 |
| Versión preliminar | 1.21.0-pre.3 (2026-10-02) | Nunca se publicó `v1.21.0-pre.1`; el registro de cambios de pre.2 abarca de pre.0 a pre.2 |

Cilium CLI sigue un ciclo de versiones distinto del agente; especifica `--version` explícitamente cuando quieras una versión concreta del agente.

Historial de versiones alrededor de esta revisión:

| Versión | Fecha | Observación |
|---|---|---|
| v1.20.0 | 2026-07-29 | 2660 confirmaciones (descripción de la versión) |
| v1.20.1 | 2026-08-18 | Revisión de la documentación de Cluster Mesh; corrección del endpoint para el tratamiento de políticas CIDR tras reiniciar el agente |
| v1.20.2 | 2026-09-16 | Última versión estable; consulta la sección 3 |
| v1.21.0-pre.0 | 2026-08-03 | |
| v1.21.0-pre.2 | 2026-09-09 | |
| v1.21.0-pre.3 | 2026-10-02 | Última versión preliminar |

Considera 1.21.0-pre.x una versión preliminar: los nombres de las opciones, los valores predeterminados y las notas de actualización aún pueden cambiar.

## 2. Matriz de funciones por versión (de 1.17 a la versión preliminar 1.21)

Los términos de madurez se citan de las notas de la versión o de la documentación incluida en el árbol de la versión citada (avisos `.. include:: /beta.rst`). Un guion indica que la función aún no existe.

### 2.1 Funciones principales

| Función | 1.17 | 1.18 | 1.19 | 1.20 | 1.21 pre.3 |
|---|---|---|---|---|---|
| Kernel mínimo | 5.4 | 5.10 (4.18 en RHEL 8.10) | 5.10 | 5.10 | 5.10 (LLVM >= 21.1 para compilación nativa) |
| Versiones de Kubernetes probadas | consulta la documentación de 1.17 | hasta 1.33 (bibliotecas Go 1.33) | bibliotecas 1.35 | de 1.33 a 1.36 | de 1.34 a 1.37 |
| CRD de Gateway API | v1.2.1 | v1.3.0 | v1.4 | v1.6.1 | v1.6.1 |
| Chart OCI de Helm `quay.io/cilium/charts/cilium` | no | no | sí | sí (recomendado) | sí |
| MCS-API | beta (introducida) | beta, duplicación de EndpointSlice | beta, CRD `v1alpha1`, instalación automática de CRD | estable, `v1beta1` (se sigue admitiendo `v1alpha1`) | `v1beta1`; correcciones de nombres de EndpointSlice duplicados |
| Ámbito predeterminado de las políticas de Cluster Mesh | todos los clústeres | todos los clústeres; se introduce la marca `policy-default-local-cluster` (predeterminado: false) | solo el clúster local (predeterminado: true) | solo el clúster local; entidad `cluster-mesh` | solo el clúster local |
| `clustermesh.apiserver.tls.authMode` | `legacy` (predeterminado) | `legacy` (predeterminado) | `migration` (predeterminado) | `migration` (predeterminado) | `cluster` (nuevo `cluster-strict`) |
| KVStoreMesh | activado de forma predeterminada desde 1.16 | `kvstoremesh.enabled` obsoleto | activado de forma predeterminada | activado de forma predeterminada; valor obsoleto | siempre activado; se elimina el valor |
| Asignación de identidades Double Write | introducida (beta) | beta | beta | beta | beta; se declara obsoleto `cilium-dbg preflight migrate-identity` |
| IPAM de varios pools | beta | beta (+KVStore, IPsec y túnel) | estable | estable; migración in situ de cluster-pool a varios pools | Azure IPAM pasa a varios pools; API `CiliumPodIPPool` `cilium.io/v2` + `reservedRanges` |
| IPAM ENI IPv6 | - | - | - | beta | masquerade IPv6 desactivado de forma predeterminada en modo ENI |
| Autenticación mutua (SPIFFE/SPIRE) | existe | existe | desactivada de forma predeterminada | obsoleta | eliminada (se retiró el puerto 4250 de la tabla del firewall) |
| ztunnel | - | - | beta | beta (CA interna o SPIRE) | beta (el archivo `encryption-ztunnel.rst` del árbol 1.21 aún conserva el aviso `beta.rst`) |
| Política L7 con reconocimiento de Kafka | compatible | obsoleta | obsoleta | eliminada | eliminada |
| Extensiones Go de Envoy (proxylib) | compatibles | obsoletas | obsoletas | eliminadas | eliminadas |
| BGPv1 `CiliumBGPPeeringPolicy` | compatible | obsoleta | eliminada | - | - |
| Detección de desviaciones de ConfigMap (`configDriftDetection`) | - | retroportada a versiones de parche 1.18.x | retroportada a versiones de parche 1.19.x | integrada en 1.20.0 | igual |
| Modo de datapath | `veth` (predeterminado), `netkit` (beta), `netkit-l2`, `lb-only` | veth, netkit | BIG TCP en túneles, PLPMTUD | `bpf.datapathMode=auto` (netkit si es compatible; de lo contrario, veth; el valor predeterminado sigue siendo veth) | sin cambios |

### 2.2 Aspectos destacados de cada versión

**1.17** (2025-02, 2761 confirmaciones): anotaciones de Pod para QoS (prioridad de egreso Guaranteed/Burstable/BestEffort); introducción de MCS-API; balanceo de carga de servicios por protocolo (TCP/UDP); algoritmo de LB por servicio (maglev/random); modo de lista de denegación para `loadBalancerSourceRanges`; IP estática de AWS mediante etiquetas y pools multipool de una sola IP; MTU dinámica; selección de etiquetas `CiliumCIDRGroup`; políticas HTTP en rangos de puertos; Gateway API 1.2.1 con direcciones estáticas de Gateway; ConfigMap dinámico de métricas de Hubble; modo de asignación de identidades Double Write (migración entre KVStore y CRD).

**1.18** (3298 confirmaciones): rediseño del plano de control de LB; IPsec VXLAN sobre IPsec; varios gateways de egreso (también para rangos IPv6); límite de velocidad de ingreso de ancho de banda; red IPv6 subyacente para túneles; nombres de políticas de Hubble y campo `policy log`; se puede restringir la entidad `cluster` al clúster local; conmutación por error del apiserver mediante `k8s.apiServerURLs`; CRD de BGP, `CiliumCIDRGroup` y `CiliumLoadBalancerIPPool` pasan a ser estables en `cilium.io/v2`; delegación de prefijos de AWS en modo ENI; Gateway API 1.3.0 y `CiliumGatewayClassConfig`; el kernel mínimo sube a 5.10. Cambios de comportamiento: en modo ENI, el valor predeterminado de `enableIPv4Masquerade` cambia de true a false (usa `upgradeCompatibility` con valor inferior a 1.18 o configúralo explícitamente); el operador necesita `ec2:DescribeRouteTables` en modo ENI; `io.cilium.k8s.policy.serviceaccount` se añade a las etiquetas de identidad predeterminadas y provoca una rotación temporal de identidades durante la actualización.

**1.19** (2934 confirmaciones): se activa el ámbito local del clúster como valor predeterminado de las políticas; la autenticación mutua se desactiva de forma predeterminada; IPAM de varios pools pasa a estable; charts OCI de Helm; ztunnel en beta; modos de cifrado estrictos para IPsec y WireGuard; campos de política de Kafka obsoletos y se eliminan `FromRequires/ToRequires`; se elimina BGPv1; instalación automática de CRD de MCS-API (`clustermesh.mcsapi.installCRDs`); se modifica la generación de certificados para que CronJob deje de ser un hook de Helm (compatible con Argo CD y `--wait`); Gateway API 1.4; GRPCRoute de GAMMA.

**1.20** (2026-07-29): Gateway API 1.6.1 (ListenerSet, BackendTLSPolicy, TCPRoute/UDPRoute, ExternalAuth, CORS); complementos de datapath; `bpf.datapathMode=auto`; IP de egreso IPv6 para Egress Gateway; BGP mediante `cilium-dbg shell -- bgp/*` y GoBGP 4.6.1; ENI IPv6 (beta); migración in situ de cluster-pool a varios pools; distribución de tráfico `PreferSameZone`/`PreferSameNode`; pesos de Maglev mediante `service.cilium.io/weight` (0 drena); MCS-API estable; entidad de política `cluster-mesh`; niveles admin/baseline de Kubernetes ClusterNetworkPolicy; detección de desviaciones de ConfigMap; el binario `cilium-cni` se reduce de 77 MB a 16 MB; K8s 1.36, Envoy 1.37.x. **Eliminado en 1.20**: extensiones Go de Envoy (proxylib), política L7 con reconocimiento de Kafka, `CiliumNodeConfig` `v2alpha1`, `clustermesh.enableMCSAPISupport` (usa `clustermesh.mcsapi.enabled`), certificados de Cluster Mesh como valores, `cilium-docker-plugin`, las marcas antiguas `encryption.strictMode.*` (ahora `encryption.strictMode.egress.*`), `--node-port-algorithm`/`--node-port-mode`, `--ces-slice-mode`, `encryption.ipsec.interface`. **Cambios de comportamiento**: `bpf.tproxy=true` no es compatible con netkit; ahora el acceso a NodePort dentro del clúster desde Pods sin SocketLB (o con `socketLB.hostNamespaceOnly=true`) se balancea en el Pod cliente, por lo que las políticas de egreso del cliente y de ingreso del backend deben permitirlo; se rechazan en admisión los `CiliumNetworkPolicy`/`CiliumClusterwideNetworkPolicy` vacíos (sin `spec`/`specs`); los certificados autogenerados de Cluster Mesh tienen una validez predeterminada de un año y CronJob los regenera cada cuatro meses; certgen exige que la validez de la CA sea >= a la de los certificados leaf (`certgen.enforceCAValidityThroughoutLeavesDuration=false` desactiva la comprobación).

**Versión preliminar 1.21** (v1.21.0-pre.3): xDS delta (`envoy.xdsMode=delta-split`); Cilium Network Driver (DRA, SR-IOV); persistencia de sesión de Gateway API; listas de prefijos administradas por AWS en políticas; KVStoreMesh activado incondicionalmente; valor predeterminado de Cluster Mesh `authMode=cluster`; se elimina la autenticación mutua; `encryption.nodeEncryption` (WireGuard) se declara obsoleto y se prevé eliminarlo en 1.22; se elimina la marca del operador `--aws-use-primary-address` (usa `eni.nodeSpec.usePrimaryAddress`); las anotaciones `cec.cilium.io/*` de metadatos de infraestructura de Gateway/GAMMA ya no se propagan a los `CiliumEnvoyConfig` generados; el operador migra automáticamente la versión de almacenamiento de objetos obsoletos; bibliotecas de Kubernetes 1.37. La nota de pre.2 «Enable BPF masquerading by default» no se refleja en el árbol pre.3 (consulta Límites de validación).

## 3. Cambios de 1.20.1 a 1.20.2

`gh api repos/cilium/cilium/compare/v1.20.1...v1.20.2` informa de 204 confirmaciones (la API trunca la lista de archivos a 300, por lo que el recuento de archivos modificados no es fiable). No se revisó la lista de confirmaciones en busca de cambios de funciones; consulta las notas de la versión antes de suponer que la actualización es de bajo riesgo. Varias correcciones son importantes para configuraciones específicas.

| Área | Corrección |
|---|---|
| IPAM ENI de AWS | El operador liberaba IP delegadas por prefijo como IP individuales aunque siguieran en uso; la asignación fallaba cuando una subred se quedaba sin prefijos; el agente se bloqueaba al iniciar en modo ENI si `ipv4NativeRoutingCIDR` era un CIDR secundario de la VPC; correcciones de enrutamiento ENI IPv6 (endpoint de estado, ingreso, IPsec); se restauraron las reglas de enrutamiento de endpoints ENI después de cambiar la configuración de masquerade; se redujo la carga de EC2 IMDS |
| Cluster Mesh | Una condición de carrera poco frecuente dejaba conectado un clúster remoto ya eliminado; se reforzó la validación de backends de servicios ingeridos desde Cluster Mesh; la gestión de usuarios etcd de clustermesh-apiserver no revocaba roles obsoletos al cambiar la configuración (no afecta a los usuarios del chart de Helm) |
| Actualización | Los clústeres creados con Cilium 1.15 o anterior no podían actualizarse porque se eliminó la versión CRD `CiliumNodeConfig` `v2alpha1`. Usa 1.20.2 o posterior al actualizar esos clústeres a 1.20 |
| Opciones ignoradas | Ahora funcionan cinco opciones que se aceptaban pero se ignoraban silenciosamente: `vtep-sync-interval`, `enable-xt-socket-fallback`, `eni-delete-on-termination` con una configuración CNI personalizada, Helm `enableIdentityMark` fuera del modo chaining y `lb-retry-backoff-max`; también se corrigieron cuatro ajustes de Hubble que no llegaban a su destino |
| Datapath | Correcciones para datagramas UDP fragmentados clasificados erróneamente como WireGuard, suma de comprobación de errores ICMP en tráfico LB SNAT, recuperación DSR y origen de ICMP PMTU, anuncios L2 con `externalTrafficPolicy: Local`, regresiones de LocalRedirectPolicy y métricas de denegación de egreso `policy-deny-response: icmp` |
| Política | Un Pod creado justo después de cambiar una NetworkPolicy podía mostrar una revisión obsoleta hasta dos minutos; bloqueo por mapas de políticas concurrentes con puertos con nombre; las identidades persistían el doble de lo esperado |
| Gateway API | ExternalAuth de `HTTPRoute` ahora falla de forma cerrada si `backendRef` no es válido; la documentación indica que Gateway API necesita módulos iptables y netfilter TPROXY cuando `bpf.tproxy` es false (valor predeterminado) |
| BGP | La autodetección del peer `defaultGateway` elegía la tabla de enrutamiento incorrecta |

Actualizaciones de imágenes y del chart en 1.20.2: certgen de v0.4.9 a v0.4.11; Envoy de v1.37.5 a v1.37.6; hubble-ui de v0.13.5 a v0.13.6; SPIRE de 1.15.2 a 1.15.3. El diff de `values.yaml` solo contiene etiquetas de imágenes y una anotación de esquema; ahora la clave ConfigMap `enable-identity-mark` solo se representa cuando se configura `enableIdentityMark`.

Cambios en la documentación de 1.20.2: se eliminaron dos entradas de la lista de configuración obligatoria del kernel en `system_requirements.rst` (`CONFIG_CRYPTO_USER_API_HASH` y `CONFIG_INET_XFRM_MODE_TUNNEL`), y la introducción de Cluster Mesh añadió una sección «Seguridad»: todos los clústeres de una malla forman un único dominio de confianza; conecta únicamente clústeres con confianza mutua y posturas de seguridad equivalentes.

Recomendación: usa `--version 1.20.2` para usuarios de ENI, implementaciones de Cluster Mesh y cualquier clúster creado con Cilium 1.15 o anterior.

## 4. Compatibilidad y requisitos

### 4.1 Compatibilidad de versiones

| Elemento | 1.20.2 | 1.21.0-pre.3 |
|---|---|---|
| Kubernetes (probadas) | 1.33, 1.34, 1.35, 1.36 | 1.34, 1.35, 1.36, 1.37 |
| Kernel de Linux | >= 5.10 (RHEL 8.10: 4.18) | >= 5.10 |
| clang/LLVM (solo compilación nativa del agente) | >= 18.1 | >= 21.1 |
| CRD de Gateway API | se requiere v1.6.1 | v1.6.1 |
| `kubeVersion` del chart de Helm | `>= 1.21.0-0` (restricción del chart, no rango probado) | igual |
| Cilium CLI | 0.20.1 | n/a |
| Hubble CLI | 1.20.2 | n/a |

Requisitos mínimos de kernel específicos por función, según los requisitos del sistema de 1.20.2: multidifusión en AMD64 >= 5.10 y en AArch64 >= 6.0; IPv6 BIG TCP >= 5.19; IPv4 BIG TCP >= 6.3; netkit >= 6.8 con `CONFIG_NETKIT=y`. Una nota de 1.19: la combinación de IPsec, reemplazo de kube-proxy y masquerade BPF activa automáticamente el enrutamiento de host BPF, que requiere la corrección del kernel para CVE-2025-37959.

Cluster Mesh añade otra restricción: las versiones de Cilium de todos los clústeres conectados no pueden diferir en más de una versión menor (por ejemplo, 1.19.x puede unirse a 1.18.x y 1.20.x, pero no a 1.17.x).

### 4.2 Puertos

Abre estos puertos entre nodos usando solo referencias a grupos de seguridad o CIDR privados (nunca `0.0.0.0/0`):

| Puerto | Propósito |
|---|---|
| UDP 8472 | Túnel VXLAN |
| UDP 6081 | Túnel Geneve |
| TCP 4240 más ICMP tipo 8/0 | Comprobaciones de estado |
| TCP 4244 | Servidor Hubble |
| TCP 4245 | Hubble Relay |
| UDP 51871 | WireGuard |
| ESP (protocolo IP 50) | IPsec (los grupos de seguridad de AWS bloquean ESP salvo que una regla lo permita) |
| TCP 4250 | Autenticación mutua (aparece en la documentación de 1.20; se eliminó de la documentación de 1.21) |
| TCP 2379 | clustermesh-apiserver entre clústeres |

### 4.3 CRD de Gateway API

Cilium 1.20 requiere CRD de Gateway API v1.6.1 (`gateway_api_version = 'v1.6.1'` en `Documentation/conf.py`, `sigs.k8s.io/gateway-api v1.6.1` en `go.mod`). El chart de Helm no las instala. CRD requeridas: GatewayClass, Gateway, HTTPRoute, GRPCRoute, ReferenceGrant, BackendTLSPolicy y TLSRoute. Opcionales (la función permanece desactivada si faltan): TCPRoute, UDPRoute y ListenerSet. Requisitos previos: `kubeProxyReplacement=true`, `l7Proxy=true` e iptables más módulos TPROXY, salvo que `bpf.tproxy=true` (beta). Aplica con `kubectl apply --server-side`.

Precaución con TLSRoute: si ya usas TLSRoute, instala TLSRoute v1.6.1 del canal experimental, que aún utiliza `v1alpha2`. Instalar TLSRoute v1.6 del canal estándar hará que los objetos TLSRoute existentes dejen de poder leerse (en la práctica, desaparecerán). Primero haz una copia de seguridad de los objetos (`kubectl get tlsroutes -A -o yaml`).

## 5. Instalación con Helm

El chart de Helm está disponible en dos ubicaciones:

| Ubicación | Estado |
|---|---|
| `oci://quay.io/cilium/charts/cilium` | Se recomienda en la documentación desde 1.19; los charts tienen firma cosign y se pueden fijar por digest |
| `https://helm.cilium.io/` (`helm repo add cilium`) | Repositorio clásico, totalmente compatible |

Las versiones del chart no llevan prefijo `v` (`--version 1.20.2`); las etiquetas de imágenes sí. Los registros OCI no admiten `helm search`; consulta las versiones con `crane ls quay.io/cilium/charts/cilium`. Verifica la firma del chart:

```bash
cosign verify \
  --certificate-identity-regexp='https://github.com/cilium/cilium/.*' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  quay.io/cilium/charts/cilium:1.20.2
```

Guarda los valores en un archivo bajo control de versiones e instala con `-f values.yaml`; no dependas de una colección de marcas `--set`, porque en cada actualización de versión menor debes volver a proporcionar los valores, como se indica en la sección 7.

## 6. Particularidades de la instalación en EKS

### 6.1 Modos disponibles

| Modo | Helm | Datapath / IPAM | Notas |
|---|---|---|---|
| ENI (predeterminado upstream para EKS) | `eni.enabled=true` | Enrutamiento nativo (el chart establece `routingMode` en nativo al activar `eni.enabled`), IPAM ENI de AWS, almacén de datos CRD de Kubernetes | Los Pods reciben IP enrutables desde la VPC; el operador necesita privilegios para la API EC2; `aws-node` no debe ejecutarse en los nodos de Cilium |
| Overlay | omite `eni.enabled` (el valor predeterminado del chart es túnel/VXLAN) | VXLAN, IPAM cluster-pool | Más Pods por nodo que el límite de ENI; el tráfico Pod-a-VPC usa SNAT a la IP del nodo; el servidor de API de EKS no puede enrutar a las IP de Pods del overlay, por lo que los webhooks deben usar la red del host o alcanzarse mediante un Service/ingress; vacía las cadenas iptables `AWS-SNAT-CHAIN-0/1` y `AWS-CONNMARK-CHAIN-0/1` que deja VPC CNI |
| Chaining sobre VPC CNI | `cni.chainingMode=aws-cni`, `cni.exclusive=false`, `enableIPv4Masquerade=false`, `routingMode=native` | VPC CNI gestiona las redes; Cilium añade políticas y visibilidad | Requiere VPC CNI >= 1.11.2; reinicia los Pods existentes después de habilitarlo. Las limitaciones de chaining aparecen en upstream (`cni-chaining-limitations.rst`); léelas antes de elegir este modo |
| EKS Hybrid Nodes | chart compilado por AWS `oci://public.ecr.aws/eks/cilium/cilium` | Overlay VXLAN, cluster-pool | Consulta 6.4 |
| EKS Auto Mode | no compatible | n/a | Consulta 6.5 |

### 6.2 Instalación en modo ENI

Cilium administra las ENI, así que evita que VPC CNI se ejecute en los nodos administrados por Cilium. Aplica un selector de nodos a DaemonSet `aws-node` que ningún nodo tenga (comando upstream, literal):

```bash
kubectl -n kube-system patch daemonset aws-node --type='strategic' \
  -p='{"spec":{"template":{"spec":{"nodeSelector":{"io.cilium/aws-node-enabled":"true"}}}}}'
```

Aplica un taint a los grupos de nodos administrados para que los Pods de aplicaciones esperen a Cilium (recomendación upstream):

```yaml
# eksctl ClusterConfig fragment
managedNodeGroups:
- name: ng-1
  taints:
  - key: "node.cilium.io/agent-not-ready"
    value: "true"
    effect: "NoExecute"
```

Archivo de valores (todas las claves existen en el chart 1.20.2; `eni.enabled=true` define la imagen del operador, las rutas de endpoints, la gestión de CiliumNode y los valores predeterminados de IPv4 masquerade; la validación del chart falla si se establece `ipam.mode=eni` sin `eni.enabled=true`):

```yaml
# values-eks-eni.yaml  (Cilium 1.20.2)
eni:
  enabled: true
kubeProxyReplacement: true
k8sServiceHost: <EKS-API-ENDPOINT-FQDN-without-scheme>
k8sServicePort: 443
cluster:
  name: eks-a
  id: 1   # keep below 128 in ENI mode (see the cluster.id note in the Helm reference)
```

```bash
helm install cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system -f values-eks-eni.yaml
```

Notas:

- Al reemplazar kube-proxy, debes definir `k8sServiceHost` y `k8sServicePort` antes de quitar kube-proxy; de lo contrario, el agente no podrá acceder al servidor de API.
- El operador necesita privilegios de EC2 (consulta la sección upstream `ec2privileges`) y, desde 1.18, `ec2:DescribeRouteTables`.
- En 1.18, el valor predeterminado de `enableIPv4Masquerade` en modo ENI cambió a false. Si actualizas un clúster ENI anterior a 1.18 y dependes de masquerade, establécelo explícitamente o usa `upgradeCompatibility`.
- IPv6 ENI es beta en 1.20 (`eni.rst`). Una página upstream (`requirements-eks.rst`) aún dice que ENI solo admite IPv4; sigue las notas de versión y `eni.rst`.
- Usa 1.20.2 con ENI: corrige la liberación de prefijos delegados, la asignación al agotar prefijos de una subred y el bloqueo de enrutamiento nativo con un CIDR secundario de VPC.
- Las IP de Pod proceden del pool `default`; en modo ENI no se usan `CiliumPodIPPool` ni la anotación `ipam.cilium.io/ip-pool` (`eni.rst`). Consulta [IPAM](10-ipam-deep-dive.md).

### 6.3 Imágenes de máquina

Los requisitos del sistema de 1.20.2 indican que Amazon Linux 2 y Bottlerocket son compatibles (todas las versiones), Ubuntu >= 20.04, RHEL >= 8.6, Talos >= 1.5.0 y Flatcar (con una salvedad de DHCP para ENI). Amazon Linux 2023 no se menciona por nombre; su kernel es más reciente que el mínimo 5.10, pero esto es una inferencia, no una afirmación upstream. La documentación de AWS sobre Hybrid Nodes señala que Ubuntu 20.04 y RHEL 8 no cumplen el requisito de kernel para Cilium 1.18.3.

### 6.4 EKS Hybrid Nodes

AWS admite Cilium en nodos híbridos únicamente mediante la compilación mantenida por AWS del repositorio público ECR `oci://public.ecr.aws/eks/cilium/cilium` (en la documentación de AWS aparecen versiones como `1.17.9-0` y `1.18.3-0`; esta revisión no verificó la lista de compilaciones AWS más recientes). VPC CNI no es compatible con nodos híbridos. La configuración predeterminada de AWS es un overlay VXLAN con IPAM cluster-pool; el CIDR del pool debe coincidir con la red remota de Pods de EKS, no debe solaparse con los CIDR de nodos, VPC o Service y no debe cambiarse después de la implementación. Fija el agente y el operador a nodos híbridos mediante la afinidad `eks.amazonaws.com/compute-type In hybrid`, y usa BGP Control Plane para enrutar los CIDR de Pods. La tabla de compatibilidad de AWS indica que Cilium Ingress y Cilium Gateway son compatibles con nodos híbridos (configuraciones predeterminadas; consulta las páginas de AWS sobre [CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html) e [Ingress](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-ingress.html)). `envoy.enabled: false` solo aparece en los valores de ejemplo de referencia de AWS; como Cilium Ingress/Gateway y las políticas de red L7 necesitan Envoy, actívalo si los utilizas, siguiendo la página de ingress de AWS. En esa configuración, Cilium no es compatible con nodos de la nube de AWS.

### 6.5 EKS Auto Mode

EKS Auto Mode no funciona con Cilium. AWS documenta que Auto Mode no admite complementos CNI alternativos ni complementos de políticas de red (guía del usuario de EKS, páginas «alternate CNI plugins» y «auto networking»), y la documentación upstream de Cilium no tiene una página sobre Auto Mode. Para Cilium, usa un grupo de nodos administrado estándar o nodos autoadministrados.

### 6.6 Regla de exposición de este repositorio

Nada en este capítulo requiere un listener público. Si los clientes fuera de la VPC necesitan acceder a una aplicación, usa CloudFront con un origen VPC hacia un ALB/NLB interno. El Service de clustermesh-apiserver también debe ser interno (sección 14).

## 7. Procedimiento de actualización y reversión

### 7.1 Reglas

1. Solo se han probado actualizaciones y reversiones entre versiones menores consecutivas (de 1.19 a 1.20 y viceversa). No omitas ninguna versión menor.
2. Primero actualiza a la versión de parche más reciente de tu versión menor actual, para disponer de un destino de reversión con todas las correcciones.
3. Actualiza todos los componentes (agente, operador, Hubble Relay y clustermesh-apiserver) a la misma versión; no actualices únicamente el agente.
4. El tráfico L3/L4 sufre poco o ningún impacto; las conexiones que pasan por proxies de espacio de usuario (políticas L7, Ingress, Gateway API, Envoy) se interrumpen y los clientes deben reconectarse. Las reglas de políticas nuevas quedan pendientes en cada nodo hasta que vuelva a estar activo su agente.
5. Nunca uses `helm upgrade --reuse-values` al pasar entre versiones menores: omite los nuevos valores predeterminados del chart y puede generar manifiestos no válidos. `--reuse-values` solo se acepta si no cambia la versión del chart (por ejemplo, durante la actualización de la configuración de Cluster Mesh más adelante en este capítulo).
6. Establece `upgradeCompatibility` en la versión menor en la que instalaste originalmente (no en la versión desde la que actualizas). Esto fija los valores predeterminados antiguos en el ConfigMap generado; por ejemplo, restablece el valor de masquerade ENI anterior a 1.18.
7. Para clústeres creados con 1.15 o anterior, actualiza a 1.20.2 o posterior, no a 1.20.0/1.20.1.

### 7.2 Procedimiento

```bash
# 0. Save and review current values for renamed/removed keys
helm get values cilium -n kube-system -o yaml > old-values.yaml

# 1. Pre-flight: pre-pulls the new image on every node and validates existing CNPs
helm install cilium-preflight oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system \
  --set preflight.enabled=true --set agent=false --set operator.enabled=false
#   (add k8sServiceHost/k8sServicePort when kube-proxy replacement is on)
kubectl -n kube-system get ds cilium-pre-flight-check   # READY must equal the node count
kubectl -n kube-system get deploy cilium-pre-flight-check   # must be 1/1
kubectl -n kube-system logs deployment/cilium-pre-flight-check -c cnp-validator --previous
helm delete cilium-preflight -n kube-system

# 2. Upgrade (NO --reuse-values); 1.19 is the minor you installed originally in this example
helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 \
  -n kube-system -f old-values.yaml --set upgradeCompatibility=1.19

# 3. Watch
kubectl -n kube-system rollout status ds/cilium
kubectl -n kube-system rollout status deploy/cilium-operator
cilium status --wait
```

Una implementación de preflight que se queda en `READY 0/1` indica que al menos una CiliumNetworkPolicy existente no supera la validación en la versión nueva; corrige la política antes de actualizar.

### 7.3 Reversión

```bash
helm history cilium -n kube-system
helm rollback cilium <REVISION> -n kube-system
# or, for the DaemonSet only:
kubectl -n kube-system rollout undo daemonset/cilium
```

Si ya utilizaste funciones de la nueva versión menor (CR nuevas, opciones activadas en ConfigMap), consulta las notas de actualización de esa versión antes de revertir. La reversión restaura los manifiestos anteriores, pero no los objetos creados por la nueva versión.

### 7.4 Gestión de CRD

| Familia de CRD | Quién la instala/actualiza | Acción |
|---|---|---|
| CRD de Cilium (`cilium.io`) | El operador/agente las registra y actualiza al arrancar | Ninguna, pero verifica `kubectl get crd \| grep cilium.io` después de actualizar. En 1.20 se eliminó `CiliumNodeConfig` `v2alpha1`; usa `cilium.io/v2` |
| Gateway API | Tú (manual, `kubectl apply --server-side`) | Usa la versión de la sección 4.3; primero haz una copia de TLSRoute |
| MCS-API (`multicluster.x-k8s.io`) | El chart cuando `clustermesh.mcsapi.enabled=true`, salvo que `clustermesh.mcsapi.installCRDs=false` (desde 1.19) | Establece `installCRDs=false` si otro controlador administra las CRD |
| Versiones obsoletas almacenadas | **[versión preliminar 1.21]** el operador migra automáticamente las versiones de almacenamiento | `CiliumPodIPPool` `v2` pasa a ser la versión de almacenamiento |

### 7.5 Acciones que debes comprobar en cada actualización de versión menor

Consulta siempre las «Upgrade Notes» de la versión menor de destino. Entre los cambios anteriores que suelen causar problemas: valor predeterminado de masquerade ENI y `ec2:DescribeRouteTables` (1.18); rotación de etiquetas de identidad al añadirse la etiqueta de cuenta de servicio (1.18); `policy-default-local-cluster` cambia a true (1.19, consulta la sección 13); la autenticación mutua se desactiva de forma predeterminada (1.19); se eliminan opciones y Kafka/proxylib (1.20); `bpf.tproxy` con netkit y balanceo NodePort en el cliente (1.20); `authMode=cluster` como valor predeterminado y eliminación del valor `kvstoremesh.enabled` (versión preliminar 1.21).

## 8. Configuración del día 2

### 8.1 Detección de desviaciones de ConfigMap

Muchas opciones solo surten efecto después de reiniciar el agente. Tras editar el ConfigMap `cilium-config` (mediante `helm upgrade` o `cilium config set`), el agente en ejecución puede diferir del ConfigMap. La detección de desviaciones permite observarlo. Está integrada en 1.20.0 y se retroportó a las versiones de parche 1.18.x y 1.19.x (está presente en los charts v1.18.14 y v1.19.8, pero no en v1.18.0 ni v1.19.0).

```yaml
configDriftDetection:
  enabled: true        # enable-dynamic-config: watch the ConfigMap
  driftChecker: true   # enable-drift-checker: compare desired vs active
  ignoredKeys: []      # for example ["devices"] for keys that are intentionally different
```

El agente registra una advertencia por cada clave que no coincide y expone la métrica gauge `cilium_drift_checker_config_delta`. `0` significa que están sincronizados; un valor superior a 0 indica que el agente no ha aplicado el ConfigMap actual y necesita reiniciarse. Genera una alerta si `cilium_drift_checker_config_delta > 0` durante más tiempo que tu ventana de despliegue.

`cilium config set <key> <value>` edita el ConfigMap y reinicia los agentes de forma predeterminada; pasa `--restart=false` para aplazar el reinicio y permitir que la métrica gauge muestre el cambio pendiente.

### 8.2 CiliumNodeConfig (anulaciones por nodo)

`CiliumNodeConfig` (`apiVersion: cilium.io/v2`, espacio de nombres `kube-system`) anula claves del ConfigMap/agente en los nodos que coinciden con `spec.nodeSelector` (el selector vacío `{}` coincide con todos). Los cambios se aplican solo al recrear el Pod del agente o reiniciar el nodo. `v2alpha1` se eliminó en 1.20.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNodeConfig
metadata:
  namespace: kube-system
  name: enable-xdp
spec:
  nodeSelector:
    matchLabels:
      io.cilium.xdp-offload: "true"
  defaults:
    bpf-lb-acceleration: native
```

Usos habituales: habilitar XDP o IPv6 BIG TCP solo en nodos con hardware adecuado, y desplegar gradualmente el reemplazo de kube-proxy (etiqueta los nodos migrados con `io.cilium.migration/kube-proxy-replacement=true`, aplica al DaemonSet de kube-proxy una afinidad `NotIn` para esa etiqueta, establece `kube-proxy-replacement: "true"` en CiliumNodeConfig y elimina el Pod del agente nodo por nodo). `k8sServiceHost` y `k8sServicePort` deben estar definidos antes de retirar kube-proxy.

### 8.3 Migración de identidades de KVStore a CRD («Double Write», beta)

Se introdujo en 1.17 y sigue marcada como beta en 1.20.2 y 1.21 pre.3. El modo de asignación es la opción del agente `--identity-allocation-mode`, que se configura mediante el valor de Helm `identityAllocationMode` (que genera la clave `identity-allocation-mode` del ConfigMap en el chart).

| Paso | Modo | Orden de despliegue | Fuente de verdad |
|---|---|---|---|
| 0 | `kvstore` | | KVStore |
| 1 | `doublewrite-readkvstore` | operador y luego agentes | KVStore (las identidades también se escriben como CRD, pero no se usan) |
| 2 | `doublewrite-readcrd` | operador y luego agentes | CRD (se siguen escribiendo en KVStore para permitir una reversión rápida) |
| 3 | `crd` | agentes y luego operador | solo CRD; se puede retirar KVStore |

Espera a que converja cada etapa antes de continuar. El operador expone métricas gauge en el espacio de nombres `cilium_operator`. La página upstream de actualización aún muestra los nombres antiguos `cilium_operator_identity_*_count`, pero el código de v1.20.2 en `operator/doublewrite/metrics.go` registra `doublewrite_crd_identities`, `doublewrite_kvstore_identities`, `doublewrite_crd_only_identities` y `doublewrite_kvstore_only_identities`, que aparecen como `cilium_operator_doublewrite_*`. Consulta `curl` en el puerto de métricas del operador para conocer los nombres exactos de tu versión. Las diferencias transitorias son normales porque la recolección de elementos no utilizados de KVStore y CRD se ejecuta en momentos distintos (`--identity-gc-interval`, `--identity-heartbeat-timeout`). Para revertir la migración (de CRD a KVStore), repite los pasos en orden inverso. Recuperación desde cero: sin ningún agente ejecutándose en modo `crd`, ejecuta `kubectl delete ciliumid --all`.

La herramienta de ejecución única `cilium-dbg preflight migrate-identity` está documentada en 1.20.2 con limitaciones (no admite rotación de identidades y no ofrece una reversión sencilla) y se declara obsoleta en la versión preliminar 1.21; usa Double Write.

## 9. Arquitectura de Cluster Mesh

Cluster Mesh conecta los planos de control de varios clústeres de Kubernetes para compartir identidades, endpoints, nodos y servicios, mientras que el tráfico de los Pods fluye directamente entre nodos sin gateway ni proxy.

```
 Cluster 1                                         Cluster 2
 ┌──────────────────────────────┐                  ┌──────────────────────────────┐
 │ clustermesh-apiserver (Deploy)│                 │ clustermesh-apiserver (Deploy)│
 │  ┌────────┐ ┌──────────────┐ │  mTLS etcd 2379  │  ┌────────┐ ┌──────────────┐ │
 │  │ etcd   │◄┤ apiserver    │ │◄────────────────►│  │ etcd   │◄┤ apiserver    │ │
 │  │(local  │ │ (sync local  │ │  (via internal LB│  │        │ │              │ │
 │  │ state) │ │  state -> etcd)│ │   / NodePort)   │  │        │ │              │ │
 │  └───▲────┘ └──────────────┘ │                  │  └───▲────┘ └──────────────┘ │
 │      │      ┌──────────────┐ │                  │      │      ┌──────────────┐ │
 │      └──────┤ kvstoremesh  │─┼─ pulls remote ──►│      └──────┤ kvstoremesh  │ │
 │             └──────▲───────┘ │   cluster state  │             └──────▲───────┘ │
 │   agents read ONLY │ local   │                  │   agents read ONLY │ local   │
 │   ┌────────────────┴─┐       │                  │   ┌────────────────┴─┐       │
 │   │ cilium-agent (DS)│       │                  │   │ cilium-agent (DS)│       │
 │   └─────────┬────────┘       │                  │   └─────────┬────────┘       │
 └─────────────┼────────────────┘                  └─────────────┼────────────────┘
               └──────── Pod -> Pod, node to node (VXLAN/Geneve or native) ───────┘
```

Componentes (v1.20.2 `intro.rst`, `values.yaml`):

- **clustermesh-apiserver** es un Deployment con tres contenedores. `etcd` es una instancia integrada única, sin almacenamiento persistente; al iniciarse, reconstruye su estado desde el servidor de API de Kubernetes y se expone mediante mTLS. `apiserver` sincroniza el estado local de Cilium y Kubernetes (nodos, endpoints, identidades y servicios) en ese etcd (`etcdQPS: 50`). `kvstoremesh` obtiene el estado de cada clúster remoto y lo guarda en la caché etcd local (`etcdQPS: 100`).
- **KVStoreMesh**: los agentes leen el estado remoto únicamente desde la caché local; así, cada agente evita abrir conexiones a todos los etcd remotos. Es el valor predeterminado desde 1.16; el valor `clustermesh.apiserver.kvstoremesh.enabled` se declaró obsoleto en 1.18 y en **[versión preliminar 1.21]** se habilita incondicionalmente y se elimina el valor.
- **Réplicas**: `clustermesh.apiserver.replicas` tiene el valor predeterminado 1. Cada réplica ejecuta su propio clúster etcd; los clientes remotos eligen una mediante el Service. `service.enableSessionAffinity` (predeterminado `HAOnly`, también admite `Always` y `Never`) reduce las resincronizaciones completas tras una reconexión. `podDisruptionBudget` está desactivado de forma predeterminada.
- **Modo KVStore**: si Cilium ya usa un etcd externo como almacén de estado/identidades, Cluster Mesh puede reutilizarlo (`clustermesh.apiserver.kvstoremesh.kvstoreMode: external`); `external` no se puede combinar con el modo de asignación de identidades `crd`.
- **Dominio de confianza único** (v1.20.2 `intro.rst`): un clúster comprometido puede envenenar a los demás; conecta únicamente clústeres con confianza mutua y posturas de seguridad equivalentes.

### 9.1 Ruta de datos

Los Pods remotos aparecen en el ipcache local con el nodo remoto como endpoint del túnel (overlay), o se enrutan por la red subyacente (enrutamiento nativo). Como las identidades incluyen el ID de clúster, una decisión de política en el clúster 1 para el tráfico de un Pod del clúster 2 usa la identidad numérica del Pod remoto y funciona sin gateway. Por eso son obligatorios los CIDR de Pods sin solapamientos y la conectividad entre las IP de los nodos.

## 10. Configuración de Cluster Mesh

### 10.1 Requisitos previos

| Requisito | Detalle |
|---|---|
| Mismo modo de datapath | Todos los clústeres usan overlay o todos usan enrutamiento nativo |
| Diferencia entre versiones menores de Cilium | Como máximo una versión menor |
| CIDR de Pods únicos y sin solapamientos | Entre todos los nodos de todos los clústeres |
| Conectividad entre nodos | Mediante la InternalIP de cada nodo (peering, TGW o VPN) |
| Firewall | TCP 2379 (clustermesh-apiserver), TCP 4240 e ICMP (estado), UDP 8472/6081 (túnel), UDP 51871 (WireGuard) |
| Solo para enrutamiento nativo | `ipv4NativeRoutingCIDR` debe incluir los CIDR de Pods de todos los clústeres (por ejemplo, `10.0.0.0/8`), y los Pods deben poder enrutarse entre clústeres en todos los puertos |

### 10.2 Nombre e ID del clúster

| Ajuste | Regla |
|---|---|
| `cluster.name` | Máximo 32 caracteres; expresión regular `^([a-z0-9][-a-z0-9]*)?[a-z0-9]$` (`pkg/clustermesh/types/types.go`); debe ser único por clúster. No se puede usar `default` si el ID no es cero |
| `cluster.id` | De 1 a 255 de forma predeterminada; 0 indica que no está establecido y está reservado. Con `maxConnectedClusters: 511`, el rango llega a 511. **Modo ENI y chaining aws-cni**: el chart rechaza los ID 128-255 (y 384-511 con `maxConnectedClusters: 511`), salvo que se establezca `extraConfig.allow-unsafe-policy-skb-usage=true` (`templates/validate.yaml:160-168`, cilium/cilium#21330); en EKS con modo ENI, usa ID inferiores a 128 |
| `clustermesh.maxConnectedClusters` | `255` (predeterminado) o `511`; debe ser idéntico en todos los clústeres; configúralo solo durante la instalación |

Compromiso: el ID del clúster ocupa bits de la identidad numérica. Con 255 clústeres, el máximo de identidades locales por clúster es 65535; con 511, baja a 32767. Cambiar `maxConnectedClusters` en un clúster activo puede interrumpir conexiones y hacer que las políticas se apliquen incorrectamente. El comentario de `cluster.id` en `values.yaml` aún indica de 1 a 255; está desactualizado para el caso 511. Cambiar el nombre o el ID del clúster en ejecución requiere reiniciar todas las cargas de trabajo porque las identidades incorporan el ID del clúster.

### 10.3 TLS y authMode

| Valor | Significado |
|---|---|
| `clustermesh.apiserver.tls.auto.method` | `helm` (los certificados solo se renuevan con `helm upgrade`, así que actualiza al menos una vez al año), `cronJob` (programación predeterminada `0 0 1 */4 *`, cada cuatro meses), `certmanager` |
| `tls.auto.certValidityDuration` | `365` días |
| CA compartida | Todos los clústeres deben compartir una CA: copia el Secret `cilium-ca` al otro clúster antes de habilitar la función, o configura `tls.caBundle` |
| Certificados proporcionados por el usuario | Secrets `clustermesh-apiserver-{server,admin,remote,local}-cert`; CN: servidor `clustermesh-apiserver.<ns>.svc` (SAN `*.mesh.cilium.io`, `127.0.0.1`, `::1` y nombres DNS adicionales), admin `admin-<cluster>`, local `local-<cluster>`, remoto `remote` (1.20) o `remote-<cluster-name>` (modo `cluster`) |

`authMode` controla qué usuario de etcd usa cada clúster al conectarse a un clustermesh-apiserver remoto:

| authMode | Comportamiento | Predeterminado en |
|---|---|---|
| `legacy` | Todos los clústeres usan el usuario `remote` | 1.17 y 1.18 (`values.yaml`: v1.17.18 línea 3416, v1.18.14 línea 3634) |
| `migration` | Se crean usuarios por clúster, pero la autenticación sigue usando `remote`; es necesario para cambiar entre `legacy` y `cluster` sin interrupciones | 1.19, 1.20 |
| `cluster` | Cada clúster se autentica como `remote-<cluster-name>`; solo es útil si todos comparten la misma CA | **[versión preliminar 1.21]** |
| `cluster-strict` | **[versión preliminar 1.21]** Igual que `cluster`, pero sin el usuario compartido `remote`; actívalo solo cuando todos los clústeres usen `cluster` | - |

Acción para 1.21: con `clustermesh.useAPIServer=true` y `tls.auto.enabled=false`, vuelve a emitir el certificado remoto con el CN `remote-<cluster-name>`, o establece `authMode` en `migration` o `legacy`. Se espera que la transición sea transparente con certificados automáticos. Cuando `clustermesh.config.enabled=false`, debes crear tú mismo el ConfigMap `clustermesh-remote-users` (nota de 1.19). Cambios en la validez de certificados: en 1.19 se modificó la generación (CronJob dejó de ser un hook de Helm); en 1.20 se establece un año de validez y regeneración cada cuatro meses, y se exige que la validez de la CA sea >= a la del certificado leaf; la clave 1.20 `clustermesh.apiserver.tls.server.{extraDnsNames,extraIpAddresses}` pasó a `clustermesh.apiserver.tls.auto.server.*`.

### 10.4 Configuración de Helm

Valores para cada clúster (estructura de la guía de configuración upstream; la anotación para el balanceador interno es la anotación estándar de esquema del AWS Load Balancer Controller; no se verificó si aparece en los comentarios del chart):

```yaml
# cluster1.yaml
cluster:
  name: cluster1
  id: 1
clustermesh:
  useAPIServer: true
  config:
    enabled: true
  apiserver:
    service:
      type: LoadBalancer
      annotations:
        service.beta.kubernetes.io/aws-load-balancer-scheme: internal
    tls:
      auto:
        enabled: true
        method: cronJob
        server:
          extraDnsNames:
            - cluster1.example.com
```

```yaml
# clusters.yaml  (shared; the local cluster entry is ignored by each cluster)
clustermesh:
  config:
    clusters:
      cluster1:
        address: cluster1.example.com
        port: 2379
      cluster2:
        address: cluster2.example.com
        port: 2379
```

Aplica la configuración con la misma versión del chart ya instalada (este es el único caso en que se acepta `--reuse-values`, como indica la guía upstream), después de copiar primero la CA:

```bash
helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 -n kube-system \
  --kube-context $CLUSTER1 --reuse-values -f clusters.yaml -f cluster1.yaml

kubectl --context $CLUSTER1 get secret -n kube-system cilium-ca -o yaml | \
  kubectl --context $CLUSTER2 create -f -

helm upgrade cilium oci://quay.io/cilium/charts/cilium --version 1.20.2 -n kube-system \
  --kube-context $CLUSTER2 --reuse-values -f clusters.yaml -f cluster2.yaml
```

Exposición del Service: `clustermesh.apiserver.service.type` es `NodePort` de forma predeterminada (`nodePort: 32379`). Upstream recomienda `LoadBalancer` para tener una dirección estable; `NodePort` requiere IP de nodo estables; `ClusterIP` requiere que las ClusterIP sean enrutables entre clústeres. En AWS, usa siempre `service.beta.kubernetes.io/aws-load-balancer-scheme: internal` (y limita `loadBalancerSourceRanges` a los CIDR de las VPC emparejadas) o NodePort/ClusterIP a través de peering/TGW. Un LB expuesto a Internet para este plano de control infringe la política de este repositorio y expone el dominio de confianza de la malla. Acompáñalo con un grupo de seguridad que permita TCP 2379 únicamente desde el grupo de seguridad de nodos del clúster emparejado o su CIDR privado.

Malla parcial: proporciona a cada clúster un mapa `clusters` que incluya solo los clústeres a los que debe conectarse. También se admiten direcciones `ips` estáticas por clúster; **[versión preliminar 1.21]** cambiar las IP estáticas ya no reinicia los Pods y se puede configurar `clustermesh.apiserver.service.port`.

Alternativa con CLI (un contenedor de Helm, práctico para laboratorios):

```bash
cilium install --set cluster.name=$CLUSTER1 --set cluster.id=1 --context $CLUSTER1
cilium install --set cluster.name=$CLUSTER2 --set cluster.id=2 --context $CLUSTER2
cilium clustermesh enable --context $CLUSTER1
cilium clustermesh enable --context $CLUSTER2
cilium clustermesh connect --context $CLUSTER1 --destination-context $CLUSTER2   # one direction is enough
cilium clustermesh status --context $CLUSTER1 --wait
cilium connectivity test --context $CLUSTER1 --multi-cluster $CLUSTER2
```

### 10.5 Espacios de nombres: `defaultGlobalNamespace`

`clustermesh.defaultGlobalNamespace` (predeterminado `true`; presente en el chart 1.20.2, pero no en el chart 1.19.8) controla si se exportan los CiliumEndpoints, CiliumIdentities y Services de un espacio de nombres. Anota un espacio de nombres con `clustermesh.cilium.io/global: "true"` o `"false"` para anularlo. Tanto el espacio de nombres de origen como el de destino deben ser globales para permitir la conectividad y las políticas entre clústeres; además, un Global Service debe estar en un espacio de nombres global y llevar la anotación del servicio. Si estableces el valor predeterminado en `false`, se limita el estado sincronizado entre clústeres y mejora la escalabilidad.

### 10.6 Datos obsoletos: `cacheTTL`

`clustermesh.cacheTTL` tiene el valor predeterminado `"0s"`: los datos almacenados en caché de un clúster remoto desconectado nunca se revocan. Define una duración (por ejemplo, `"15m"`) para descartar los datos remotos obsoletos si no se restablece la conectividad dentro de ese plazo.

## 11. Servicios globales, afinidad y sincronización de EndpointSlice

Un Global Service usa el mismo nombre de Service y el mismo espacio de nombres en cada clúster, y lleva la anotación `service.cilium.io/global: "true"`. Los backends de todos los clústeres se combinan.

| Anotación | Efecto |
|---|---|
| `service.cilium.io/global: "true"` | Hace que el Service sea global. Si un clúster omite la anotación o la establece en false, el Service de ese clúster permanece local |
| `service.cilium.io/shared: "false"` | No exporta los backends de este clúster, pero sigue consumiendo los remotos. Si ambos clústeres tienen el servicio global y `shared` está activo en los dos, cada uno ve los backends locales y remotos; un clúster con `shared: "false"` no exporta ninguno |
| `service.cilium.io/affinity: none\|local\|remote` | `local`: usa backends locales en buen estado y recurre a los remotos solo si todos los locales no están disponibles; `remote` hace lo inverso; `none` (predeterminado) no establece preferencia |
| `service.cilium.io/global-sync-endpoint-slices: "true"` | **Beta.** También crea EndpointSlice para backends remotos, de modo que puedan verlos controladores externos; requiere Helm `clustermesh.enableEndpointSliceSynchronization=true` y reiniciar el operador. Los Global Services Headless lo reciben de forma predeterminada |

```yaml
apiVersion: v1
kind: Service
metadata:
  name: rebel-base
  annotations:
    service.cilium.io/global: "true"
    service.cilium.io/affinity: "local"
spec:
  type: ClusterIP
  ports:
  - port: 80
  selector:
    name: rebel-base
```

Inspecciona la afinidad con `cilium-dbg service list --clustermesh-affinity` (los backends preferidos muestran `(preferred)`). Limitaciones: Global NodePort y clientes en la red del host balancean hacia backends remotos solo con el reemplazo de kube-proxy (o con `socketLB.enabled=true` y `socketLB.hostNamespaceOnly=true`). El controlador de ingress de Cilium funciona en una malla sin sincronizar EndpointSlice; otros controladores de ingress pueden necesitarlo. Métrica añadida en 1.19: `cilium_agent_clustermesh_remote_cluster_endpoints`.

## 12. MCS-API (servicios multiclúster)

MCS-API es la API de Kubernetes SIG-Multicluster: un `ServiceExport` publica un Service y cada clúster obtiene un `ServiceImport` cuyo nombre DNS es `<svc>.<ns>.svc.clusterset.local`. Cilium implementa la importación como un Service derivado llamado `derived-<hash>` que reutiliza la mecánica de Global Services, por lo que ambos mecanismos son compatibles.

| Elemento | Valor |
|---|---|
| Madurez | beta en 1.19 (CRD `multicluster.x-k8s.io/v1alpha1`); estable en 1.20 (`v1beta1`, aún se admite `v1alpha1`) |
| Habilitación | `clustermesh.mcsapi.enabled=true` (reemplaza el valor eliminado `clustermesh.enableMCSAPISupport`) |
| CRD | Las instala el chart (`clustermesh.mcsapi.installCRDs`, predeterminado true) |
| CoreDNS | `clustermesh.mcsapi.corednsAutoConfigure.enabled` (requiere CoreDNS >= 1.12.2, predeterminado en Kubernetes >= 1.35). Configuración manual: ClusterRole `coredns-mcsapi` (permisos list/watch sobre `serviceimports`) y el complemento CoreDNS `multicluster clusterset.local` |
| Espacio de nombres | El espacio de nombres del Service debe existir en todos los clústeres |

```yaml
apiVersion: multicluster.x-k8s.io/v1beta1
kind: ServiceExport
metadata:
  name: rebel-base
spec:
  exportedLabels:
    app.kubernetes.io/name: rebel-base
  exportedAnnotations:
    service.cilium.io/affinity: local
```

Propiedades conciliadas entre exportaciones: SessionAffinity, Ports (unión), Type (ClusterSetIP o Headless), InternalTrafficPolicy, TrafficDistribution y etiquetas/anotaciones. Si hay un conflicto, Cilium establece una condición de conflicto en el estado de `ServiceExport` y resuelve según la fecha de creación, primero el más antiguo; corrige los conflictos en vez de depender de esa resolución. No se admite un nombre DNS por clúster; exporta `mysvc-eu` y `mysvc-us` por separado. Los nombres de host de Pods de StatefulSet se resuelven como `<hostname>.<cluster>.<svc>.<ns>.svc.clusterset.local`. Gateway API puede usar `ServiceImport` como `backendRef`. **[versión preliminar 1.21]** los EndpointSlice duplicados cuyos nombres superen los 40 caracteres tras quitar el prefijo pueden recrearse durante una actualización y causar una breve interrupción.

## 13. Políticas entre clústeres

- **Ámbito predeterminado (1.19+)**: los selectores solo coinciden con endpoints del clúster local (`policy-default-local-cluster`, Helm `clustermesh.policyDefaultLocalCluster: true`). Hasta 1.18, el valor predeterminado incluía todos los clústeres. Antes de actualizar desde 1.18, revisa con `cilium clustermesh inspect-policy-default-local-cluster --all-namespaces` (o `-p <namespace>`); una nota anterior afirmaba que un error de CLI de este comando se había corregido en el árbol 1.21 pre.3, pero no se verificó; confirma el resultado con tu versión de CLI.
- **Selecciona un clúster remoto** mediante la etiqueta `io.cilium.k8s.policy.cluster`:

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-cross-cluster
spec:
  endpointSelector:
    matchLabels:
      name: x-wing
  egress:
  - toEndpoints:
    - matchLabels:
        name: rebel-base
        io.cilium.k8s.policy.cluster: cluster2
```

Para seleccionar cualquier clúster, usa en su lugar `matchExpressions: [{key: io.cilium.k8s.policy.cluster, operator: Exists}]`.

- **Entidades**: `cluster` incluye nodos remotos de la malla, salvo que se restrinja al clúster local (opción de 1.18); 1.20 añade `cluster-mesh`, que abarca todos los endpoints de clústeres conectados en malla además de todo lo incluido en `cluster`.
- Las políticas no se replican: aplícalas en cada clúster.
- La autenticación mutua (SPIRE) no es compatible con Cluster Mesh y se elimina por completo en la versión preliminar 1.21; según las notas de service mesh de este repositorio, ztunnel tampoco es compatible con Cluster Mesh. Consulta [mTLS, cifrado e identidad](12-mtls-encryption-identity.md).
- El firewall del host tiene restricciones cuando se combina con Cluster Mesh (`host.rst`). El cifrado del plano de datos es independiente del mTLS del plano de control; configura WireGuard o IPsec de la misma manera en todos los clústeres y abre UDP 51871 entre ellos. En esta revisión no se volvieron a verificar las salvedades exactas de Cluster Mesh junto con el cifrado.

## 14. Cluster Mesh en EKS

La guía upstream `eks-clustermesh-prep.rst` usa `eksctl`, dos VPC con CIDR sin solapamientos (por ejemplo, `10.0.0.0/16` y `10.1.0.0/16`, evitando `172.17.0.0/16`), peering de VPC y un grupo de seguridad que permite tráfico desde sí mismo y desde el peer. Esa guía también crea subredes públicas con un gateway de Internet. Para este repositorio, adáptala así:

- Usa únicamente subredes privadas para los nodos; no asignes IP públicas ni EIP a los nodos.
- Empareja las VPC (o usa un Transit Gateway) y añade rutas al CIDR del peer en las tablas de rutas privadas.
- Las reglas de grupos de seguridad deben referenciar los grupos de seguridad de nodos de ambos clústeres (o CIDR privados); nunca uses `0.0.0.0/0` ni `::/0`.
- Expón clustermesh-apiserver mediante un NLB interno (`aws-load-balancer-scheme: internal`) o NodePort a través del enlace de peering; establece `loadBalancerSourceRanges` en el CIDR de la VPC del peer.
- El modo ENI proporciona IP de Pod enrutables desde la VPC, así que el enrutamiento nativo solo requiere que `ipv4NativeRoutingCIDR` incluya los rangos de Pods de ambas VPC. En modo overlay, basta con que haya conectividad entre nodos (UDP 8472).
- Usa valores distintos de `cluster.name`/`cluster.id` para cada clúster EKS y el mismo valor de `maxConnectedClusters`. En modo ENI, mantén `cluster.id` por debajo de 128, porque el chart rechaza los valores 128-255 (y 384-511 con `maxConnectedClusters: 511`) salvo que se establezca `extraConfig.allow-unsafe-policy-skb-usage=true` (`validate.yaml:160-168`).

## 15. Laboratorios

> Estos laboratorios no se ejecutaron en un clúster activo durante esta revisión; se contrastaron con el código fuente y la documentación upstream. Ejecútalos únicamente en clústeres desechables.

### Laboratorio 1: Cluster Mesh de dos clústeres

Requisitos previos: dos clústeres desechables cuyos nodos puedan comunicarse entre sí (dos clústeres kind en un host Docker con valores distintos de `networking.podSubnet`/`serviceSubnet` y `disableDefaultCNI: true`, o dos clústeres EKS en VPC emparejadas), Helm 3, Cilium CLI 0.20.1 y contextos `$CLUSTER1`/`$CLUSTER2`.

1. Instala Cilium 1.20.2 en cada clúster con `cluster.name` y `cluster.id` distintos y CIDR de Pods sin solapamientos (las listas de cluster-pool deben diferir).
2. Copia la CA: `kubectl --context $CLUSTER1 get secret -n kube-system cilium-ca -o yaml | kubectl --context $CLUSTER2 create -f -`.
3. Aplica los archivos de valores de la sección 10.4. En kind (sin balanceador de carga), usa `service.type: NodePort` e indica las IP de los nodos en `clustermesh.config.clusters.<name>.ips` con el puerto `32379`.
4. Ejecuta `cilium clustermesh status --context $CLUSTER1 --wait` y luego `cilium connectivity test --context $CLUSTER1 --multi-cluster $CLUSTER2`.

Verificación: `cilium clustermesh status` indica que clustermesh-apiserver está listo y que el clúster remoto está conectado; `kubectl exec -n kube-system ds/cilium -c cilium-agent -- cilium-dbg status --all-clusters` muestra el clúster remoto listo, con su ID y todos los valores de `synchronization status` en true; `cilium-dbg node list` incluye los nodos remotos.

Limpieza: ejecuta `helm uninstall cilium -n kube-system` en ambos clústeres o elimínalos. Para revertir una conexión fallida, quita las entradas de `-f clusters.yaml` y vuelve a ejecutar `helm upgrade` con la misma versión del chart.

### Laboratorio 2: Servicio global, `shared` y afinidad

Requisitos previos: Laboratorio 1.

1. En ambos clústeres, crea el mismo espacio de nombres y un Deployment con Service `rebel-base` y `service.cilium.io/global: "true"`; configura los Pods para responder con el nombre de su clúster.
2. Desde un Pod cliente del clúster 1, ejecuta un bucle de curl y observa las respuestas de ambos clústeres.
3. Anota el Service del clúster 1 con `service.cilium.io/affinity=local` y repite; solo recibirás respuestas del clúster 1. Escala a cero los backends locales y observa la conmutación al clúster 2.
4. En el clúster 2, establece `service.cilium.io/shared: "false"` y comprueba que el clúster 1 no ve los backends del clúster 2, mientras el clúster 2 sigue llegando al clúster 1.

Verificación: `cilium-dbg service list --clustermesh-affinity` en el agente muestra los backends preferidos; `cilium-dbg bpf lb list` muestra las direcciones de backends remotos.

Limpieza: elimina el espacio de nombres en ambos clústeres.

### Laboratorio 3: MCS-API

Requisitos previos: Laboratorio 1 con `clustermesh.mcsapi.enabled=true` y `corednsAutoConfigure.enabled=true` (reinicia CoreDNS si lo configuras manualmente).

1. Crea el espacio de nombres y el Service en ambos clústeres y, después, un `ServiceExport` con el mismo nombre en cada uno.
2. Desde un Pod, resuelve `rebel-base.<namespace>.svc.clusterset.local` y ejecuta curl contra él.
3. Haz que los puertos exportados difieran entre clústeres y examina `kubectl get serviceexport -o yaml` para encontrar la condición de conflicto.

Verificación: existe un `ServiceImport` en ambos clústeres y aparece un Service derivado llamado `derived-<hash>`; el nombre DNS se resuelve.

Limpieza: elimina los ServiceExports, los Services y los espacios de nombres.

### Laboratorio 4: Ensayo de actualización con detección de desviaciones

Requisitos previos: un clúster desechable en 1.19.8 instalado desde un archivo de valores, con el endpoint de métricas Prometheus accesible (o usa `cilium-dbg metrics list`).

1. Guarda los valores: `helm get values cilium -n kube-system -o yaml > old-values.yaml`.
2. Ejecuta el chart de preflight para 1.20.2, confirma que se superan las comprobaciones y elimínalo.
3. Actualiza con `--version 1.20.2 -f old-values.yaml --set upgradeCompatibility=1.19`.
4. Cambia una clave del ConfigMap que requiera reiniciar solo el agente con `cilium config set --restart=false <key> <value>` y consulta la métrica de desviación: `kubectl -n kube-system exec ds/cilium -c cilium-agent -- cilium-dbg metrics list | grep drift_checker_config_delta`.
5. Revierte: ejecuta `helm history cilium -n kube-system` y luego `helm rollback cilium <REVISION> -n kube-system`.

Verificación: `cilium_drift_checker_config_delta` es distinto de cero después del paso 4 y vuelve a 0 después de reiniciar los agentes; `cilium status` indica estado correcto tras actualizar y revertir.

Limpieza: elimina el clúster desechable. Nota sobre la reversión: este laboratorio prueba el procedimiento; no lo ejecutes en un clúster que haya utilizado funciones exclusivas de 1.20.

### Laboratorio 5: Anulación por nodo con CiliumNodeConfig

Requisitos previos: cualquier clúster Cilium 1.20.2 con al menos dos nodos.

1. Etiqueta un nodo: `kubectl label node <node> io.cilium.test-override=true`.
2. Aplica en `kube-system` un `CiliumNodeConfig` que seleccione esa etiqueta y establezca una clave inocua en `defaults`, como `debug: "true"`.
3. Elimina el Pod del agente en el nodo etiquetado y en otro nodo sin etiqueta.

Verificación: el agente recreado en el nodo etiquetado muestra la anulación en su configuración efectiva (`cilium-dbg config`); el agente del nodo sin etiqueta no la muestra.

Limpieza: elimina CiliumNodeConfig, quita la etiqueta y vuelve a crear el Pod del agente.

## Diferencias entre versiones

| Área | 1.18 | 1.19 | 1.20 | 1.21 pre.3 |
|---|---|---|---|---|
| Kernel mínimo | 5.10 | 5.10 | 5.10 | 5.10 (LLVM 21.1) |
| CRD de Gateway API | 1.3.0 | 1.4 | 1.6.1 | 1.6.1 |
| Chart OCI de Helm | no | sí | sí (recomendado) | sí |
| MCS-API | beta | beta (`v1alpha1`, CRD automáticas) | estable (`v1beta1`) | `v1beta1` |
| Valor predeterminado de políticas de Cluster Mesh | todos los clústeres | solo local | solo local; entidad `cluster-mesh` | solo local |
| Valor predeterminado de authMode | `legacy` | `migration` | `migration` | `cluster` (+ `cluster-strict`) |
| KVStoreMesh | `enabled` obsoleto | activado de forma predeterminada | activado de forma predeterminada | siempre activado |
| Autenticación mutua | existe | desactivada de forma predeterminada | obsoleta | eliminada |
| L7 Kafka / proxylib | obsoletos | Kafka obsoleto | eliminados | eliminados |
| BGPv1 | obsoleto | eliminado | - | - |
| IPAM de varios pools | beta | estable | + migración desde cluster-pool | Azure IPAM pasa a varios pools |
| Double Write | beta | beta | beta | beta; `migrate-identity` obsoleto |
| configDriftDetection | retroportado | retroportado | integrado | igual |
| Valor predeterminado de masquerade ENI | IPv4 cambia a false | false | false | masquerade IPv6 desactivado |

## Solución de problemas

| Síntoma | Comprobación |
|---|---|
| No se conecta el clúster remoto | `cilium clustermesh status --wait`; `kubectl exec -n kube-system ds/cilium -c cilium-agent -- cilium-dbg troubleshoot clustermesh [cluster...]` (DNS, conectividad, TLS, autorización de etcd); con KVStoreMesh, también `kubectl exec -n kube-system deploy/clustermesh-apiserver -c kvstoremesh -- clustermesh-apiserver kvstoremesh-dbg troubleshoot` |
| Estado por clúster remoto | `cilium-dbg status --all-clusters` (nodos, endpoints, identidades, servicios, exportaciones MCS-API, reconexiones, `has-quorum`, `cluster-id`, `kvstoremesh` y estado de sincronización); `... kvstoremesh-dbg status --verbose` |
| Registros | agente: `New remote cluster configuration`, `Connection to remote cluster established`, `Unable to establish etcd connection to remote cluster`; `kubectl logs -n kube-system deployment/clustermesh-apiserver -c apiserver` |
| Errores TLS | CA distintas (copia `cilium-ca`), certificados caducados (método `helm` después de un año), CN incorrecto para el `authMode`; Secrets `cilium-clustermesh` y `cilium-kvstoremesh` |
| Resolución de nombres `*.mesh.cilium.io` | `hostAliases` asocia `cluster1.mesh.cilium.io` a la IP del LB, en el DaemonSet (sin KVStoreMesh) o el Deployment clustermesh-apiserver (con KVStoreMesh) |
| Puerto | TCP 2379 debe permitirse mediante referencia al grupo de seguridad o CIDR privado |
| Tráfico entre clústeres denegado | `cilium-dbg identity list` (etiqueta `io.cilium.k8s.policy.cluster`), `cilium-dbg bpf ipcache list`, `cilium-dbg service list`, `cilium-health status`; recuerda que desde 1.19 el ámbito predeterminado de las políticas es el clúster local y que ambos espacios de nombres deben ser globales |
| CIDR solapados o ID duplicados | `cilium-dbg node list` muestra rangos de nodos en conflicto; para corregirlo, reasigna las IP y reinicia las cargas de trabajo |
| Se bloquea la actualización a 1.20 desde un clúster antiguo | Usa 1.20.2 o posterior (error en la CRD `CiliumNodeConfig v2alpha1`) |
| El cambio de configuración no surte efecto | Si `cilium_drift_checker_config_delta > 0`, reinicia los agentes |

## Límites de validación y fuentes

Los laboratorios no se ejecutaron en un clúster activo durante esta revisión; se contrastaron con el código fuente upstream y con la documentación de las etiquetas indicadas más abajo. Los hechos que no se pudieron verificar se enumeran aquí en lugar de afirmarse:

- Si Cilium 1.21 habilita BPF masquerade de forma predeterminada. La nota de versión pre.2 así lo indica, pero en el árbol pre.3 el valor predeterminado del daemon y de `bpf.masquerade` del chart es `false`, y la sección «Changed Options» de `upgrade-next.inc` está vacía.
- Salvedades exactas de Cluster Mesh con WireGuard/IPsec; no se volvieron a comprobar.
- Limitaciones del modo chaining en EKS; comando exacto para quitar el complemento kube-proxy administrado por EKS; si Amazon Linux 2023 aparece mencionado por nombre.
- Versiones de compilaciones de Cilium mantenidas por AWS posteriores a 1.17.9-0 y 1.18.3-0.
- Madurez de `bpf.tproxy` y de ENI IPv6 más allá de la etiqueta citada «beta».
- Fecha de publicación de 1.19.0 y matriz exacta de versiones de Kubernetes probadas para 1.17.
- La etiqueta «estable» de MCS-API proviene de la descripción de la versión v1.20.0; el código fuente confirma que se eliminó el aviso beta y que están las CRD `v1beta1`.
- Nombres de las métricas Double Write: la página upstream de actualización y el código discrepan (sección 8.3); se siguió el código de v1.20.2.
- El valor predeterminado `kubeVersion` del chart es una restricción del chart, no el rango probado.

Fuentes:

- [Documentación de Cilium v1.20.2: operations/upgrade.rst](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade.rst)
- [Notas de actualización de v1.20.2](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/upgrade-current.inc)
- [Documentación de Cluster Mesh v1.20.2](https://github.com/cilium/cilium/tree/v1.20.2/Documentation/network/clustermesh)
- [Solución de problemas de Cluster Mesh v1.20.2](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/troubleshooting_clustermesh.rst)
- [Instalación de Helm y EKS en v1.20.2](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/k8s-install-helm.rst), [requirements-eks.rst](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/installation/requirements-eks.rst)
- [IPAM ENI en v1.20.2](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/concepts/ipam/eni.rst)
- [Requisitos del sistema en v1.20.2](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/operations/system_requirements.rst)
- [Configuración por nodo en v1.20.2](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/configuration/per-node-config.rst), [detección de desviaciones de ConfigMap](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/configuration/configmap-drift-detection.rst)
- [Valores de Helm v1.20.2](https://github.com/cilium/cilium/blob/v1.20.2/install/kubernetes/cilium/values.yaml)
- [Código de las métricas Double Write de v1.20.2](https://github.com/cilium/cilium/blob/v1.20.2/operator/doublewrite/metrics.go)
- [Notas de actualización de v1.21.0-pre.3](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/Documentation/operations/upgrade-next.inc), [values.yaml](https://github.com/cilium/cilium/blob/v1.21.0-pre.3/install/kubernetes/cilium/values.yaml)
- Notas de versión: [v1.20.2](https://github.com/cilium/cilium/releases/tag/v1.20.2), [v1.20.0](https://github.com/cilium/cilium/releases/tag/v1.20.0), [v1.19.0](https://github.com/cilium/cilium/releases/tag/v1.19.0), [v1.18.0](https://github.com/cilium/cilium/releases/tag/v1.18.0), [v1.17.0](https://github.com/cilium/cilium/releases/tag/v1.17.0), [v1.21.0-pre.3](https://github.com/cilium/cilium/releases/tag/v1.21.0-pre.3)
- AWS: páginas de la guía de usuario de EKS sobre complementos CNI alternativos, redes de Auto Mode y CNI para nodos híbridos.

## Cuestionario

Ponte a prueba con el [cuestionario de la parte 13](../../quizzes/networking/cilium/13-clustermesh-install-upgrade-quiz.md).
