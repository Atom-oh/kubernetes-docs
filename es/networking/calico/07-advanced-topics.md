# Parte 7: Temas avanzados de Calico

> **Versiones compatibles**: Calico 3.32.2 / Kubernetes 1.34–1.36 (rango probado)
> **Última actualización**: 12 de septiembre de 2026

## Descripción general

Este capítulo aborda temas avanzados de Calico para entornos de producción, entre ellos un análisis detallado de IPAM, el cifrado WireGuard, Egress Gateway, la federación multiclúster, la compatibilidad con contenedores Windows y patrones de diseño para clústeres a gran escala.

## Análisis detallado de IPAM

Esta sección trata **Calico IPAM**. Host-local y el IPAM del proveedor de nube son asignadores distintos; crear un IPPool de Calico no cambia otro CNI para que use Calico IPAM.

### Bloques, afinidad y límites de asignación

Calico asigna direcciones a partir de bloques asociados a nodos. Un bloque IPv4 `/26` contiene 64 direcciones y uno IPv6 `/122` también contiene 64; esto no garantiza que todas las plataformas proporcionen 64 direcciones utilizables para Pods. Windows reserva cuatro direcciones de cada bloque administrado por Calico.

![El almacén de datos asigna a cada nodo bloques /26 de tamaño fijo procedentes del IPPool 10.244.0.0/16; cada nodo asigna direcciones IP individuales para Pods desde sus bloques afines y recibe otro bloque cuando agota uno.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-0.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-0.html)

> El diagrama muestra un modelo de asignación, no una caché local del nodo que elimine todas las escrituras en el almacén de datos. La afinidad de un bloque no se libera necesariamente en cuanto desaparece su último Pod: también influyen las asignaciones de túneles/VM y el estado de reconciliación y ciclo de vida.

Con la asignación automática normal, Calico puede usar un bloque afín existente, reclamar otro bloque elegible o tomar prestado uno cuando esté permitido. `strictAffinity`, `autoAllocateBlocks`, los límites globales o por solicitud de bloques, la selección del pool y las restricciones de la plataforma pueden hacer que la asignación falle aunque otro pool todavía tenga direcciones libres.

![Al crear un Pod, Calico intenta primero usar el bloque afín propio del nodo; después reclama un bloque libre del pool y, por último, puede tomar prestado un bloque de otro nodo. Solo falla cuando no queda ninguna IP libre en ningún lugar.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-1.html)

> Este flujo simplificado presupone que hay pools elegibles, la asignación automática de bloques está habilitada, se permite tomar bloques prestados y no hay un límite que lo impida. Windows no admite préstamos; no interprete el diagrama como garantía de que la asignación solo puede fallar cuando se agotan todas las direcciones.

Consulte `IPAMConfiguration/default` para ver la configuración global. La página de referencia web indica un límite predeterminado de 20 bloques, pero la **implementación 3.32.2 publicada y la CRD pública inicializan `maxBlocksPerHost` en 0** si no existe configuración. Cero significa que no hay un límite global de bloques; siguen aplicándose los límites por solicitud y de la plataforma, y los clústeres existentes conservan el valor que ya tengan. En la ruta de configuración de IPAM revisada, un límite global positivo debe combinarse con `strictAffinity: true`.

### Elegir el tamaño de bloque antes de crear el pool

Los valores predeterminados son `/26` para IPv4 y `/122` para IPv6. Los rangos admitidos son IPv4 `/20`–`/32` e IPv6 `/116`–`/128`. Elija el tamaño según la demanda prevista de direcciones, la cantidad de nodos, la agregación de rutas y la sobrecarga de asignación, no según el ancho de banda de GPU ni una regla fija como «200 nodos significa /28».

```yaml
# Fresh-pool example; do not apply over an existing pool or overlapping pools.
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: demo-ipv4-pool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  ipipMode: Never
  vxlanMode: Always
  natOutgoing: true
  nodeSelector: all()
```

`blockSize` y el CIDR del pool no se pueden cambiar en el sitio. La creación de un pool nuevo o la migración deben respetar las rutas, los límites de CIDR de Service/nodo y el plan de asignación de cargas de trabajo del clúster real; consulte los [modos de red](03-networking-modes.md). No solape este pool agregado con el ejemplo de subpool que aparece más adelante.

### IPAM Host-local

Host-local usa estado de asignación local al nodo y la configuración de PodCIDR por nodo que proporciona Kubernetes. El operador lo selecciona mediante **`spec.cni.ipam.type: HostLocal`**:

```yaml
# Installation fragment: preserve other settings through the configuration owner.
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  cni:
    type: Calico
    ipam:
      type: HostLocal
```

No existe el interruptor `calicoNetwork.hostLocalIPAMEnabled`. La configuración de red/controlador de Kubernetes ya debe proporcionar PodCIDR distintos y válidos para cada nodo; aplicar parches manuales a nodos existentes no es un procedimiento de migración de IPAM. No suponga que uno de los asignadores libera direcciones siempre de inmediato o con retraso, ni que existe una clasificación universal de escalabilidad entre ambos.

### Varios pools y solicitudes explícitas

Use pools que no se solapen y asigne a cada uno un propósito documentado. El tercer ejemplo es solo para uso manual, de modo que las cargas generales no consuman automáticamente el rango sin SNAT:

