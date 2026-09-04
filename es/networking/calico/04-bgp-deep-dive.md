# Parte 4: Análisis detallado de BGP

> **Versiones compatibles**: Calico v3.29+ / Kubernetes 1.28+ **Última actualización**: February 23, 2026

## Introducción

Border Gateway Protocol (BGP) es el protocolo de enrutamiento que impulsa Internet, y Calico lo aprovecha para proporcionar redes altamente escalables y basadas en estándares para clústeres de Kubernetes. A diferencia de las redes de superposición que encapsulan el tráfico, las redes de Calico basadas en BGP habilitan el enrutamiento IP nativo, ofreciendo un rendimiento superior y una integración fluida con la infraestructura de red existente.

Este análisis detallado abarca los fundamentos de BGP, las opciones de arquitectura BGP de Calico, los recursos de configuración y los patrones de despliegue avanzados para entornos empresariales.

***

## Fundamentos de BGP

### ¿Qué es BGP?

BGP (Border Gateway Protocol) es un protocolo de enrutamiento de vector de ruta diseñado para intercambiar información de enrutamiento entre sistemas autónomos. En Calico, BGP distribuye rutas de IP de Pod entre los nodos del clúster y, opcionalmente, hacia la infraestructura de red externa.

### Conceptos clave de BGP

| Concepto                    | Descripción                                                          |
| -------------------------- | -------------------------------------------------------------------- |
| **Sistema autónomo (AS)** | Una colección de redes IP bajo un único dominio administrativo     |
| **Número de AS (ASN)**        | Identificador único de un AS (16 bits: 1-65534, 32 bits: 1-4294967294)  |
| **iBGP**                   | BGP interno: sesiones entre routers en el mismo AS               |
| **eBGP**                   | BGP externo: sesiones entre routers en AS diferentes            |
| **NLRI**                   | Información de alcanzabilidad de la capa de red: las rutas anunciadas |
| **BGP Speaker**            | Un router o software que participa en BGP                        |

### Rangos de números de AS privados

Para el uso interno dentro de las organizaciones, IANA reserva los siguientes rangos de ASN privados:

```
16-bit Private ASN Range: 64512 - 65534
32-bit Private ASN Range: 4200000000 - 4294967294
```

Calico normalmente utiliza ASN en el rango `64512-65534` para BGP interno del clúster.

### Proceso de selección de rutas BGP

Cuando un BGP Speaker recibe varias rutas al mismo destino, selecciona la mejor ruta mediante los siguientes criterios (en orden):

![Un BGP Speaker con varias rutas al mismo destino evalúa siete criterios de desempate en orden, pasando al siguiente criterio en caso de empate, hasta que se selecciona una ruta como la mejor.](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-0.svg)

### Comportamiento de iBGP frente a eBGP

| Atributo               | iBGP                               | eBGP                                   |
| ----------------------- | ---------------------------------- | -------------------------------------- |
| Modificación de AS\_PATH   | No se modifica                       | Antecede el AS local                      |
| Siguiente salto                | No cambia de forma predeterminada             | Cambia a la dirección de peering             |
| TTL predeterminado             | 255                                | 1 (se requiere multihop para no adyacentes) |
| Anuncio de rutas     | Solo a pares eBGP (horizonte dividido) | A todos los pares                           |
| Distancia administrativa | 200                                | 20                                     |

***

## Arquitectura BGP de Calico

![Topologías BGP de Calico lado a lado: la malla completa predeterminada, donde cuatro nodos establecen peering con todos los demás (N(N−1)/2 sesiones), frente a un diseño de Route Reflector donde los nodos establecen peering solo con dos reflectores conectados entre sí (2N+1 sesiones).](../../.gitbook/assets/en-networking-calico-04-bgp-deep-dive-9.png)

