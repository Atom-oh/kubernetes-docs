# Parte 4: Análisis detallado de BGP

> **Versiones compatibles**: Calico v3.29+ / Kubernetes 1.28+ **Última actualización**: February 23, 2026

## Introducción

Border Gateway Protocol (BGP) es el protocolo de enrutamiento que impulsa internet, y Calico lo aprovecha para proporcionar redes altamente escalables y basadas en estándares para clústeres de Kubernetes. A diferencia de las redes overlay que encapsulan el tráfico, las redes basadas en BGP de Calico permiten el enrutamiento IP nativo, ofreciendo un rendimiento superior y una integración fluida con la infraestructura de red existente.

Este análisis detallado cubre los fundamentos de BGP, las opciones de arquitectura BGP de Calico, los recursos de configuración y patrones de implementación avanzados para entornos empresariales.

***

## Fundamentos de BGP

### ¿Qué es BGP?

BGP (Border Gateway Protocol) es un protocolo de enrutamiento de vector de ruta diseñado para intercambiar información de enrutamiento entre sistemas autónomos. En Calico, BGP distribuye rutas IP de Pod entre los nodos del clúster y, opcionalmente, a la infraestructura de red externa.

### Conceptos clave de BGP

| Concepto                    | Descripción                                                          |
| -------------------------- | -------------------------------------------------------------------- |
| **Sistema autónomo (AS)** | Una colección de redes IP bajo un único dominio administrativo     |
| **Número de AS (ASN)**        | Identificador único para un AS (16 bits: 1-65534, 32 bits: 1-4294967294)  |
| **iBGP**                   | BGP interno: sesiones entre routers en el mismo AS               |
| **eBGP**                   | BGP externo: sesiones entre routers en AS diferentes            |
| **NLRI**                   | Información de alcanzabilidad de capa de red: las rutas que se anuncian |
| **BGP Speaker**            | Un router o software que participa en BGP                        |

### Rangos de números de AS privados

Para uso interno en las organizaciones, IANA reserva los siguientes rangos de ASN privados:

```
16-bit Private ASN Range: 64512 - 65534
32-bit Private ASN Range: 4200000000 - 4294967294
```

Calico suele usar ASN en el rango `64512-65534` para BGP interno del clúster.

### Proceso de selección de rutas de BGP

Cuando un BGP speaker recibe varias rutas al mismo destino, selecciona la mejor ruta mediante los siguientes criterios (en orden):

```mermaid
flowchart TD
    A[Receive Multiple Routes] --> B{Highest Weight?}
    B -->|Tie| C{Highest LOCAL_PREF?}
    C -->|Tie| D{Locally Originated?}
    D -->|Tie| E{Shortest AS_PATH?}
    E -->|Tie| F{Lowest Origin Type?}
    F -->|Tie| G{Lowest MED?}
    G -->|Tie| H{eBGP over iBGP?}
    H -->|Tie| I{Lowest IGP Metric?}
    I -->|Tie| J{Oldest Route?}
    J -->|Tie| K{Lowest Router ID}
    K --> L[Select Best Route]
```

### Comportamiento de iBGP frente a eBGP

| Atributo               | iBGP                               | eBGP                                   |
| ----------------------- | ---------------------------------- | -------------------------------------- |
| Modificación de AS\_PATH   | No se modifica                       | Antecede el AS local                      |
| Siguiente salto                | No cambia de forma predeterminada             | Cambia a la dirección de peering             |
| TTL predeterminado             | 255                                | 1 (se requiere multihop para nodos no adyacentes) |
| Anuncio de rutas     | Solo a pares eBGP (split-horizon) | A todos los pares                           |
| Distancia administrativa | 200                                | 20                                     |

***

## Arquitectura BGP de Calico

![Topologías BGP de Calico](../../.gitbook/assets/calico_bgp_topology.png)

### BIRD: la implementación BGP de Calico

Calico usa BIRD (BIRD Internet Routing Daemon) como su implementación BGP. BIRD se ejecuta como parte del DaemonSet `calico-node` en cada nodo.

```mermaid
graph TB
    subgraph "Calico Node"
        FV[Felix] --> DT[Dataplane<br/>iptables/eBPF]
        BIRD[BIRD BGP] --> RT[Routing Table]
        CONFD[confd] --> BIRD
        API[Calico API] --> CONFD
    end

    BIRD <--> EXT[External Router]
    BIRD <--> OTHER[Other Calico Nodes]
```