```yaml
# Alternative to demo-ipv4-pool; these sub-pools must not overlap another pool.
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: production-pool
spec:
  cidr: 10.244.0.0/18
  blockSize: 26
  vxlanMode: Always
  natOutgoing: true
  nodeSelector: node-type == 'production'
---
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: development-pool
spec:
  cidr: 10.244.64.0/18
  blockSize: 28
  vxlanMode: Always
  natOutgoing: true
  nodeSelector: node-type == 'development'
---
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: routed-workloads-pool
spec:
  cidr: 10.244.128.0/18
  blockSize: 26
  ipipMode: Never
  vxlanMode: Never
  natOutgoing: false
  assignmentMode: Manual
  allowedUses: [Workload]
```

`natOutgoing: false` requiere una ruta de retorno externa funcional y todavía puede aplicarse NAT aguas arriba. No crea un gateway de salida ni una dirección SNAT estable por namespace. Para asignar direcciones a LoadBalancer, use el flujo independiente `allowedUses: [LoadBalancer]` de la [guía de BGP](04-bgp-deep-dive.md).

El Pod siguiente necesita un namespace preparado, etiquetas de nodo coincidentes y una imagen de carga de trabajo revisada que sustituya el marcador de posición:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: production-app
  namespace: calico-demo
  annotations:
    cni.projectcalico.org/ipv4pools: '["production-pool"]'
spec:
  nodeSelector:
    node-type: production
  containers:
    - name: app
      image: registry.example.com/team/app:approved
```

La anotación solicita un pool de IP; `nodeSelector` programa el Pod. En el código de Calico IPAM revisado, una solicitud explícita de pool omite por compatibilidad los selectores de nodo/namespace del pool; por ello, esos selectores **no son un límite de autorización**. Los pools deshabilitados o inexistentes siguen provocando errores. Las anotaciones del namespace pueden proporcionar valores predeterminados para Pods, pero no convierten la selección del pool en una política de red.

### IPv6 y doble pila

El clúster de Kubernetes, el CNI/IPAM, las direcciones de los nodos y la red subyacente ya deben admitir las familias IP elegidas. Agregar pools o activar solo una opción de Felix no cambia la configuración de familias IP del clúster.

```yaml
# A separate fresh dual-stack example.
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: dual-ipv4-pool
spec:
  cidr: 10.244.0.0/16
  blockSize: 26
  vxlanMode: Always
  natOutgoing: true
---
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: dual-ipv6-pool
spec:
  cidr: fd00:10:244::/48
  blockSize: 122
  ipipMode: Never
  vxlanMode: Always
  natOutgoing: false
```

IPv6 VXLAN está admitido en el dataplane Linux compatible; IPv6 IP-in-IP no lo está. El rango ULA anterior no se vuelve enrutable globalmente por el mero hecho de ser IPv6. `natOutgoing: false` requiere rutas de retorno adecuadas u otra ruta de salida diseñada explícitamente.

La autodetección de direcciones de nodo se configura en el operador (o en el entorno de instalación correspondiente), no mediante campos de Felix inventados:

```yaml
# Operator configuration fragment, not a replacement for the existing Installation.
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  calicoNetwork:
    nodeAddressAutodetectionV4:
      kubernetes: NodeInternalIP
    nodeAddressAutodetectionV6:
      kubernetes: NodeInternalIP
```

El campo `ipv6Support` de Felix es booleano, no `Enabled`. Controla el procesamiento de Felix y no sustituye los requisitos completos para doble pila.

### Investigar el agotamiento antes de liberar direcciones

```bash
kubectl get ipamconfigurations.projectcalico.org default -o yaml
calicoctl ipam show
calicoctl ipam show --show-blocks
calicoctl ipam check --show-problem-ips -o ipam-report.json
```

Revise la elegibilidad de los pools, las reservas, la afinidad, los límites por host y la propiedad real de las cargas de trabajo/túneles/VM. No libere una dirección solo porque un comando de ejemplo la llame huérfana. `calicoctl ipam release --block` no es una opción de CLI admitida en la versión revisada.

La herramienta de liberación admite `--from-report` y puede intersectar varios informes; al menos uno debe ser reciente, y la limpieza basada en informes conserva información de secuencia de asignación. Tras verificar las asignaciones notificadas, siga el procedimiento de recuperación de la versión correspondiente. Evite usar `--force`, eliminar directamente IPAMBlock/BlockAffinity o liberar IP arbitrarias como solución general al agotamiento.

## Inspeccionar bloques CIDR afines a nodos

Calico IPAM administra `BlockAffinity`, que expone el estado, nodo, CIDR, eliminación y tipo de afinidad. No equivale a `Node.spec.podCIDR` ni es una instantánea completa de todas las rutas del host cuando hay direcciones prestadas o en migración.

```bash
kubectl get blockaffinities.projectcalico.org \
  -o custom-columns='NAME:.metadata.name,CIDR:.spec.cidr,NODE:.spec.node,STATE:.spec.state,DELETED:.spec.deleted,TYPE:.spec.type'
kubectl get ippools.projectcalico.org \
  -o custom-columns='NAME:.metadata.name,CIDR:.spec.cidr,BLOCK_SIZE:.spec.blockSize'

# Review active host affinities; exclude deletion states and virtual affinities.
kubectl get blockaffinities.projectcalico.org -o json | jq -r \
  '.items[] | select(.spec.state == "confirmed" and .spec.deleted != true and ((.spec.type // "") == "" or .spec.type == "host")) | [.spec.cidr, .spec.node] | @tsv'
