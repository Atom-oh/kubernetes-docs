# Parte 4: BGP en profundidad

> **Base de revisión**: Calico 3.32.2; Calico 3.32 prueba Kubernetes 1.34–1.36. **Última actualización**: 12 de septiembre de 2026.
>
> Los ejemplos suponen un clúster Linux Calico con BGP y el servidor API estándar (`projectcalico.org/v3`). Son topologías alternativas, no un manifiesto que aplicar en secuencia. Conserve la propiedad del operador/GitOps y combine los campos previstos con la configuración existente. La [guía de instalación](01-introduction.md) cubre requisitos API; la [guía de modos](03-networking-modes.md), alternativas sin BGP. Direcciones, ASN y CIDR deben pertenecer a una red bajo su control. Esta revisión no probó un fabric real ni failover de clúster.

## Introducción

Border Gateway Protocol (BGP) intercambia información de accesibilidad. Calico puede distribuir rutas de cargas e integrarse con una red enrutada existente. Es un protocolo de control, compatible con rutas sin encapsulación o IP-in-IP, y no garantiza por sí solo mejor rendimiento. Calico 3.32 también admite rutas de clúster gestionadas por Felix sin BGP; anunciar BGP externo sigue requiriendo un participante BGP.

Esta guía cubre fundamentos, opciones arquitectónicas de Calico, recursos de configuración y patrones avanzados para empresas.

***

## Fundamentos de BGP

### ¿Qué es BGP?

BGP (Border Gateway Protocol) es un protocolo de enrutamiento de vector de ruta diseñado para intercambiar información de enrutamiento entre sistemas autónomos. En Calico, BGP distribuye rutas IP de pods entre nodos del clúster y, opcionalmente, a la infraestructura de red externa.

### Conceptos principales

| Concepto | Descripción |
| -------------------------- | -------------------------------------------------------------------- |
| **Sistema autónomo (AS)** | Conjunto de redes IP bajo un dominio administrativo |
| **Número AS (ASN)** | Identificador de 16 o 32 bits; excluye rangos especiales/reservados |
| **iBGP** | BGP interno: sesiones entre routers del mismo AS |
| **eBGP** | BGP externo: sesiones entre AS distintos |
| **NLRI** | Network Layer Reachability Information: rutas anunciadas |
| **Participante BGP** | Router o software que participa en BGP |

### Rangos privados de ASN

IANA reserva estos rangos para uso interno:

```
16-bit Private ASN Range: 64512 - 65534
32-bit Private ASN Range: 4200000000 - 4294967294
```