### Opciones de topología BGP

Calico admite dos topologías BGP principales:

1. **Malla de nodo a nodo (malla completa)**: configuración predeterminada
2. **Route Reflectors**: recomendados para clústeres más grandes

***

## Topología de malla completa

### Cómo funciona la malla completa

En la configuración de malla completa predeterminada, cada nodo de Calico establece una sesión de peering BGP con todos los demás nodos del clúster.

```mermaid
graph TB
    subgraph "Full-Mesh BGP (5 Nodes)"
        N1[Node 1<br/>AS 64512] <--> N2[Node 2<br/>AS 64512]
        N1 <--> N3[Node 3<br/>AS 64512]
        N1 <--> N4[Node 4<br/>AS 64512]
        N1 <--> N5[Node 5<br/>AS 64512]
        N2 <--> N3
        N2 <--> N4
        N2 <--> N5
        N3 <--> N4
        N3 <--> N5
        N4 <--> N5
    end
```

### Fórmula de recuento de sesiones

El número de sesiones BGP en una topología de malla completa crece cuadráticamente:

```
Sessions = N × (N - 1) / 2

Examples:
- 10 nodes:   10 × 9 / 2 = 45 sessions
- 50 nodes:   50 × 49 / 2 = 1,225 sessions
- 100 nodes:  100 × 99 / 2 = 4,950 sessions
- 500 nodes:  500 × 499 / 2 = 124,750 sessions
```

### Limitaciones de escalado de la malla completa

| Tamaño del clúster  | Sesiones BGP | Memoria por nodo | Impacto de CPU | Recomendación |
| ------------- | ------------ | --------------- | ---------- | -------------- |
| < 50 nodos    | < 1,225      | \~50 MB         | Mínimo    | Malla completa aceptable   |
| 50-100 nodos  | 1,225-4,950  | \~100 MB        | Bajo        | Considerar RR    |
| 100-200 nodos | 4,950-19,900 | \~200 MB        | Moderado   | Usar RR         |
| > 200 nodos   | > 19,900     | > 400 MB        | Alto       | Requiere RR     |

### Habilitar/deshabilitar la malla de nodo a nodo

Compruebe el estado actual:

```bash
calicoctl get bgpconfiguration default -o yaml
```

Deshabilite la malla de nodo a nodo (al usar Route Reflectors):

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

```mermaid
graph TB
    subgraph "Route Reflector Topology"
        subgraph "Route Reflectors"
            RR1[RR Node 1<br/>Cluster ID: 1.0.0.1]
            RR2[RR Node 2<br/>Cluster ID: 1.0.0.1]
        end

        subgraph "Client Nodes"
            C1[Client 1]
            C2[Client 2]
            C3[Client 3]
            C4[Client 4]
            C5[Client 5]
            C6[Client 6]
        end

        RR1 <--> RR2

        C1 --> RR1
        C2 --> RR1
        C3 --> RR1
        C1 --> RR2
        C2 --> RR2
        C3 --> RR2

        C4 --> RR1
        C5 --> RR1
        C6 --> RR1
        C4 --> RR2
        C5 --> RR2
        C6 --> RR2
    end
```

### Atributos clave de Route Reflector

| Atributo            | Descripción                                                   |
| -------------------- | ------------------------------------------------------------- |
| **ID de clúster**       | Identifica un conjunto de RR que atienden a los mismos clientes              |
| **ID del originador**    | Evita bucles de enrutamiento (se establece en el ID de router del originador)   |
| **Reflexión de rutas** | El RR vuelve a anunciar rutas aprendidas de clientes a otros clientes |

### Recuento de sesiones con Route Reflectors

Con 2 Route Reflectors y N nodos cliente:

```
Sessions = 2 × N + 1 (RR-to-RR peering)

Examples:
- 100 nodes: 2 × 100 + 1 = 201 sessions (vs 4,950 in full-mesh)
- 500 nodes: 2 × 500 + 1 = 1,001 sessions (vs 124,750 in full-mesh)
```

### Configurar nodos Route Reflector

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

**Paso 3: Deshabilite la malla de nodo a nodo**

```yaml
apiVersion: projectcalico.org/v3
kind: BGPConfiguration
metadata:
  name: default
spec:
  nodeToNodeMeshEnabled: false
  asNumber: 64512
```

**Paso 4: Configure el peering BGP hacia Route Reflectors**

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