```

Estos resultados son inventarios, no comandos `ip route add` listos para ejecutar. El enrutamiento también requiere los siguientes saltos reales de los nodos, el estado actual de las asignaciones, las reglas de exportación/encapsulación del pool y cualquier ruta más específica. No suponga que una IP de nodo de ejemplo o todas las entradas de afinidad forman un plan válido de rutas estáticas.

Para **EKS Hybrid Nodes**, la [guía especializada de CNI](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html) documenta builds de Cilium mantenidos por AWS y traslada los ejemplos de Calico al repositorio Hybrid Examples. La [página general de CNI alternativos de AWS](https://docs.aws.amazon.com/eks/latest/userguide/alternate-cni-plugins.html) todavía describe el soporte básico de Cilium/Calico para Hybrid Nodes. Estas páginas no ofrecen una matriz de soporte de Calico coherente y versionada; mover los ejemplos no demuestra por sí solo que el soporte haya terminado. Confirme la distribución, las capacidades y el responsable de soporte exactos para el despliegue previsto. Esta sección cubre el inventario de IPAM de Calico, no un procedimiento de instalación en Hybrid Nodes.

## Cifrado WireGuard

WireGuard protege el tráfico admitido **entre nodos compatibles y configurados**. No equivale a TLS entre aplicaciones, y el tráfico entre Pods del mismo nodo no atraviesa ese túnel entre nodos. El tráfico que involucre un nodo sin soporte de WireGuard puede quedar sin cifrar. Compruebe el CNI, la familia IP y la ruta real del tráfico de cargas de trabajo/host antes de considerar cumplido un requisito de cifrado.

![El tráfico sale del Pod A en texto sin cifrar; la interfaz WireGuard del nodo 1 (wireguard.cali) lo cifra y cruza la red subyacente de eth0 a eth0 por un túnel WireGuard UDP 51820 cifrado. La interfaz WireGuard del nodo 2 lo descifra y lo entrega al Pod B en texto sin cifrar.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-2.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-2.html)

> En este diagrama, «texto sin cifrar» significa que el tramo local no está protegido por el túnel WireGuard; la aplicación puede usar TLS de forma independiente. El ejemplo muestra el puerto IPv4 predeterminado de WireGuard, 51820. IPv6 tiene interfaces y configuración de puertos independientes.

### Habilitar solo las familias IP necesarias

```yaml
# Example for an already compatible dual-stack Linux deployment.
apiVersion: projectcalico.org/v3
kind: FelixConfiguration
metadata:
  name: default
spec:
  wireguardEnabled: true
  wireguardEnabledV6: true
```

Use `wireguardEnabled` para IPv4 y `wireguardEnabledV6` para una ruta IPv6 habilitada; no active IPv6 solo porque exista el campo. Mantenga las demás opciones de Felix bajo su responsable de configuración y compruebe que ambos pares admitan el kernel necesario. El valor de encapsulación de IPPool del operador `WireguardCrossSubnet` no existe.

Mantenga la autodetección de MTU salvo que la ruta real de red subyacente/encapsulación requiera una anulación. En una red IPv4 subyacente de 1500 bytes, los 60 bytes de sobrecarga de WireGuard sugieren 1440; la sobrecarga de IPv6 y las rutas específicas de la plataforma son distintas. La [explicación de MTU](03-networking-modes.md) indica por qué no se deben sumar a ciegas rutas de encapsulación alternativas.

`wireguardHostEncryptionEnabled` se refiere al tráfico **entre nodos originado en el host o de red del host** que esté admitido, no cifra el salto local del host a un Pod. Consulte la matriz de tráfico admitida de la plataforma en lugar de aplicar este interruptor de forma universal.

### Claves, keepalives y verificación

Calico administra las claves de los nodos y publica información de claves públicas para sus pares. El protocolo WireGuard deriva claves de sesión nuevas durante los handshakes; esto es distinto de una política administrativa de rotación de identidades de nodo.

Los keepalives persistentes mantienen activo el estado de NAT/firewall durante los períodos de inactividad. El intervalo habitual de ejemplo de WireGuard, 25 **segundos**, no es un intervalo de rotación de claves. Ni `wireguardPersistentKeepAlive` ni `wireguardPersistentKeepalive` son campos admitidos de Felix en el esquema de Open Source revisado.

```bash
# On the intended node with wireguard-tools available:
WIREGUARD_INTERFACE=wireguard.cali
wg show "$WIREGUARD_INTERFACE" public-key
wg show "$WIREGUARD_INTERFACE" latest-handshakes
wg show "$WIREGUARD_INTERFACE" endpoints
wg show "$WIREGUARD_INTERFACE" transfer
```

```bash
# Kubernetes datastore: public identity information only.
kubectl get nodes -o json | jq -r \
  '.items[] | [.metadata.name, (.metadata.annotations["projectcalico.org/WireguardPublicKey"] // "-"), (.metadata.annotations["projectcalico.org/WireguardPublicKeyV6"] // "-")] | @tsv'