[🔍 Ver diagrama interactivo](https://www.atomai.click/kubernetes-docs/archmaps/en-networking-calico-04-bgp-deep-dive-9.html)

### BIRD: implementación de BGP de Calico

Calico utiliza BIRD (BIRD Internet Routing Daemon) como su implementación de BGP. BIRD se ejecuta como parte del DaemonSet `calico-node` en cada nodo.

![Dentro de cada Pod calico-node, la API de Calico alimenta a confd, que configura BIRD; BIRD programa la tabla de enrutamiento y establece peering mediante BGP con routers externos y otros nodos de Calico, mientras que Felix programa de forma independiente el plano de datos iptables/eBPF.](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-1.svg)

### Opciones de topología BGP

Calico admite dos topologías BGP principales:

1. **Malla de nodo a nodo (malla completa)** - Configuración predeterminada
2. **Route Reflectors** - Recomendados para clústeres más grandes

***

## Topología de malla completa

### Cómo funciona la malla completa

En la configuración predeterminada de malla completa, cada nodo de Calico establece una sesión de peering BGP con todos los demás nodos del clúster.

![En la configuración predeterminada de malla completa, cada nodo de Calico establece peering con todos los demás, mostrado desde la perspectiva del Nodo 1 conectándose con los otros cuatro; lo mismo ocurre simétricamente para los cinco nodos, produciendo 10 sesiones BGP en total.](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-2.svg)

### Fórmula del número de sesiones

El número de sesiones BGP en una topología de malla completa crece de forma cuadrática:

```
Sessions = N × (N - 1) / 2

Examples:
- 10 nodes:   10 × 9 / 2 = 45 sessions
- 50 nodes:   50 × 49 / 2 = 1,225 sessions
- 100 nodes:  100 × 99 / 2 = 4,950 sessions
- 500 nodes:  500 × 499 / 2 = 124,750 sessions
```

### Limitaciones de escalabilidad de la malla completa

| Tamaño del clúster  | Sesiones BGP | Memoria por nodo | Impacto de CPU | Recomendación |
| ------------- | ------------ | --------------- | ---------- | -------------- |
| < 50 nodos    | < 1,225      | \~50 MB         | Mínimo    | Malla completa aceptable   |
| 50-100 nodos  | 1,225-4,950  | \~100 MB        | Bajo        | Considere RR    |
| 100-200 nodos | 4,950-19,900 | \~200 MB        | Moderado   | Use RR         |
| > 200 nodos   | > 19,900     | > 400 MB        | Alto       | Requiere RR     |

### Activar/desactivar la malla de nodo a nodo

Compruebe el estado actual:

```bash
calicoctl get bgpconfiguration default -o yaml
```

Desactive la malla de nodo a nodo (al usar Route Reflectors):

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: false
  asNumber: 64512
```

***

## Topología de Route Reflector

### Conceptos de Route Reflector

Los Route Reflectors (RR) resuelven el problema de escalabilidad de iBGP al permitir que un subconjunto de nodos refleje rutas a otros nodos. Esto elimina la necesidad de una malla completa.

![Dos Route Reflectors establecen peering entre sí y con cada nodo cliente, permitiendo que los nodos cliente aprendan rutas sin establecer peering directamente entre sí, lo que elimina la necesidad de una malla completa.](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-3.svg)

### Atributos clave de Route Reflector

| Atributo            | Descripción                                                   |
| -------------------- | ------------------------------------------------------------- |
| **ID de clúster**       | Identifica un conjunto de RR que atienden a los mismos clientes              |
| **ID de originador**    | Evita bucles de enrutamiento (se establece en el ID de router del originador)   |
| **Reflexión de rutas** | El RR vuelve a anunciar rutas aprendidas de los clientes a otros clientes |

### Número de sesiones con Route Reflectors

Con 2 Route Reflectors y N nodos cliente:

```
Sessions = 2 × N + 1 (RR-to-RR peering)

Examples:
- 100 nodes: 2 × 100 + 1 = 201 sessions (vs 4,950 in full-mesh)
- 500 nodes: 2 × 500 + 1 = 1,001 sessions (vs 124,750 in full-mesh)
```

### Configuración de nodos Route Reflector

**Paso 1: Etiquete los nodos designados como Route Reflectors**

```bash
kubectl label node rr-node-1 calico-route-reflector=true
kubectl label node rr-node-2 calico-route-reflector=true
```

**Paso 2: Configure el ID de clúster de Route Reflector**

```yaml
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: rr-node-1
  labels:
    calico-route-reflector: "true"
spec:
  bgp:
    ipv4Address: 10.0.1.10/24
    routeReflectorClusterID: 1.0.0.1
---
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: rr-node-2
  labels:
    calico-route-reflector: "true"
spec:
  bgp:
    ipv4Address: 10.0.1.11/24
    routeReflectorClusterID: 1.0.0.1
```

**Paso 3: Desactive la malla de nodo a nodo**

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: false
  asNumber: 64512
```

**Paso 4: Configure el peering BGP hacia los Route Reflectors**

```yaml
# Peering from non-RR nodes to RR nodes
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: peer-to-route-reflectors
spec:
  nodeSelector: "!has(calico-route-reflector)"
  peerSelector: has(calico-route-reflector)
---
# Peering between RR nodes
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: route-reflector-mesh
spec:
  nodeSelector: has(calico-route-reflector)
  peerSelector: has(calico-route-reflector)
```

### Patrones de redundancia de Route Reflector

**Patrón 1: Route Reflectors duales (clústeres pequeños/medianos)**

![Cada zona de disponibilidad aloja un Route Reflector, y cada nodo de ambas zonas establece peering con ambos Route Reflectors, de modo que la pérdida del Route Reflector de una zona no aísla ningún nodo.](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-4.svg)

**Patrón 2: Route Reflectors jerárquicos (clústeres grandes)**

![Una jerarquía de Route Reflectors de dos niveles: dos Route Reflectors globales establecen peering entre sí y con cada Route Reflector de nivel de rack, y los nodos de cada rack establecen peering solo con el Route Reflector de su rack, manteniendo estable el número de sesiones a medida que crece el clúster.](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-5.svg)

***

## Recurso BGPPeer

El recurso `BGPPeer` define las relaciones de peering BGP entre los nodos de Calico y BGP Speakers externos.

### Tipos de ámbito de BGPPeer

| Tipo              | Descripción          | Caso de uso                |
| ----------------- | -------------------- | ----------------------- |
| **Global**        | Se aplica a todos los nodos | Peering de router externo |
| **Específico del nodo** | Utiliza nodeSelector    | Peering local del rack      |
| **Por nodo**      | Especifica el nodo exacto | Configuraciones especiales  |

### Ejemplo de BGPPeer global

Establezca peering de todos los nodos con switches ToR externos:

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

### Ejemplo de BGPPeer específico de nodo

Establezca peering de los nodos en racks específicos con su switch ToR local:

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

Utilice `peerSelector` para seleccionar dinámicamente nodos de Calico como pares:

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: client-to-rr-peering
spec:
  nodeSelector: "!has(route-reflector)"
  peerSelector: has(route-reflector)
```

### Configuración avanzada de BGPPeer

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: advanced-peer
spec:
  node: specific-node-name
  peerIP: 192.168.1.1
  asNumber: 65100

  # Authentication
  password:
    secretKeyRef:
      name: bgp-secrets
      key: peer-password

  # Timers (seconds)
  keepAliveTime: 30
  holdTime: 90

  # Source address for BGP session
  sourceAddress: 10.0.0.5

  # Maximum number of hops for eBGP multihop
  numAllowedLocalASNumbers: 2

  # TTL security (GTSM)
  ttlSecurity: 1

  # Filters
  filters:
    - action: Accept
      matchOperator: In
      cidr: 10.0.0.0/8
```

***

## Recurso BGPConfiguration

El recurso `BGPConfiguration` define la configuración BGP para todo el clúster.

### BGPConfiguration básica

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  # Cluster AS number
  asNumber: 64512

  # Node-to-node mesh (disable for Route Reflectors)
  nodeToNodeMeshEnabled: false

  # Log level for BIRD
  logSeverityScreen: Info
```

### Anuncio de IP de Service

Calico puede anunciar IP de Service de Kubernetes mediante BGP, lo que permite a los clientes externos acceder directamente a los servicios.

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512
  nodeToNodeMeshEnabled: false

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

### Configuración de comunidades BGP

Las comunidades BGP permiten etiquetar rutas para el enrutamiento basado en políticas en routers externos:

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

  # Named communities (referenced in other configs)
  communities:
    - name: pod-networks
      value: "64512:100"
    - name: service-networks
      value: "64512:300"
    - name: no-export
      value: "65535:65281"  # Well-known NO_EXPORT
```

### Número de AS específico del nodo

Para topologías complejas, puede asignar distintos números de AS por nodo:

```yaml
apiVersion: projectcalico.org/v3
kind: Node
metadata:
  name: border-node-1
spec:
  bgp:
    ipv4Address: 10.0.1.10/24
    asNumber: 65001  # Override cluster default
```

***

## Anuncio de IP de Service

### Tipos de anuncio

| Tipo               | Descripción               | Caso de uso                |
| ------------------ | ------------------------- | ----------------------- |
| **ClusterIP**      | IP de Service interna       | Balanceo de carga interno |
| **ExternalIP**     | IP externa asignada por el usuario | Acceso externo directo  |
| **LoadBalancerIP** | Asignada por el proveedor de nube   | Integración con la nube       |

### Ejemplo de anuncio de ExternalIP

```yaml
# BGPConfiguration for ExternalIP advertisement
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  serviceExternalIPs:
    - cidr: 203.0.113.0/24

---
# Service with ExternalIP
apiVersion: v1
kind: Service
metadata:
  name: my-external-service
spec:
  type: ClusterIP
  externalIPs:
    - 203.0.113.10
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
```

### Anuncio de IP de LoadBalancer

Para clústeres bare-metal sin integración de proveedor de nube:

```yaml
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
  annotations:
    metallb.universe.tf/loadBalancerIPs: 198.51.100.50
spec:
  type: LoadBalancer
  selector:
    app: my-app
  ports:
    - port: 443
      targetPort: 8443
```

### Anuncio selectivo de Service

Utilice anotaciones para controlar qué servicios se anuncian:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: internal-only-service
  annotations:
    # Prevent BGP advertisement
    projectcalico.org/bgp-advertise: "false"
spec:
  type: LoadBalancer
  ...
```

***

## Integración de red física

### Ejemplos de configuración de switches ToR

**Configuración de Cisco NX-OS:**

```
! Configure BGP
router bgp 65001
  router-id 10.0.1.1

  ! Peer with Kubernetes nodes in rack
  neighbor 10.0.1.0/24 remote-as 64512

  address-family ipv4 unicast
    ! Accept pod network routes
    network 10.244.0.0/16
    ! Redistribute connected for node networks
    redistribute connected route-map KUBERNETES-NODES

    ! Route map for prefix filtering
    neighbor 10.0.1.0/24 route-map ACCEPT-K8S-ROUTES in
    neighbor 10.0.1.0/24 route-map DENY-ALL out

! Route map definitions
route-map ACCEPT-K8S-ROUTES permit 10
  match ip address prefix-list K8S-POD-NETS

ip prefix-list K8S-POD-NETS seq 10 permit 10.244.0.0/16 le 26
ip prefix-list K8S-POD-NETS seq 20 permit 10.96.0.0/12 le 32
```

**Configuración de Arista EOS:**

```
! Configure BGP
router bgp 65001
  router-id 10.0.1.1

  ! Peer group for Kubernetes nodes
  neighbor K8S-NODES peer group
  neighbor K8S-NODES remote-as 64512
  neighbor K8S-NODES maximum-routes 10000
  neighbor K8S-NODES password 7 <encrypted>

  ! Dynamic neighbors from subnet
  bgp listen range 10.0.1.0/24 peer-group K8S-NODES

  address-family ipv4
    neighbor K8S-NODES activate
    neighbor K8S-NODES prefix-list K8S-PODS-IN in
    neighbor K8S-NODES prefix-list DENY-ALL out

! Prefix lists
ip prefix-list K8S-PODS-IN seq 10 permit 10.244.0.0/16 le 26
ip prefix-list K8S-PODS-IN seq 20 permit 10.96.0.0/12 le 32
ip prefix-list DENY-ALL seq 10 deny 0.0.0.0/0 le 32
```

**Configuración de Juniper Junos:**

```
protocols {
    bgp {
        group K8S-NODES {
            type external;
            peer-as 64512;
            local-as 65001;

            multipath multiple-as;

            import K8S-IMPORT;
            export DENY-ALL;

            allow 10.0.1.0/24;

            authentication-key "$9$encrypted";
        }
    }
}

policy-options {
    prefix-list K8S-POD-NETS {
        10.244.0.0/16;
    }
    prefix-list K8S-SVC-NETS {
        10.96.0.0/12;
    }
    policy-statement K8S-IMPORT {
        term accept-pods {
            from {
                prefix-list K8S-POD-NETS;
                prefix-length-range /26-/26;
            }
            then accept;
        }
        term accept-services {
            from {
                prefix-list K8S-SVC-NETS;
            }
            then accept;
        }
        term reject-all {
            then reject;
        }
    }
    policy-statement DENY-ALL {
        then reject;
    }
}
```

### Integración con arquitectura spine-leaf

![En una estructura spine-leaf, cada switch leaf establece peering con ambos switches spine para redundancia, y los nodos de Kubernetes de cada rack establecen peering solo con el switch leaf de su rack, de modo que las rutas BGP fluyen desde los nodos a través de las capas leaf y spine.](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-6.svg)

Configuración de Calico para spine-leaf:

```yaml
# Disable node-to-node mesh
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: false
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

## Estrategia de etiquetado de comunidades BGP

### Patrones de diseño de comunidades

| Comunidad     | Significado        | Acción                           |
| ------------- | -------------- | -------------------------------- |
| `64512:100`   | Redes de Pod   | Aceptar, enrutamiento normal           |
| `64512:200`   | IP de Service    | Aceptar, puede aplicar una política especial |
| `64512:300`   | Infraestructura | Enrutamiento de mayor prioridad          |
| `65535:65281` | NO\_EXPORT     | No anunciar fuera del AS      |
| `65535:65282` | NO\_ADVERTISE  | No anunciar a ningún par     |

### Ingeniería de tráfico basada en comunidades

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
    # Production pod networks - advertise everywhere
    - cidr: 10.244.0.0/17
      communities:
        - production

    # Staging pod networks - keep local
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

## Seguridad de BGP

### Autenticación MD5

Proteja las sesiones BGP con autenticación MD5:

```yaml
# Create secret for BGP password
apiVersion: v1
kind: Secret
metadata:
  name: bgp-auth
  namespace: kube-system
type: Opaque
stringData:
  bgp-password: "SuperSecretPassword123!"

---
# Reference in BGPPeer
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: secure-peer
spec:
  peerIP: 10.0.1.1
  asNumber: 65001
  password:
    secretKeyRef:
      name: bgp-auth
      key: bgp-password
```

### Filtrado de prefijos

Limite qué prefijos se aceptan/anuncian:

```yaml
apiVersion: projectcalico.org/v3
kind: BGPFilter
metadata:
  name: allow-pod-nets-only
spec:
  exportV4:
    - action: Accept
      matchOperator: In
      cidr: 10.244.0.0/16
      prefixLength: "24-28"
    - action: Reject
      matchOperator: In
      cidr: 0.0.0.0/0

  importV4:
    - action: Accept
      matchOperator: In
      cidr: 10.0.0.0/8
    - action: Reject
      matchOperator: In
      cidr: 0.0.0.0/0

---
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: filtered-peer
spec:
  peerIP: 10.0.1.1
  asNumber: 65001
  filters:
    - allow-pod-nets-only
```

### GTSM (seguridad TTL)

El mecanismo Generalized TTL Security Mechanism evita los paquetes BGP suplantados:

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: gtsm-enabled-peer
spec:
  peerIP: 10.0.1.1
  asNumber: 65001
  ttlSecurity: 1  # Expect TTL of 254 or higher
```

***

## Ajuste de rendimiento

### Configuración de temporizadores BGP

```yaml
apiVersion: projectcalico.org/v3
kind: BGPPeer
metadata:
  name: tuned-peer
spec:
  peerIP: 10.0.1.1
  asNumber: 65001

  # Keepalive interval (default: 60s)
  keepAliveTime: 20

  # Hold time (default: 180s, must be 3x keepalive)
  holdTime: 60
```

### Agregación de rutas

Reduzca el número de rutas anunciadas agregando CIDR de Pod:

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  # Aggregate individual /26 pod CIDRs into /16
  prefixAdvertisements:
    - cidr: 10.244.0.0/16
      communities:
        - "64512:100"
```

### Reinicio elegante

Active BGP Graceful Restart para minimizar la interrupción del tráfico durante los reinicios de BIRD:

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512

  # Enable graceful restart (BIRD default is enabled)
  # Stale route time in seconds
  nodeMeshMaxRestartTime: 120
```

***

## Depuración de BGP

### Comandos birdcl

Acceda a la interfaz de línea de comandos de BIRD desde un Pod calico-node:

```bash
# Enter calico-node pod
kubectl exec -it -n kube-system calico-node-xxxxx -c calico-node -- /bin/sh

# Show BGP protocol status
birdcl -s /var/run/calico/bird.ctl show protocols all

# Show BGP neighbors
birdcl -s /var/run/calico/bird.ctl show protocols all bgp*

# Show routing table
birdcl -s /var/run/calico/bird.ctl show route

# Show routes to specific prefix
birdcl -s /var/run/calico/bird.ctl show route for 10.244.1.0/24

# Show route export to specific peer
birdcl -s /var/run/calico/bird.ctl show route export Mesh_10_0_1_11

# Show BGP neighbor details
birdcl -s /var/run/calico/bird.ctl show protocols all Mesh_10_0_1_11
```

### Problemas comunes de BGP y soluciones

| Problema                    | Síntomas                      | Solución                              |
| ------------------------ | ----------------------------- | ------------------------------------- |
| Sesiones bloqueadas en Active | No se aprenden rutas             | Compruebe el firewall (TCP 179), los números de AS  |
| Rutas no se propagan   | Pods inaccesibles entre racks | Verifique la configuración de malla de nodo a nodo o RR |
| Fluctuación de rutas           | Conectividad intermitente     | Compruebe los temporizadores BGP, la estabilidad de red   |
| Restablecimientos de sesión           | Established->Active frecuente  | Compruebe MTU, contraseñas MD5              |

### Comandos de diagnóstico

```bash
# Check Calico node status
calicoctl node status

# List all BGP peers
calicoctl get bgppeers -o wide

# Check BGP configuration
calicoctl get bgpconfiguration default -o yaml

# View BIRD logs
kubectl logs -n kube-system calico-node-xxxxx -c calico-node | grep -i bird

# Check IP routes on node
ip route show | grep bird
```

***

## Diseño de varios racks y varios centros de datos

### Varios racks con Route Reflectors

![Dos Route Reflectors en un rack de administración establecen peering entre sí y con cada rack de cómputo, de modo que los nodos de cada rack de cómputo alcanzan las rutas de todos los demás racks sin una malla completa, y la pérdida de un Route Reflector no aísla ningún rack.](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-7.svg)

### Diseño BGP de varios centros de datos

![Cada centro de datos ejecuta su propio AS con sus propios Route Reflectors que establecen peering internamente con sus nodos, y los Route Reflectors de cada centro de datos establecen peering mediante eBGP con un borde WAN compartido, conectando los dos centros de datos.](../../../assets/diagrams/rendered/en-networking-calico-04-bgp-deep-dive-8.svg)

Configuración para varios centros de datos:

```yaml
# DC1 Configuration
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  asNumber: 64512
  nodeToNodeMeshEnabled: false

  communities:
    - name: dc1-origin
      value: "64512:1"

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

## Resumen de prácticas recomendadas

### Recomendaciones de diseño

1. **Tamaño del clúster < 50 nodos**: La malla completa es aceptable
2. **Tamaño del clúster 50-200 nodos**: Despliegue 2-3 Route Reflectors
3. **Tamaño del clúster > 200 nodos**: Despliegue Route Reflectors jerárquicos
4. **Varios racks**: Use una ubicación de Route Reflector consciente del rack
5. **Varios centros de datos**: Use un AS independiente por DC con eBGP entre DC

### Recomendaciones de seguridad

1. Active siempre la autenticación MD5 para pares externos
2. Implemente filtrado de prefijos para evitar la inyección de rutas
3. Use GTSM (seguridad TTL) donde sea compatible
4. Limite las rutas máximas aceptadas por par
5. Supervise las sesiones BGP en busca de anomalías

### Recomendaciones operativas

1. Etiquete los nodos de forma coherente para la topología BGP
2. Documente el esquema de asignación de números de AS
3. Implemente supervisión y alertas de BGP
4. Pruebe regularmente los escenarios de failover
5. Mantenga los temporizadores BGP coherentes entre pares

***

## Referencias

* [Documentación de BGP de Calico](https://docs.tigera.io/calico/latest/networking/configuring/bgp)
* [BIRD Internet Routing Daemon](https://bird.network.cz/)
* [RFC 4271 - BGP-4](https://tools.ietf.org/html/rfc4271)
* [RFC 4456 - BGP Route Reflection](https://tools.ietf.org/html/rfc4456)
* [RFC 5765 - GTSM para BGP](https://tools.ietf.org/html/rfc5082)