```mermaid
graph TB
    subgraph "Availability Zone 1"
        RR1[Route Reflector 1]
        N1[Node 1]
        N2[Node 2]
        N3[Node 3]
    end

    subgraph "Availability Zone 2"
        RR2[Route Reflector 2]
        N4[Node 4]
        N5[Node 5]
        N6[Node 6]
    end

    RR1 <--> RR2
    N1 & N2 & N3 --> RR1
    N1 & N2 & N3 --> RR2
    N4 & N5 & N6 --> RR1
    N4 & N5 & N6 --> RR2
```

**Patrón 2: Route Reflectors jerárquicos (clústeres grandes)**

```mermaid
graph TB
    subgraph "Tier 1 - Global RRs"
        GRR1[Global RR 1]
        GRR2[Global RR 2]
    end

    subgraph "Tier 2 - Rack RRs"
        RRR1[Rack 1 RR]
        RRR2[Rack 2 RR]
        RRR3[Rack 3 RR]
    end

    subgraph "Rack 1 Nodes"
        R1N1[Node]
        R1N2[Node]
    end

    subgraph "Rack 2 Nodes"
        R2N1[Node]
        R2N2[Node]
    end

    subgraph "Rack 3 Nodes"
        R3N1[Node]
        R3N2[Node]
    end

    GRR1 <--> GRR2
    GRR1 <--> RRR1 & RRR2 & RRR3
    GRR2 <--> RRR1 & RRR2 & RRR3

    R1N1 & R1N2 --> RRR1
    R2N1 & R2N2 --> RRR2
    R3N1 & R3N2 --> RRR3
```

***

## Recurso BGPPeer

El recurso `BGPPeer` define relaciones de peering BGP entre nodos de Calico y BGP speakers externos.

### Tipos de ámbito de BGPPeer

| Tipo              | Descripción          | Caso de uso                |
| ----------------- | -------------------- | ----------------------- |
| **Global**        | Se aplica a todos los nodos | Peering de router externo |
| **Específico de nodo** | Usa nodeSelector    | Peering local de rack      |
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

Establezca peering de los nodos de racks específicos con su switch ToR local:

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

Use `peerSelector` para seleccionar dinámicamente nodos de Calico como pares:

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

Calico puede anunciar IP de Service de Kubernetes mediante BGP, permitiendo que clientes externos accedan a los servicios directamente.

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

Las comunidades BGP le permiten etiquetar rutas para enrutamiento basado en políticas en routers externos:

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

### Número de AS específico de nodo

Para topologías complejas, puede asignar diferentes números de AS por nodo:

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
| **ClusterIP**      | IP de servicio interna       | Balanceo de carga interno |
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

Para clústeres bare-metal sin integración con un proveedor de nube:

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

Use annotations para controlar qué servicios se anuncian:

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

### Ejemplos de configuración de switch ToR

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

### Integración de arquitectura spine-leaf

```mermaid
graph TB
    subgraph "Spine Layer (AS 65000)"
        S1[Spine 1<br/>10.0.0.1]
        S2[Spine 2<br/>10.0.0.2]
    end

    subgraph "Leaf Layer"
        subgraph "Rack 1 (AS 65001)"
            L1[Leaf 1<br/>10.0.1.1]
            K1[K8s Node 1<br/>AS 64512]
            K2[K8s Node 2<br/>AS 64512]
        end

        subgraph "Rack 2 (AS 65002)"
            L2[Leaf 2<br/>10.0.2.1]
            K3[K8s Node 3<br/>AS 64512]
            K4[K8s Node 4<br/>AS 64512]
        end

        subgraph "Rack 3 (AS 65003)"
            L3[Leaf 3<br/>10.0.3.1]
            K5[K8s Node 5<br/>AS 64512]
            K6[K8s Node 6<br/>AS 64512]
        end
    end

    S1 <--> L1 & L2 & L3
    S2 <--> L1 & L2 & L3

    K1 & K2 --> L1
    K3 & K4 --> L2
    K5 & K6 --> L3
```

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

Generalized TTL Security Mechanism evita paquetes BGP falsificados:

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

Reduzca la cantidad de rutas anunciadas mediante la agregación de CIDR de Pod:

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

### Reinicio ordenado

Habilite BGP Graceful Restart para minimizar la interrupción del tráfico durante los reinicios de BIRD:

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

### Comandos de birdcl

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