```

Elija la interfaz real para la familia IP deseada. Las claves públicas, los handshakes y los contadores de bytes ayudan a diagnosticar, pero no prueban que todo el tráfico de aplicaciones esté cifrado. Compruebe la ruta de tráfico prevista y el transporte cifrado esperado. `calicoctl node status` no es una tabla de estado de WireGuard y no es necesario mostrar claves privadas para esta comprobación.

### Registros de rendimiento conservados

Las versiones anteriores en otros idiomas contenían cifras distintas y no verificadas. No se proporcionaron fecha de prueba, hardware, configuración de aceleración, versiones de software ni resultados brutos. Consérvelas como valores históricos comunicados, no como garantías actuales de rendimiento de Calico/WireGuard.

**Registro A (guía anterior en inglés):**

| Métrica | WireGuard | IPsec (AES-GCM) |
| --- | --- | --- |
| Cambio de rendimiento frente a la línea base | −5 a −10% | −15 a −25% |
| Latencia agregada | 0,1–0,3 ms | 0,5–1,0 ms |
| Cambio del uso de CPU | +10–15% | +30–50% |

**Registro B (guía anterior en coreano):**

| Métrica | WireGuard | IPsec (AES-GCM) |
| --- | --- | --- |
| Rendimiento como porcentaje de la línea base | 95–98% | 85–90% |
| Cambio de latencia frente a la línea base | +5–10% | +15–25% |
| Descripción cualitativa del uso de CPU | Medio | Alto |

El Registro B usó como línea base el 100% sin cifrado y describió como bajo el uso de CPU sin cifrado. Los cambios porcentuales no especifican si son puntos porcentuales o cambios relativos de CPU. No combine estos registros como si fueran un único experimento.

### Diferencias entre WireGuard e IPsec

WireGuard usa un diseño criptográfico deliberadamente acotado; IPsec es un framework con varias implementaciones, algoritmos y opciones de administración de claves. El costo de CPU, la sobrecarga de paquetes, la descarga de hardware, la itinerancia y la complejidad de configuración dependen de esas opciones y de la ruta medida. El recuento de líneas de código sin versión no es una métrica de seguridad, y el esquema Open Source de Felix revisado no tiene un campo `ipsecEnabled`.

Para requisitos FIPS, compare el registro de certificación vigente del producto elegido, su versión y las condiciones de operación.

## Egress Gateway

El gateway de salida de Calico Enterprise es un **Pod de tránsito** que hace SNAT para los clientes seleccionados. Tiene requisitos propios de producto y plataforma; la línea base Open Source al principio del capítulo no es una matriz de compatibilidad Enterprise.

La ruta es: política de salida del cliente → túnel al Pod gateway → SNAT del gateway → política de salida del gateway → red externa. Una regla Allow de NetworkPolicy no redirige paquetes ni hace SNAT. `BGPConfiguration.serviceExternalIPs` anuncia rutas de Service; no asigna identidades de salida a las cargas de trabajo.

### Configuración comercial actual

La ruta documentada de Calico-CNI local requiere una instalación Enterprise admitida, namespaces y permisos de seguridad de Pods preparados, direcciones de salida enrutadas y conectividad UDP 4790. Se excluyen GKE y Windows. AWS y Azure tienen procedimientos independientes; no traslade este pool a una configuración de CNI de proveedor de nube.

A través del responsable existente de la configuración Felix predeterminada, habilite `egressIPSupport` de forma uniforme como `EnabledPerNamespace` o, cuando esté autorizado, `EnabledPerNamespaceOrPerPod`. El recurso gateway es **`operator.tigera.io/v1` EgressGateway**. El operador administra su imagen y configuración; no invente un Deployment `calico/egress-gateway`.

```yaml
# Calico Enterprise example, not an Open Source gateway installation.
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: egress-demo-pool
spec:
  cidr: 203.0.113.0/28
  blockSize: 32
  nodeSelector: "!all()"
  natOutgoing: false
---
apiVersion: operator.tigera.io/v1
kind: EgressGateway
metadata:
  name: approved-egress
  namespace: calico-egress
spec:
  replicas: 2
  ipPools:
    - cidr: 203.0.113.0/28
  template:
    metadata:
      labels:
        egress-code: approved
    spec:
      nodeSelector:
        kubernetes.io/os: linux
---
apiVersion: v1
kind: Namespace
metadata:
  name: calico-demo
  annotations:
    egress.projectcalico.org/selector: egress-code == 'approved'
    egress.projectcalico.org/namespaceSelector: projectcalico.org/name == 'calico-egress'