Calico usa `64512` por defecto. Los ASN privados deben retirarse del AS_PATH antes de anunciar rutas a Internet global; son identificadores, no direcciones IP intrínsecamente no enrutables. Hay rangos documentales `64496–64511` y `65536–65551`, además de `23456` (AS_TRANS). Consulte [IANA](https://www.iana.org/assignments/as-numbers/as-numbers.xhtml), sin considerar cualquier otro entero un ASN público asignado.

### Selección de rutas

Compare implementación y política reales. Cisco `Weight` y distancias administrativas 20/200 no son propiedades universales ni valores predeterminados de BIRD Calico.

Calico 3.32.2 fija su fork BIRD a `v0.3.3-211-g9111ec3c`. Entre rutas elegibles comparables comprueba LOCAL_PREF mayor, AS_PATH más corto si se habilita, ORIGIN menor, MED menor según la política del AS vecino, eBGP antes que iBGP y menor métrica IGP. Desempata por router/ORIGINATOR_ID, longitud CLUSTER_LIST e IP del peer; la preferencia opcional por rutas antiguas altera el desempate. También importan supresión, next hop accesible, rutas obsoletas y preferencia BIRD. No es una escalera universal de once pasos.

Calico 3.32 convierte sus prioridades a LOCAL_PREF y métricas del kernel. No asuma que toda ruta local exportada conserva LOCAL_PREF 100 predeterminado de BIRD upstream.

### Comportamiento iBGP y eBGP

| Atributo | iBGP | eBGP |
| --- | --- | --- |
| Relación AS | Mismo AS | AS distintos |
| AS_PATH | Normalmente conservado | Normalmente antepone el AS local |
| Propagación | Una ruta iBGP normalmente no pasa a otro peer iBGP; RR es excepción | Depende de política y prevención de bucles |
| Siguiente salto | Suele conservarse y debe ser accesible | Suele cambiar; influyen `nextHopMode` y topología |
| TTL y distancia administrativa | Dependen de implementación/configuración | Dependen de implementación/configuración |

Las rutas locales o aprendidas por eBGP pueden anunciarse a peers iBGP. La configuración externa generada usa multihop de BIRD; no la diagnostique con una tabla genérica «eBGP TTL 1». Inspeccione configuración y negociación reales.

***

## Arquitectura BGP de Calico

### BIRD: implementación BGP de Calico

Con BGP habilitado, Calico ejecuta su fork en `calico-node` y confd genera la configuración. Sin BGP no es necesario BIRD. BIRD y Felix asumen responsabilidades de rutas según el modo.

![Relaciones de control: confd configura BIRD, BIRD intercambia rutas con peers y Felix programa el dataplane.](../../.gitbook/assets/en-networking-calico-04-bgp-deep-dive-1.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-04-bgp-deep-dive-1.html)

> El límite es esquemático: el servidor API Calico es separado, no un proceso en cada Pod calico-node. Felix también gestiona rutas locales y, según el modo, del clúster. BIRD solo existe cuando se habilita.

### Opciones de topología

Las opciones internas habituales son:

1. **Malla completa entre nodos** - Predeterminada
2. **Reflectores de rutas** - Recomendados para clústeres mayores

***

## Topología de malla completa

### Funcionamiento

Con BGP y la malla predeterminada, los nodos participantes no RR se conectan entre sí. Los reflectores quedan excluidos de la malla automática.

![Diez sesiones conectan todos los pares de cinco nodos.](../../.gitbook/assets/en-networking-calico-04-bgp-deep-dive-3.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-04-bgp-deep-dive-3.html)

> Las flechas enumeran sesiones bidireccionales, no tráfico de un solo sentido. Se cuenta una sesión por par para la familia de direcciones tratada.

### Fórmula de sesiones

El número crece cuadráticamente:

```
Sessions = N × (N - 1) / 2

Examples:
- 10 nodes:   10 × 9 / 2 = 45 sessions
- 50 nodes:   50 × 49 / 2 = 1,225 sessions
- 100 nodes:  100 × 99 / 2 = 4,950 sessions
- 500 nodes:  500 × 499 / 2 = 124,750 sessions
```

### Escalado y transición

La fórmula supone una sesión por par y familia. Cada nodo tiene `N−1` peers. CPU/memoria dependen de rutas, cambios, políticas, hardware y objetivos de convergencia; la antigua tabla de memoria y límites 50/200 nodos no eran capacidades medidas.

Compruebe la configuración:

```bash
kubectl get bgpconfiguration.projectcalico.org default -o yaml
```

Si no existe `default`, pueden estar activos los valores predeterminados. Prepare y valide sesiones RR/fabric antes de desactivar la malla. Siga el orden posterior: una etiqueta RR no crea una sustitución operativa.

***

## Topología con reflectores

### Conceptos

Los reflectores (RR) resuelven la escalabilidad iBGP permitiendo que algunos nodos reflejen rutas hacia otros, sin malla completa.

![Seis clientes conectados a dos reflectores, también conectados entre sí.](../../.gitbook/assets/en-networking-calico-04-bgp-deep-dive-4.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-04-bgp-deep-dive-4.html)

> Este dibujo contiene seis clientes más dos RR: 13 sesiones. En la expresión 2N+1 de la figura, N cuenta los clientes, mientras que en la malla completa N cuenta el total de nodos. La malla automática se deshabilita solo después de verificar la topología explícita de sustitución.

### Atributos principales

| Atributo | Descripción |
| -------------------- | ------------------------------------------------------------- |
| **Cluster ID** | Identifica RR que sirven a los mismos clientes |
| **Originator ID** | Evita bucles; toma el router ID del originador |
| **Reflexión de rutas** | Reanuncia a otros clientes rutas aprendidas de clientes |

### Número de sesiones con RR

Sea `T` el total, `R` los reflectores y `C=T−R` los clientes. Si cada cliente conecta con cada RR y los RR entre sí:

```text
RR sessions = C×R + R×(R−1)/2
T=100, R=2: 98×2 + 1 = 197 (full mesh of the same 100 nodes: 4,950)
T=500, R=2: 498×2 + 1 = 997 (full mesh of the same 500 nodes: 124,750)
```

Si «100 nodos» significa 100 clientes más dos RR, son 201 sesiones, pero 102 nodos. No mezcle ambas interpretaciones.

### Configurar nodos RR

Utilice nodos RR preparados y sin cargas de trabajo para esta transición. Establecer un ID de clúster elimina inmediatamente ese nodo de la malla automática; cambiar un nodo ocupado en su ubicación actual puede interrumpir la conectividad. Este ejemplo de almacén de datos Kubernetes conserva las IP existentes de los nodos y los demás campos.

**1. Etiquetar y anotar los RR preparados**

```bash
kubectl label node rr-node-1 rr-node-2 route-reflector=true
kubectl annotate node rr-node-1 rr-node-2   projectcalico.org/RouteReflectorClusterID=244.0.0.1
```

El ID compartido identifica este grupo redundante de RR, no Kubernetes. Otros grupos/niveles necesitan un diseño deliberado de ID.

**2. Crear peerings explícitos**

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: peer-to-rr
spec:
  nodeSelector: "!has(route-reflector)"
  peerSelector: "has(route-reflector)"
---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rr-mesh
spec:
  nodeSelector: "has(route-reflector)"
  peerSelector: "has(route-reflector)"
```

`peerSelector` elige nodos Calico; el peering inverso es automático salvo `reversePeering: Manual`. No descubre routers externos arbitrarios.

**3. Verificar antes de retirar la ruta antigua**

Compruebe sesiones Established en ambos RR/clientes, prefijos esperados enviados/recibidos, next hops accesibles y tráfico representativo. Verifique reenvío ante pérdida de cualquiera de los RR. Las sesiones de malla cliente pueden permanecer durante la transición.

**4. Desactivar la malla automática solo después**

Actualice `BGPConfiguration/default` mediante su propietario, conservando ASN, comunidades y ajustes. El parche equivalente es:

```bash
kubectl patch bgpconfiguration.projectcalico.org default --type=merge   -p '{"spec":{"nodeToNodeMeshEnabled":false}}'
```

Si `default` no existe, créelo mediante el responsable de configuración de la instalación tras las mismas comprobaciones. Vuelva a comprobar las rutas y el tráfico después del cambio; mantenga un plan de reversión para la topología original.

### Patrones de redundancia

**Patrón 1: dos reflectores, clústeres pequeños/medianos**

![Clientes de cada zona conectan con ambos RR ubicados en zonas distintas.](../../.gitbook/assets/en-networking-calico-04-bgp-deep-dive-11.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-04-bgp-deep-dive-11.html)

> Esto proporciona una ruta redundante de distribución de rutas para los clientes supervivientes cuando se pierde un RR, siempre que el transporte, el reenvío y la capacidad restante estén en buen estado. No conserva las cargas de trabajo ubicadas en una zona fallida.

**Patrón 2: reflectores jerárquicos**

Los RR de rack pueden conectarse con RR globales para reducir sesiones por nodo. El total sigue creciendo con clientes/racks. Un solo RR por rack sigue siendo un punto de fallo aunque los globales sean redundantes; evalúe redundancia por nivel, ID, reflexión, conectividad y convergencia.

***

## Recurso BGPPeer

`BGPPeer` define relaciones entre nodos Calico y participantes BGP externos.

### Ámbitos de BGPPeer

| Tipo | Descripción | Uso |
| ----------------- | -------------------- | ----------------------- |
| **Global** | Todos los nodos | Routers externos |
| **Selección de nodos** | Usa nodeSelector | Peering local por rack |
| **Por nodo** | Nodo específico | Configuraciones especiales |

### BGPPeer global

Conectar todos los nodos con switches ToR externos:

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: peer-to-tor-switches
spec:
  peerIP: 10.0.0.1
  asNumber: 65001
  # No nodeSelector means all nodes peer with this address
```

### BGPPeer con selección de nodos

Conectar nodos de racks concretos con su ToR:

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack1-tor-peer
spec:
  nodeSelector: rack == 'rack1'
  peerIP: 10.0.1.1
  asNumber: 65001
---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack2-tor-peer
spec:
  nodeSelector: rack == 'rack2'
  peerIP: 10.0.2.1
  asNumber: 65002
```

### BGPPeer con peerSelector

Seleccione peers Calico dinámicamente con `peerSelector`:

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: client-to-rr-peering
spec:
  nodeSelector: "!has(route-reflector)"
  peerSelector: has(route-reflector)
```

### Configuración avanzada

Cree antes el Secret y BGPFilter `tor-policy` de la sección de seguridad. El ejemplo supone conexión directa y GTSM/autenticación coincidentes.

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: advanced-peer
spec:
  node: specific-node-name
  peerIP: 192.168.1.1
  asNumber: 65100
  password:
    secretKeyRef:
      name: bgp-secrets
      key: datacenter-password
  keepaliveTime: 30s
  maxRestartTime: 120s
  sourceAddress: UseNodeIP
  nextHopMode: Auto
  ttlSecurity: 1
  filters:
    - tor-policy
```

| Campo | Significado en Calico 3.32.2 |
| --- | --- |
| `keepaliveTime` | Cadena de duración; importa la `a` minúscula. Verificada con CRD y renderer publicados. |
| `maxRestartTime` | Tiempo de reinicio ordenado anunciado al vecino, no intervalo de reconexión. |
| `sourceAddress` | `UseNodeIP` o `None`; no admite IP literal. |
| `filters` | Nombres de recursos `BGPFilter` existentes, no reglas incrustadas. |
| `ttlSecurity` | Longitud GTSM en enlaces; `1` indica conexión directa. |
| `numAllowedLocalASNumbers` | Ocurrencias permitidas del ASN local en AS_PATH recibido; relaja prevención de bucles, no multihop. Omitir salvo necesidad del diseño. |

La API `BGPPeer` no tiene `holdTime`, `keepAliveTime` ni `restartTime`. `nextHopMode` acepta `Auto`, `Self` o `Keep`; `keepOriginalNextHop` está obsoleto, no eliminado.

***

## Recurso BGPConfiguration

`BGPConfiguration` define los ajustes BGP del clúster.

### Configuración básica

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  # Cluster AS number
  asNumber: 64512

  # Set topology separately after validating its peerings.
  # Log level for BIRD
  logSeverityScreen: Info
```

### Anuncio de IP de Service

Calico puede anunciar IP de Services existentes a una red enrutada autorizada. El anuncio no asigna la IP, crea un equilibrador de carga en la nube ni garantiza una ruta de retorno accesible. Los CIDR siguientes son ejemplos: combine solo los rangos necesarios con la configuración existente y conserve los demás ajustes.

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  # Advertise Service ClusterIPs
  serviceClusterIPs:
    - cidr: 10.96.0.0/12

  # Advertise Service ExternalIPs
  serviceExternalIPs:
    - cidr: 203.0.113.0/24

  # Advertise Service LoadBalancerIPs
  serviceLoadBalancerIPs:
    - cidr: 198.51.100.0/24
```

### Comunidades BGP

`prefixAdvertisements` añade comunidades a rutas existentes coincidentes, incluidas las de Pods en el renderer actual. **No** origina el prefijo ni agrega todos los bloques Pod en él. Las comunidades nombradas solo actúan cuando se referencian; nombres y valores arbitrarios no implementan por sí solos una política.

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  # Community tagging for pod networks
  prefixAdvertisements:
    - cidr: 10.244.0.0/16
      communities:
        - "64512:100"  # Standard community
        - "64512:200"
    - cidr: 10.96.0.0/12
      communities:
        - "64512:300"  # Service IPs community

  # Named aliases, referenced by prefixAdvertisements in this configuration
  communities:
    - name: pod-networks
      value: "64512:100"
    - name: service-networks
      value: "64512:300"
    - name: no-export
      value: "65535:65281"  # Well-known NO_EXPORT
```

### ASN por nodo

Con datastore Kubernetes, anote el nodo existente para conservar direcciones y campos. Cambiar ASN reinicia los peerings afectados; coordine ambos extremos y la topología.

```bash
kubectl annotate node border-node-1 projectcalico.org/ASNumber=65001
```

Para una anotación existente, actualícela mediante el responsable de configuración después de revisar su valor actual. Otros almacenes de datos utilizan la API Node de Calico; no sustituya un Node existente por un ejemplo parcial que contenga direcciones inventadas.

***

## Anuncio de IP de Service

### Tipos de anuncio y reenvío

| Tipo | Propietario y requisito |
| --- | --- |
| ClusterIP | Kubernetes lo asigna; anunciar el CIDR expone una ruta a la red de Services. |
| ExternalIP | El operador debe poseer y enrutar la dirección. `spec.externalIPs` está obsoleto desde Kubernetes 1.36, pero sigue soportado. |
| LoadBalancer IP | Lo asigna un controlador compatible. Calico puede asignar VIP propios o usar otro asignador elegido explícitamente. Un hostname de LB no es un prefijo IP. |

Con el comportamiento de agregación predeterminado, los Services en modo Cluster utilizan anuncios agregados configurados, mientras que los Services en modo Local utilizan rutas de host (`/32` o `/128`) desde nodos con endpoints locales listos. Los rangos explícitos de prefijos de host y el ajuste `serviceLoadBalancerAggregation` de Calico 3.32 pueden cambiar las rutas anunciadas; inspeccione la RIB/exportación real en vez de deducirlas únicamente del tipo de Service. Valide los endpoints, el plano de datos de Service, el ECMP ascendente y las rutas de retorno. Esto es distinto del anuncio de bloques IPAM de Pods.

### IPAM LoadBalancer nativo

Calico 3.32 incluye un controlador LoadBalancer en `calico-kube-controllers`. Requiere IPPool `allowedUses: [LoadBalancer]`; el grupo Pod normal no suministra esas direcciones automáticamente. Confirme que esté habilitado. Este ejemplo bare-metal independiente requiere namespace `calico-demo` y endpoints listos `app=my-app` en el puerto indicado. Sustituya el rango documental por uno propio y enrutable.

```yaml
apiVersion: projectcalico.org/v3
kind: IPPool
metadata:
  name: service-lb-pool
spec:
  cidr: 198.51.100.0/24
  allowedUses:
    - LoadBalancer
  assignmentMode: Automatic
---
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  serviceLoadBalancerIPs:
    - cidr: 198.51.100.0/24
---
apiVersion: v1
kind: Service
metadata:
  name: my-lb-service
  namespace: calico-demo
  annotations:
    projectcalico.org/loadBalancerIPs: '["198.51.100.50"]'
spec:
  type: LoadBalancer
  loadBalancerClass: calico
  externalTrafficPolicy: Local
  selector:
    app: my-app
  ports:
    - port: 443
      targetPort: 8443
```

La solicitud explícita `projectcalico.org/loadBalancerIPs` debe pertenecer a un grupo elegible y estar disponible; no busca otra IP si falla. Asignación y anuncio son distintos. Revise `assignIPs`: `RequestedServicesOnly` puede retirar IP de Services existentes sin anotaciones. Mantenga la propiedad de grupos y controlador.

MetalLB es un asignador alternativo: su anotación actual de IP solicitada es `metallb.io/loadBalancerIPs`. Elija deliberadamente los responsables de asignación y de anuncios BGP en vez de ejecutar asignadores/emisores competidores para la misma VIP. No anuncie direcciones de equilibradores de carga gestionados por AWS como un grupo de propiedad local.

### Anuncio selectivo

No existe una anotación de exclusión de Service de Calico documentada llamada `projectcalico.org/bgp-advertise`. Seleccione los rangos anunciados en `BGPConfiguration` y aplique BGPFilters específicos de cada par donde sea necesario. La etiqueta de nodo compatible `node.kubernetes.io/exclude-from-external-load-balancers=true` excluye un nodo; no es una exclusión por Service.

Rechazar un `/32` no impide acceso si sigue anunciado un agregado que lo cubre. Para mantener un Service interno, asegúrese de que ningún anuncio lo abarque y aplique control de acceso independiente; el filtrado de rutas no es autorización.

***

## Integración con la red física

### Políticas ToR y adaptación al fabricante

Diseñe conjuntamente ASN, vecinos, familia, autenticación, importación/exportación y next hops accesibles. Decida si los nodos usan una ruta por defecto existente o recibida por BGP. `network` origina una ruta coincidente existente, no acepta rutas del vecino. Un `redistribute connected` amplio puede filtrar redes ajenas.

| Plataforma | Adaptación necesaria |
| --- | --- |
| Cisco IOS XE / NX-OS | Sintaxis exacta de plataforma/versión. Vecinos dinámicos IOS XE usan peer group y `bgp listen range`; no mezcle jerarquías IOS/NX-OS. Defina todos los route maps y prefix lists. |
| Arista EOS | Use la configuración de peer-group, familia, secretos y políticas de la versión desplegada. El antiguo bloque EOS no verificado no era una receta ejecutable. |
| Junos | Prefix-list simple es coincidencia exacta. Use tipos route-filter explícitos para rutas más específicas. |

Por ejemplo, este **fragmento de política Junos**, asociado como política de importación al grupo BGP previsto del ToR orientado a nodos, acepta las rutas de Pods `/26`–`/32` y las rutas de LoadBalancer `/32` planificadas, y después rechaza el resto:

```text
policy-options {
    policy-statement K8S-IMPORT {
        term approved {
            from {
                route-filter 10.244.0.0/16 prefix-length-range /26-/32;
                route-filter 198.51.100.0/24 prefix-length-range /32-/32;
            }
            then accept;
        }
        term reject-rest {
            then reject;
        }
    }
}
```

La longitud mínima supone bloques IPAM `/26`; adáptela al inventario. Direcciones prestadas o movilidad pueden necesitar `/32`, por lo que `le 26` no es un filtro Pod generalmente seguro. No crea vecinos ni anuncia una ruta por defecto. La configuración de equipos y failover no se probaron en ejecución; complete y valide exportación, límites y next hop en la versión exacta antes de desplegar.

### Integración spine-leaf

![Los nodos conectan con switches leaf locales y estos con la capa spine.](../../.gitbook/assets/en-networking-calico-04-bgp-deep-dive-5.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-04-bgp-deep-dive-5.html)

> Los cuadros agrupan sesiones. Compartir ASN de nodos requiere diseño explícito de bucles/override; dos spines no proporcionan redundancia de leaf o uplink del nodo. Direcciones y ASN son ilustrativos, no una configuración completa.

A continuación figuran fragmentos de pares de Calico para un diseño spine-leaf. Confirme primero las etiquetas de los nodos, la accesibilidad directa/recursiva del siguiente salto, las políticas de exportación y la ruta de retorno. Reutilizar ASN 64512 en nodos de distintos racks puede provocar el rechazo de una ruta cuando su AS_PATH contiene el ASN del nodo receptor; diseñe ASN únicos o una política AS-override/bucles de la red validada deliberadamente. No lo evite aumentando a ciegas `numAllowedLocalASNumbers`. Valide la ruta de sustitución antes de eliminar sesiones de malla.

```yaml
# Final topology alternative: establish fabric peerings before removing mesh.
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

---
# Peer nodes with their local leaf switch
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack1-leaf-peer
spec:
  nodeSelector: topology.kubernetes.io/zone == 'rack1'
  peerIP: 10.0.1.1
  asNumber: 65001

---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack2-leaf-peer
spec:
  nodeSelector: topology.kubernetes.io/zone == 'rack2'
  peerIP: 10.0.2.1
  asNumber: 65002

---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: rack3-leaf-peer
spec:
  nodeSelector: topology.kubernetes.io/zone == 'rack3'
  peerIP: 10.0.3.1
  asNumber: 65003
```

***

## Estrategia de comunidades BGP

### Patrones de diseño

Los valores privados son una convención local que requiere política del router, no controles de prioridad incorporados. Las comunidades estándar tienen dos valores de 16 bits; las grandes tienen tres de 32 bits y admiten un ASN de cuatro bytes sin forzarlo al formato estándar.

| Comunidad | Significado | Acción |
| ------------- | -------------- | -------------------------------- |
| `64512:100` | Redes Pod | Aceptar, rutas normales |
| `64512:200` | IP de Services | Aceptar, posible política especial |
| `64512:300` | Infraestructura | Enrutamiento de mayor prioridad |
| `65535:65281` | NO\_EXPORT | No anunciar fuera de la confederación AS, o del AS si no hay confederación |
| `65535:65282` | NO\_ADVERTISE | No anunciar a ningún peer |

### Ingeniería de tráfico por comunidades

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  communities:
    - name: production
      value: "64512:100"
    - name: staging
      value: "64512:200"
    - name: local-only
      value: "65535:65281"  # NO_EXPORT

  prefixAdvertisements:
    # Tag existing production routes; actual propagation follows routing policy
    - cidr: 10.244.0.0/17
      communities:
        - production

    # Add NO_EXPORT to existing staging routes
    - cidr: 10.244.128.0/17
      communities:
        - staging
        - local-only

    # Service IPs
    - cidr: 10.96.0.0/12
      communities:
        - production
```

***

## Seguridad BGP

### Autenticación MD5

Calico admite la opción de firma TCP MD5 para BGP. Autentica el tráfico de pares que comparten el secreto; no cifra el tráfico ni valida la legitimidad de las rutas enviadas por un par autenticado.

Aprovisione `bgp-secrets` mediante su proceso de gestión de secretos en el espacio de nombres donde se ejecuta `calico-node` (`calico-system` para la instalación con operador utilizada aquí; las instalaciones por manifiestos pueden utilizar `kube-system`). El ejemplo requiere la clave `datacenter-password`. Otros ejemplos que referencian `mesh-password` o claves específicas de rack o leaf también requieren esas claves. Configure credenciales coincidentes en los routers correspondientes y confirme que la cuenta de servicio de Calico pueda leer el Secret.

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: secure-peer
spec:
  peerIP: 192.168.1.1
  asNumber: 65100
  password:
    secretKeyRef:
      name: bgp-secrets
      key: datacenter-password
```

### Filtrado de prefijos

Las reglas se evalúan en orden y la primera coincidencia actúa inmediatamente. Las rutas sin coincidencia son **Accept** por defecto; una lista permitida necesita Reject final incondicional. `Equal 0.0.0.0/0` solo coincide con la ruta por defecto; `In 0.0.0.0/0` con todas las IPv4 y `NotIn 0.0.0.0/0` con ninguna.

El siguiente ejemplo de par externo acepta al importar únicamente una ruta predeterminada y la red subyacente planificada `10.0.0.0/16`. Al exportar permite las rutas reales de Pods `/26`–`/32` y las de LoadBalancer `/32`. Adapte los CIDR y sus longitudes al inventario real de rutas; no asocie indiscriminadamente esta política externa a sesiones RR/cliente.

```yaml
apiVersion: projectcalico.org/v3
kind: BGPFilter
metadata:
  name: tor-policy
spec:
  importV4:
    - action: Accept
      matchOperator: Equal
      cidr: 0.0.0.0/0
    - action: Accept
      matchOperator: In
      cidr: 10.0.0.0/16
    - action: Reject
  exportV4:
    - action: Accept
      matchOperator: In
      cidr: 10.244.0.0/16
      prefixLength:
        min: 26
        max: 32
      operations:
        - addCommunity:
            value: "64512:100"
    - action: Accept
      matchOperator: In
      cidr: 198.51.100.0/24
      prefixLength:
        min: 32
        max: 32
    - action: Reject
---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: filtered-peer
spec:
  peerIP: 192.168.1.1
  asNumber: 65100
  filters:
    - tor-policy
```

`prefixLength` es un objeto con `min` y `max`, no una cadena de rango. Calico 3.32 admite operaciones como `addCommunity`. Un Accept explícito de exportación termina antes del procesamiento incorporado de exportación/agregación/`prefixAdvertisements`; puede exportar rutas más específicas de la RIB, por lo que el ejemplo añade la etiqueta Pod en la regla. Revise `show route export` antes de aplicarlo al fabric. BGPFilter no crea rutas ausentes.

### GTSM (seguridad TTL)

GTSM rechaza TTL inferiores al umbral esperado. Reduce suplantación fuera de ruta, pero no autentica ni detiene a un atacante en el enlace. Configure ambos extremos de forma coherente.

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: gtsm-enabled-peer
spec:
  peerIP: 192.168.1.1
  asNumber: 65100
  ttlSecurity: 1
```

BIRD fijado envía TTL 255 y exige al menos `256−hops`. Así, `ttlSecurity: 1` requiere 255, no 254; dos enlaces requieren al menos 254. Verifique la ruta real antes de habilitarlo. No está relacionado con el número de ASN locales permitidos en AS_PATH.

***

## Ajuste de rendimiento

### Temporizadores BGP

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: tuned-peer
spec:
  peerIP: 192.168.1.1
  asNumber: 65100
  keepaliveTime: 20s
  maxRestartTime: 120s
```

El fork fijado de BIRD propone de forma predeterminada un Hold Time de 240 segundos y negocia el valor menor con el vecino. Si no se configura un intervalo de keepalive, utiliza un tercio de ese Hold Time negociado. Un `keepaliveTime` explícito anula el intervalo; **no** cambia automáticamente el Hold Time a tres veces ese valor. Inspeccione los temporizadores realmente negociados y elija un intervalo que se ajuste a ellos.

`BGPPeer` no expone `holdTime`. Las recomendaciones anteriores 60/180, 10/30 y 3/9 no eran defaults Calico verificados ni garantías de detección. BFD en BIRD independiente no implica un CRD/campo BFD soportado por Calico. Pruebe una integración aparte contra el despliegue exacto en lugar de inventar campos.

### Agregación de rutas

Calico normalmente agrega direcciones IPAM locales en bloques asignados; la plantilla actual permite también rutas más específicas de mayor prioridad. Préstamos y movilidad pueden requerir rutas host. `prefixAdvertisements` solo etiqueta rutas existentes y no transforma cada `/26` en un `/16` originado.

Bloques mayores reducen rutas a cambio de granularidad y utilización de IP. `blockSize` de un IPPool existente es inmutable; si necesita otro, use la [migración de grupos](03-networking-modes.md). No aplique un tamaño nuevo al grupo predeterminado existente ni anuncie un agregado desde un router incapaz de alcanzar todo lo cubierto.

### Reinicio ordenado

La plantilla BIRD habilita Graceful Restart. Su beneficio requiere capacidad negociada y reenvío todavía operativo; de otro modo las rutas obsoletas retenidas pueden descartar tráfico. No garantiza actualizaciones sin interrupción.

En peers explícitos, `BGPPeer.maxRestartTime` fija el tiempo anunciado. El ajuste siguiente corresponde a sesiones de **malla automática de nodos**, no a todos los peers:

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeMeshMaxRestartTime: 120s
```

Es una duración en cadena, no entero ni interruptor. Cambie mediante el propietario y valide capacidades y recuperación reales.

***

## Diagnóstico BGP

### Inspeccionar BIRD desde el nodo correcto

Elija nodo y namespace reales. Estos comandos de lectura consultan el socket IPv4 desde la consola del operador. Para IPv6 use `birdcl6` y `/var/run/calico/bird6.ctl`. Sin BGP no es obligatorio ninguno de los demonios.

```bash
CALICO_NAMESPACE=calico-system
CALICO_NODE=worker-1
CALICO_POD="$(kubectl -n "$CALICO_NAMESPACE" get pods -l k8s-app=calico-node \
  --field-selector "spec.nodeName=$CALICO_NODE" -o jsonpath='{.items[0].metadata.name}')"
test -n "$CALICO_POD"
kubectl -n "$CALICO_NAMESPACE" exec "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show protocols all
kubectl -n "$CALICO_NAMESPACE" exec "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show route
```

```bash
CALICO_BGP_PROTOCOL=Global_192_168_1_1
kubectl -n "$CALICO_NAMESPACE" exec "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show protocols all "$CALICO_BGP_PROTOCOL"
kubectl -n "$CALICO_NAMESPACE" exec "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show route export "$CALICO_BGP_PROTOCOL"
kubectl -n "$CALICO_NAMESPACE" exec "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl show route protocol "$CALICO_BGP_PROTOCOL"
kubectl -n "$CALICO_NAMESPACE" exec "$CALICO_POD" -c calico-node -- \
  birdcl -s /var/run/calico/bird.ctl 'show route where net ~ [10.244.0.0/16+]'
```

```bash
kubectl get bgpconfiguration.projectcalico.org default -o yaml
kubectl get bgppeers.projectcalico.org -o wide
kubectl get bgpfilters.projectcalico.org -o yaml
kubectl -n "$CALICO_NAMESPACE" logs "$CALICO_POD" -c calico-node --tail=200
```

Sustituya `CALICO_BGP_PROTOCOL` por un nombre de `show protocols`, como `Mesh_…`, `Global_…` o `Node_…`; no existe un prefijo universal `bgp*`. Entrecomille expresiones para evitar expansión local. `show protocols all` también incluye protocolos no BGP.

Los logs pueden mostrar errores de arranque/confd, pero no encontrar líneas no demuestra salud de BIRD. Revise destino de logs y sesiones. `calicoctl node status` requiere el entorno local del nodo, no solo kubeconfig de una estación. También `ip route` debe inspeccionarse en el nodo/namespace de red correcto.

| Síntoma | Comprobaciones |
| --- | --- |
| Sesión sigue Active | Dirección/ASN, listener TCP/firewall, origen, MD5/GTSM y conectividad |
| Established sin rutas útiles | Filtros, roles RR, endpoints/IPAM, next hop y rechazo de bucles AS |
| Flapping o resets | Pérdida de transporte, MTU, autenticación, timers y cambios de controlador |
| Hay ruta pero falla tráfico | Kernel/FIB, retorno, Service, acceso y agregados que cubren el destino |

BGP Established no demuestra conectividad de la carga.

***

## Diseño multirrack y multicentro de datos

### Varios racks con RR

![Dos reflectores en un rack de gestión conectan con nodos de cómputo de varios racks.](../../.gitbook/assets/en-networking-calico-04-bgp-deep-dive-7.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-04-bgp-deep-dive-7.html)

> Un RR superviviente solo puede conservar la distribución de rutas si su transporte y capacidad siguen disponibles. Ambos RR en un mismo rack de gestión comparten el riesgo de fallo de ese rack; separe dominios de fallo para obtener resiliencia a nivel de rack.

### Diseño BGP multicentro

![Cada centro tiene su AS y reflectores conectados a routers WAN.](../../.gitbook/assets/en-networking-calico-04-bgp-deep-dive-8.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-04-bgp-deep-dive-8.html)

> WAN resume tránsito que debe configurarse aparte; los enlaces visibles no prueban conectividad completa. Etiquetar origen DC1 requiere también la referencia prefixAdvertisements del texto.

A continuación figuran fragmentos de configuración de DC1, suponiendo que su CIDR propio de cargas de trabajo sea `10.244.0.0/16` y que su topología RR local ya funcione. Una comunidad con nombre también debe referenciarse mediante `prefixAdvertisements` para etiquetar las rutas coincidentes. DC2 necesita sus propios CIDR no superpuestos, ASN y definiciones de pares; la WAN necesita enrutamiento y políticas explícitos de tránsito/retorno. Este fragmento no es un despliegue completo de dos centros de datos.

```yaml
# DC1 Configuration
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  communities:
    - name: dc1-origin
      value: "64512:1"
  prefixAdvertisements:
    - cidr: 10.244.0.0/16
      communities:
        - dc1-origin

---
# Peer DC1 RRs with WAN routers
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: dc1-to-wan
spec:
  nodeSelector: has(route-reflector)
  peerIP: 10.255.0.1  # WAN Router
  asNumber: 65000
```

***

## Resumen de buenas prácticas

### Recomendaciones de diseño

1. Dimensione malla/RR mediante rutas, cambios y convergencia medidos.
2. Separe RR redundantes entre dominios de fallo y verifique capacidad/transporte supervivientes.
3. Use etiquetas de rack y un plan documentado de ASN, CIDR y next hop.
4. Añada jerarquía solo comprendiendo reflexión/bucles y redundancia de cada nivel.
5. Diseñe varios centros como red y seguridad completas, no solo dos BGPPeer.

### Recomendaciones de seguridad

1. Active siempre MD5 para peers externos
2. Filtre prefijos para impedir inyección de rutas
3. Use GTSM donde se soporte
4. Configure límites de prefijos soportados en routers externos; no invente un campo BGPPeer.
5. Vigile anomalías en sesiones

### Recomendaciones operativas

1. Etiquete nodos coherentemente con la topología
2. Documente la asignación de ASN
3. Implemente monitorización y alertas BGP
4. Pruebe failover periódicamente
5. Inspeccione timers negociados y recuperación; un keepalive menor no garantiza menor Hold Time.

***

## Referencias

* [Documentación BGP de Calico](https://docs.tigera.io/calico/latest/networking/configuring/bgp)
* [BIRD Internet Routing Daemon](https://bird.network.cz/)
* [RFC 4271 - BGP-4](https://www.rfc-editor.org/rfc/rfc4271)
* [RFC 4456 - Reflexión de rutas BGP](https://www.rfc-editor.org/rfc/rfc4456)
* [RFC 5082 - GTSM](https://www.rfc-editor.org/rfc/rfc5082)

* [API Calico BGPPeer](https://docs.tigera.io/calico/latest/reference/resources/bgppeer)
* [API Calico BGPConfiguration](https://docs.tigera.io/calico/latest/reference/resources/bgpconfig)
* [API Calico BGPFilter](https://docs.tigera.io/calico/latest/reference/resources/bgpfilter)
* [Anuncio de IP de Service](https://docs.tigera.io/calico/latest/networking/configuring/advertise-service-ips)
* [IPAM LoadBalancer de Calico](https://docs.tigera.io/calico/latest/networking/ipam/service-loadbalancer)
* [Procesamiento BIRD en Calico 3.32.2](https://github.com/projectcalico/calico/blob/v3.32.2/confd/pkg/backends/calico/bgp_processor.go)
* [Plantilla BIRD de Calico 3.32.2](https://github.com/projectcalico/calico/blob/v3.32.2/confd/etc/calico/confd/templates/bird.cfg.template)
* [Implementación fijada de mejor ruta BIRD](https://github.com/projectcalico/bird/blob/9111ec3c3ff3e769727a5940d3d829a0be8b5201/proto/bgp/attrs.c)
* [Timers y GTSM de BIRD fijado](https://github.com/projectcalico/bird/blob/9111ec3c3ff3e769727a5940d3d829a0be8b5201/proto/bgp/bgp.c)
* [Vecinos dinámicos Cisco IOS XE](https://www.cisco.com/c/en/us/td/docs/routers/ios/config/17-x/ip-routing/b-ip-routing/m_irg-bgp-dynamic-neighbors.html)
* [Tipos de coincidencia route-filter Junos](https://www.juniper.net/documentation/en_US/junos/topics/usage-guidelines/policy-configuring-route-lists-for-use-in-routing-policy-match-conditions.html)
* [API Service y obsolescencia de externalIPs](https://kubernetes.io/docs/concepts/services-networking/service/)
* [Generación de rutas Service en Calico 3.32.2](https://github.com/projectcalico/calico/blob/v3.32.2/confd/pkg/backends/calico/routes.go)