### Problemas y soluciones comunes de BGP

| Problema                    | Síntomas                      | Solución                              |
| ------------------------ | ----------------------------- | ------------------------------------- |
| Sesiones bloqueadas en Active | No se aprenden rutas             | Compruebe el firewall (TCP 179) y los números de AS  |
| Las rutas no se propagan   | Pods inalcanzables entre racks | Verifique la malla de nodo a nodo o la configuración de RR |
| Flapping de rutas           | Conectividad intermitente     | Compruebe los temporizadores BGP y la estabilidad de red   |
| Restablecimientos de sesión           | Established->Active frecuente  | Compruebe MTU y contraseñas MD5              |

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

## Diseño multi-rack y multi-centro de datos

### Multi-rack con Route Reflectors

```mermaid
graph TB
    subgraph "Datacenter"
        subgraph "Management Rack"
            RR1[Route Reflector 1<br/>Cluster ID: 1.0.0.1]
            RR2[Route Reflector 2<br/>Cluster ID: 1.0.0.1]
        end

        subgraph "Compute Rack 1"
            N1[Node 1]
            N2[Node 2]
            N3[Node 3]
        end

        subgraph "Compute Rack 2"
            N4[Node 4]
            N5[Node 5]
            N6[Node 6]
        end

        subgraph "Compute Rack 3"
            N7[Node 7]
            N8[Node 8]
            N9[Node 9]
        end
    end

    RR1 <--> RR2

    N1 & N2 & N3 --> RR1
    N1 & N2 & N3 --> RR2
    N4 & N5 & N6 --> RR1
    N4 & N5 & N6 --> RR2
    N7 & N8 & N9 --> RR1
    N7 & N8 & N9 --> RR2
```

### Diseño BGP multi-centro de datos

```mermaid
graph TB
    subgraph "DC1 (AS 64512)"
        subgraph "DC1 RRs"
            DC1_RR1[DC1 RR1]
            DC1_RR2[DC1 RR2]
        end
        DC1_N1[DC1 Nodes]

        DC1_RR1 <--> DC1_RR2
        DC1_N1 --> DC1_RR1 & DC1_RR2
    end

    subgraph "DC2 (AS 64513)"
        subgraph "DC2 RRs"
            DC2_RR1[DC2 RR1]
            DC2_RR2[DC2 RR2]
        end
        DC2_N1[DC2 Nodes]

        DC2_RR1 <--> DC2_RR2
        DC2_N1 --> DC2_RR1 & DC2_RR2
    end

    subgraph "WAN Edge (AS 65000)"
        WAN1[WAN Router 1]
        WAN2[WAN Router 2]
    end

    DC1_RR1 & DC1_RR2 <--> WAN1 & WAN2
    DC2_RR1 & DC2_RR2 <--> WAN1 & WAN2
```

Configuración para múltiples centros de datos:

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

1. **Tamaño del clúster < 50 nodos**: la malla completa es aceptable
2. **Tamaño del clúster 50-200 nodos**: implemente 2-3 Route Reflectors
3. **Tamaño del clúster > 200 nodos**: implemente Route Reflectors jerárquicos
4. **Multi-rack**: use una ubicación de Route Reflector consciente del rack
5. **Multi-centro de datos**: use un AS independiente por DC con eBGP entre DC

### Recomendaciones de seguridad

1. Habilite siempre la autenticación MD5 para pares externos
2. Implemente filtrado de prefijos para evitar la inyección de rutas
3. Use GTSM (seguridad TTL) donde sea compatible
4. Limite el máximo de rutas aceptadas por par
5. Supervise las sesiones BGP para detectar anomalías

### Recomendaciones operativas

1. Etiquete los nodos de manera coherente para la topología BGP
2. Documente el esquema de asignación de números de AS
3. Implemente supervisión y alertas de BGP
4. Pruebe los escenarios de failover regularmente
5. Mantenga los temporizadores BGP coherentes entre pares

***

## Referencias

* [Documentación de BGP de Calico](https://docs.tigera.io/calico/latest/networking/configuring/bgp)
* [BIRD Internet Routing Daemon](https://bird.network.cz/)
* [RFC 4271 - BGP-4](https://tools.ietf.org/html/rfc4271)
* [RFC 4456 - BGP Route Reflection](https://tools.ietf.org/html/rfc4456)
* [RFC 5765 - GTSM para BGP](https://tools.ietf.org/html/rfc5082)