```

Sustituya el CIDR de documentación por direcciones bajo su control y configure la encapsulación/el enrutamiento para la red real. Los bloques `/32` evitan reservar un bloque mayor para cada gateway. `!all()` impide la asignación general automática; una solicitud explícita todavía puede usar el pool, por lo que debe controlar los permisos de anotación.

Dos réplicas requieren dos IP disponibles y una ubicación adecuada entre nodos/dominios de fallo; las réplicas por sí solas no garantizan disponibilidad. El selector de namespace es necesario porque, de otro modo, la selección del gateway usa por defecto el namespace del cliente.

Con `natOutgoing: false`, la IP del Pod gateway se conserva durante esa etapa de NAT de Calico, pero el NAT aguas arriba todavía puede cambiarla. Al habilitar NAT en el pool del gateway, en cambio, puede exponerse la IP del nodo gateway. Compruebe qué origen observa el receptor externo y permita el conjunto de direcciones previsto. Sustituir o actualizar el gateway puede interrumpir conexiones existentes.

### Límites de política e identidad

La política de salida del cliente ve el **destino externo**. Permitir que el cliente contacte con la IP del Pod gateway no enruta ni autoriza su flujo externo original. En la salida del gateway, la identidad/IP de origen y el puerto originales del cliente ya se han traducido. La política por CIDR/puerto de destino sigue siendo útil, pero no se admite política basada en dominios en ese punto.

El enrutamiento avanzado `EgressGatewayPolicy` tiene su propia selección de destino/gateway y el campo `maxNextHops`. No utiliza el campo anterior inventado `maxGatewaysPerClient` de un `projectcalico.org/v3 EgressGateway`.

En Open Source, use un proxy de aplicación o una solución NAT de nube/red subyacente configurados por separado cuando corresponda, y controle aparte el tráfico permitido. Un Pod Envoy sin configuración de bootstrap/listener/upstream no funciona como proxy de salida. Una dirección de origen estable permite configurar una lista de permitidos externa; por sí sola no demuestra cumplimiento de PCI DSS/HIPAA ni autoriza a una aplicación.

## Conectividad y federación multiclúster

Distinga la conectividad enrutada, la identidad de endpoints y el descubrimiento de Services. BGP intercambia rutas, pero no distribuye políticas de Kubernetes ni registros DNS. Typha distribuye estado dentro de su despliegue; no es una instancia principal que reporte a un Federation Controller compartido inventado en el diagrama anterior.

### Conectividad enrutada Open Source

Prepare direcciones que no se solapen, enrutamiento bidireccional, siguientes saltos accesibles y políticas en cada clúster. Tenga en cuenta NAT: `natOutgoing` puede enmascarar un CIDR de Pods remoto que no pertenezca a los pools locales de Calico y cambiar el origen que observa el receptor. Planifique exclusiones y rutas adecuadas en lugar de suponer que se conserva la identidad del Pod.

```yaml
# Receiving cluster only, after routing/source preservation is verified.
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: default.remote-client-access
spec:
  order: 100
  namespaceSelector: kubernetes.io/metadata.name == 'calico-demo'
  selector: app == 'shared-service'
  types: [Ingress]
  ingress:
    - action: Allow
      protocol: TCP
      source:
        nets: [10.245.0.0/16]
      destination:
        ports: [8080]
```

Esta política selecciona solo los endpoints receptores locales. `GlobalNetworkPolicy` indica un alcance global para el clúster/almacén de datos, no que se aplique automáticamente a clústeres remotos. Verifique la salida del emisor, la entrada del receptor y las direcciones de origen reales. La distribución de políticas requiere un flujo de trabajo administrado explícitamente; BGP o Typha no la realizan.

### Federación Enterprise

La guía Enterprise actual distingue lo siguiente:

| Capacidad | Función |
| --- | --- |
| Identidad de endpoints federados | Usa información remota de endpoints de cargas de trabajo/host como entrada para el cálculo local de políticas |
| Federated Services Controller | Lee información de Services/endpoints a través de las API de Kubernetes remotas y mantiene los Services federados locales seleccionados |
| Redes multiclúster | Proporciona un overlay admitido o trabaja con redes de Pods enrutables configuradas por separado |

La identidad de endpoints federados **no replica políticas de red**. Las políticas remotas no se aplican automáticamente en el entorno local; las políticas de cada clúster siguen aplicándose localmente. Las IP de Pods enrutables y la conservación de las direcciones de origen son requisitos previos para la identidad y para que los endpoints de Services remotos sean útiles.

Un Service federado comercial usa una anotación que selecciona **Services de respaldo por etiquetas**, no Pods:

```yaml
# Commercial controller integration; backing Services already exist.
apiVersion: v1
kind: Service
metadata:
  name: catalog-federated
  namespace: calico-demo
  annotations:
    federation.tigera.io/serviceSelector: app == 'catalog'
spec:
  type: ClusterIP
  ports:
    - name: http
      protocol: TCP
      port: 8080
```

Los Services de respaldo deben estar en namespaces con el mismo nombre en los clústeres seleccionados y exponer nombres y protocolos de puerto **coincidentes**. El Service federado omite `spec.selector`; su `targetPort` no es el selector de puerto de respaldo. No administre manualmente sus registros de endpoints.

Las credenciales de API remota, la instalación del controlador, la compatibilidad de versiones de Kubernetes/EndpointSlice y la conectividad de red son requisitos independientes. Este ejemplo no los configura ni demuestra failover entre clústeres. Siga el procedimiento de federación actual del producto y pruebe las rutas reales; no copie el resultado histórico de Endpoints de 2018 como manifiesto de despliegue vigente.

## Compatibilidad con contenedores Windows

Calico admite Windows mediante **HNS**, con restricciones importantes de funciones y plataforma. También se necesitan nodos Linux para los componentes de control y Typha. Un clúster mixto no permite combinar el dataplane eBPF de Calico con Windows.

### Intersección de versiones y plataformas

En un ejemplo de Kubernetes 1.36 dentro del rango probado de Calico 3.32, tanto Kubernetes como Calico incluyen Windows Server 2022. Kubernetes 1.36 también enumera Server 2025, mientras que la página de requisitos de Calico sigue incluyendo las versiones antiguas Server 1809 y Server 2022. No dé por sentado que el sistema operativo antiguo ni que cualquier sistema operativo Windows recién admitido por Kubernetes esté validado con la combinación de Calico/proveedor elegida. Haga coincidir el SO/build del host y de la imagen base del contenedor, y use versiones mantenidas compatibles de runtime/kubelet/kube-proxy.

Los Pods Windows de Kubernetes usan aislamiento de procesos, no aislamiento de contenedores Hyper-V. La instalación documentada actualmente para Calico usa contenedores HostProcess administrados por el operador. El ejemplo ZIP/servicio manual de la versión 3.29 y las versiones antiguas de runtime/kubelet de las instrucciones heredadas no son un procedimiento de instalación actual.

| Área | Restricciones actuales de Calico para Windows |
| --- | --- |
| Red | IPv4 VXLAN sin CrossSubnet, o BGP admitido sin overlay; no IPIP |
| VXLAN | UDP 4789; esta guía no admite CrossSubnet de Windows ni MTU VXLAN personalizado |
| IPAM | No permite préstamos; reserva cuatro direcciones por bloque de Calico, por lo que `/26` proporciona 60 direcciones de Pod; tenga en cuenta la restricción de bloque único de kube-proxy de Windows |
| Enrutamiento | Windows admite el peering BGP compatible, pero no puede ser route reflector ni anunciar IP de Services |
| No admitido aquí | IPv6/doble pila, eBPF, WireGuard, política de host-endpoint, política de capa de aplicación de Istio |
| Plataformas administradas | EKS Windows usa VPC CNI; AKS usa Azure CNI; GKE no equivale a un clúster GCE autoadministrado |

### Configuración del operador

Primero aprovisione nodos Windows compatibles y verifique que haya capacidad Linux para el perfil de alta disponibilidad de controlador/Typha. La guía de Windows requiere tres workers Linux para ese perfil. Prepare un endpoint de API directo y estable con `kubernetes-services-endpoint` en el namespace del operador y use el CIDR real de Service, no un valor kubeadm supuesto.

Esta es la forma de configuración para la **alternativa VXLAN autoadministrada con Calico-CNI**. No sustituya con el ejemplo la lista de pools de una instalación existente ni lo aplique como perfil EKS/Azure CNI:

```yaml
# Self-managed Calico-CNI IPv4 VXLAN target configuration; preserve existing pools/settings.
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  serviceCIDRs:
    - 10.96.0.0/12
  cni:
    type: Calico
  calicoNetwork:
    linuxDataplane: Iptables
    windowsDataplane: HNS
    bgp: Disabled
    ipPools:
      - cidr: 10.244.0.0/16
        blockSize: 26
        encapsulation: VXLAN
        natOutgoing: Enabled
```

El campo válido es `spec.calicoNetwork.windowsDataplane`, no el campo raíz `spec.windowsDataplane` ni `windowsIPAM`. VXLAN usa `VXLAN`, no `VXLANCrossSubnet`, y BGP está deshabilitado para este perfil. La alternativa BGP sin overlay usa otra configuración; no mezcle pools Linux IPIP con pares Windows.

```bash
kubectl get ipamconfigurations.projectcalico.org default -o yaml
# Required for the documented mixed Windows/Calico-IPAM installation:
kubectl patch ipamconfigurations.projectcalico.org default --type=merge \
  -p '{"spec":{"strictAffinity":true}}'
```

La afinidad estricta es necesaria para la configuración documentada de Calico-IPAM en Windows. Planifique el tamaño del bloque antes de conectar Pods a la red: no se admite cambiarlo después. Asegúrese de que kube-proxy esté presente en Windows con la versión/responsable adecuados. Migrar una instalación manual heredada a HostProcess puede eliminar servicios Calico antiguos y reemplazar archivos; primero inventaríe y conserve su configuración.

```bash
kubectl get nodes -l kubernetes.io/os=windows -o wide
kubectl get pods -n calico-system -l k8s-app=calico-node-windows -o wide
kubectl logs -n calico-system -l k8s-app=calico-node-windows -c felix --tail=100
```

Esto es una revisión de configuración, no una prueba de aprovisionamiento o failover de Windows. Pruebe el tráfico de Pods/Services y las políticas en ambos sistemas operativos; los cambios de NAT de Windows pueden aplicarse solo a Pods conectados recientemente y algunas actualizaciones de políticas HNS pueden reiniciar conexiones.

### HNS y ruta de paquetes

![En un nodo Windows, el tráfico de los contenedores converge en Host Networking Service (HNS), que el servicio Calico Node para Windows configura con red y políticas; luego pasa por Virtual Filtering Platform (VFP), que filtra los paquetes antes de salir por la NIC física.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-7.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-7.html)

> HNS/HCS administran redes y endpoints; los mecanismos de conmutador virtual/VFP aplican las reglas del dataplane. Los paquetes no atraviesan un servicio en espacio de usuario de Calico que actúe como proxy de reenvío. El cuadro «Windows Service» representa un agente lógico: las instalaciones actuales con operador ejecutan estos componentes en contenedores HostProcess.

## Ediciones del producto Calico

Use la edición actual y los requisitos de funciones; no dé por sentado que todas las capacidades de observabilidad/política son exclusivas de Enterprise.

| Capacidad | Línea base Open Source 3.32 | Diferencia comercial |
| --- | --- | --- |
| Redes y políticas | Redes Calico, políticas globales y por namespace, varios dataplanes admitidos | Integraciones adicionales de productos/plataformas |
| Niveles de política/RBAC | Disponibles, incluida autorización de Calico que tiene en cuenta niveles | Flujos de gestión de producto y controles adicionales |
| Política HTTP | Disponible mediante la integración configurada de Istio/Dikastes | Compruebe la ruta de aplicación específica del producto |
| Visibilidad de flujos/UI | Goldmane/Whisker y flujo de políticas por etapas disponibles | Análisis, informes y funciones de gestión adicionales |
| Política de dominios DNS | `domains` no está presente en la CRD OSS revisada | Política DNS de dominio documentada para producto comercial |
| Egress/federación | Es posible diseñar enrutamiento/proxy independientes; no existe una CR OSS inventada de gateway/federación | Gateways de salida, identidad remota y Services federados admitidos |
| Soporte | Soporte de la comunidad/proyecto | Los términos dependen de la oferta de soporte adquirida |

Calico Cloud es el producto SaaS administrado y Calico Enterprise es autoadministrado. La documentación de Cloud también describe un Free Tier para gestionar observabilidad/políticas de un único clúster. Revise las funciones, la retención y los términos de soporte actuales; no deduzca de una tabla comparativa sin fuentes un SLA universal 24/7, un precio por nodo, un conjunto de funciones de dataplane idéntico ni el flujo de datos interno del SaaS.

## Diseño de clústeres a gran escala

Use mediciones de cantidad de endpoints, complejidad de políticas, cambios, conexiones de clientes, CPU/RSS y objetivos de convergencia. Una tabla con solo el número de nodos no determina la capacidad de producción.

### Escalado de Typha por el operador

El Tigera Operator **1.42.6** revisado usa el siguiente cálculo para los nodos que cuenta:

```text
N <= 2: 1 replica
N <= 4: 2 replicas
otherwise: max(3, floor(N / 200) + 2)

100 nodes -> 3
500 nodes -> 4
1,000 nodes -> 7
2,000 nodes -> 12
5,000 nodes -> 27
```

Este es el objetivo automático de réplicas de la implementación, no un benchmark que demuestre «200 nodos por Typha». La lógica del recuento de nodos excluye los nodos marcados explícitamente como no programables y el caso pertinente de nodos virtuales de AKS; la ubicación/capacidad Linux real también debe poder alojar el resultado.

Typha distribuye las actualizaciones del almacén de datos a Felix; no agrega escrituras al almacén ni actúa como controlador de federación entre clústeres. Conserve la cuenta de servicio, RBAC, montajes TLS, ubicación y ciclo de vida administrados por el operador.

### Anulaciones admitidas

La anulación actual `typhaDeployment` no expone `spec.replicas` ni variables de entorno arbitrarias del contenedor. No sustituya el Deployment administrado por el ejemplo manual incompleto solo para cambiar el número de réplicas. Use, a través del responsable de configuración, los campos de anulación permitidos:

```yaml
# Override shape only: these illustrative requests are not a capacity recommendation.
apiVersion: operator.tigera.io/v1
kind: Installation
metadata:
  name: default
spec:
  typhaDeployment:
    spec:
      template:
        spec:
          containers:
            - name: calico-typha
              resources:
                requests:
                  cpu: 500m
                  memory: 512Mi
```

Elija las solicitudes reales a partir del uso observado y la capacidad de los dominios de fallo; los valores anteriores solo muestran la forma del campo. Revise juntos los límites, la antiafinidad y las restricciones topológicas, ya que una regla de ubicación imposible puede dejar las réplicas en Pending.

```bash
kubectl get installation.operator.tigera.io default -o yaml
kubectl -n calico-system get deployment calico-typha -o yaml
# Requires a working resource-metrics API:
kubectl -n calico-system top pods -l k8s-app=calico-typha
```

### Route Reflectors

![Jerarquía de Route Reflectors para más de 1000 nodos: tres Route Reflectors de nivel 1 mantienen peering entre sí en una malla completa iBGP, y cada uno refleja rutas a su propio RR de rack y grupo de workers, en lugar de una malla completa entre todos los nodos.](../../.gitbook/assets/en-networking-calico-07-advanced-topics-6.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-07-advanced-topics-6.html)

> El dibujo ilustra una jerarquía, no un despliegue resiliente completo: cada rack muestra solo un RR/enlace ascendente y las etiquetas no garantizan capacidad. Los ID de clúster y las relaciones de reflexión deben coincidir con la jerarquía prevista.

Siga el [procedimiento mantenido de transición de BGP](04-bgp-deep-dive.md): prepare nodos RR adecuados, use anotaciones de nodo que preserven los campos, establezca sesiones/rutas explícitas, verifique el tráfico real y solo entonces retire la malla anterior. El diagrama por sí solo no proporciona la redundancia, los siguientes saltos ni las políticas necesarias.

### Efectos específicos del ajuste de Felix

| Área de configuración | Significado |
| --- | --- |
| Intervalos de actualización de rutas/iptables | Vuelve a comprobar el estado del dataplane local; no es un intervalo general de sondeo de la API de Kubernetes |
| `iptablesBackend: NFT` | Selecciona el frontend iptables-nft; no equivale al dataplane nativo `Nftables` de Calico |
| Logs/logs de flujo | Observe el pipeline de logs admitido y su costo; no agregue a OSS campos comerciales de agregación a archivos |
| Timeouts de salud | Controlan la detección de fallos/estado Ready; los valores más largos no aceleran la programación |
| Marcas, rangos de tablas de rutas, failsafes | Afectan la red compartida del host/el acceso al plano de control; no son ajustes genéricos de memoria/CPU |
| eBPF/DSR | Cambia el dataplane/la ruta de red y tiene requisitos de plataforma; no es un preset de capacidad |

`datastoreType`, `typhaAddr` y `typhaK8sServiceName` no son campos que se deban agregar a la API revisada de FelixConfiguration. Los nombres de campo anteriores `...Secs`/`...Millis` de la receta previa tampoco pertenecían a la API actual. Lea el recurso y la referencia actuales antes de cambiar su configuración administrada por otro componente.

### Elección del almacén de datos

El almacén de datos de Kubernetes evita operar un servicio etcd de Calico por separado y es obligatorio para el dataplane eBPF actual. Direct etcd puede ser adecuado para instalaciones admitidas que no usan Kubernetes o diseñadas por separado, pero no están respaldadas las afirmaciones «más de 5.000 nodos requieren etcd» y «etcd siempre es más rápido».

Un ConfigMap llamado `etcd-config` no configura un proceso etcd a menos que el despliegue lo consuma. Tampoco puede configurar el almacén administrado del plano de control de un servicio de nube. Direct etcd necesita su propia topología, TLS/autenticación, copias de seguridad, recuperación y plan de capacidad.

La guía de ajuste de etcd relaciona los valores heartbeat/election con la latencia de red y disco. No traslade un preset de cuota/instantáneas/timeouts sin medir el clúster real. Mantenga separada la configuración del plano de control de los intervalos de actualización del dataplane de Calico.

## Validación antes de cambiar la escala

1. Establezca líneas base actuales de asignación, rutas, políticas y conexiones de clientes.
2. Cambie la opción prevista a través de su responsable y conserve los campos no relacionados.
3. Observe el uso de recursos, el retraso de reconciliación, el estado Ready y las rutas reales de tráfico positivo/negativo.
4. Pruebe la pérdida prevista de un componente/nodo/dominio de fallo y el procedimiento de reversión.

Los rangos anteriores de CPU/memoria/número de nodos eran estimaciones de planificación no validadas, no resultados medidos de capacidad. Durante esta revisión no se desplegó ningún clúster grande, Windows, gateway ni almacén de datos.

## Referencias

- [API de Calico IPPool](https://docs.tigera.io/calico/latest/reference/resources/ippool)
- [API de IPAMConfiguration](https://docs.tigera.io/calico/latest/reference/resources/ipamconfig)
- [API de BlockAffinity](https://docs.tigera.io/calico/latest/reference/resources/blockaffinity)
- [Valores predeterminados y lógica de asignación IPAM publicados](https://raw.githubusercontent.com/projectcalico/calico/v3.32.2/libcalico-go/lib/ipam/ipam.go)
- [Soporte actual de CNI de AWS para Hybrid Nodes](https://docs.aws.amazon.com/eks/latest/userguide/hybrid-nodes-cni.html)
- [Protocolo WireGuard](https://www.wireguard.com/protocol/)
- [Semántica de keepalive de WireGuard](https://www.wireguard.com/quickstart/)
- [Cifrado de Calico](https://docs.tigera.io/calico/latest/network-policy/encrypt-cluster-pod-traffic)
- [Egress Gateway Enterprise en instalaciones locales](https://docs.tigera.io/calico-enterprise/latest/networking/egress/egress-gateway-on-prem)
- [Egress Gateway Enterprise en AWS](https://docs.tigera.io/calico-enterprise/latest/networking/egress/egress-gateway-aws)
- [Alcance de federación Enterprise](https://docs.tigera.io/calico-enterprise/latest/multicluster/federation/overview)
- [Federated Services Controller](https://docs.tigera.io/calico-enterprise/latest/multicluster/federation/services-controller)
- [Requisitos de Calico para Windows](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/requirements)
- [Flujo de trabajo de Calico Operator para Windows](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/operator)
- [Limitaciones de Calico para Windows](https://docs.tigera.io/calico/latest/getting-started/kubernetes/windows-calico/limitations)
- [Arquitectura de red de Windows](https://learn.microsoft.com/en-us/virtualization/windowscontainers/container-networking/architecture)
- [Fuente de la documentación de Windows para Kubernetes 1.36](https://raw.githubusercontent.com/kubernetes/website/release-1.36/content/en/docs/concepts/windows/intro.md)
- [Descripción actual del producto Calico](https://docs.tigera.io/calico-cloud/about)
- [Función de escalado de Operator 1.42.6](https://raw.githubusercontent.com/tigera/operator/v1.42.6/pkg/common/autoscale.go)
- [Autoscaler de Typha de Operator 1.42.6](https://raw.githubusercontent.com/tigera/operator/v1.42.6/pkg/controller/installation/typha_autoscaler.go)
- [API de Operator](https://docs.tigera.io/calico/latest/reference/installation/api)
- [API de Felix](https://docs.tigera.io/calico/latest/reference/resources/felixconfig)
- [Métricas de componentes](https://docs.tigera.io/calico/latest/operations/monitor/monitor-component-metrics)
- [Ajuste de etcd](https://etcd.io/docs/v3.6/tuning/)
- [Configuración de etcd](https://etcd.io/docs/v3.6/op-guide/configuration/)

## Cuestionario

Ponga a prueba su comprensión con el [cuestionario de temas avanzados](../../quizzes/networking/calico/07-advanced-topics-quiz.md).
