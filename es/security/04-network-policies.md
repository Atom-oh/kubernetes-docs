# Network Policies

> **Base de revisión**: OpenAPI de Kubernetes 1.35, Cilium 1.20.1, Calico 3.32.2 y documentación actual de AWS. Las comprobaciones offline no establecen la compatibilidad del clúster.
> **Última actualización**: September 13, 2026

Las Network Policies de Kubernetes son reglas de firewall que controlan el tráfico entre Pods. Este documento abarca la NetworkPolicy básica y las extensiones de Cilium/Calico. Las secciones son ejemplos independientes; combinar todas las políticas cambiaría los permisos efectivos. No se realizó ningún despliegue en clúster/nube ni prueba de conectividad en vivo.

## Tabla de contenido

1. [Descripción general de Network Policy](#network-policy-overview)
2. [Especificación de NetworkPolicy de Kubernetes](#kubernetes-networkpolicy-spec)
3. [Políticas de denegación predeterminada](#default-deny-policies)
4. [Orden y evaluación de políticas](#policy-order-and-evaluation)
5. [Extensiones de Network Policy de Cilium](#cilium-network-policy-extensions)
6. [Extensiones de Network Policy de Calico](#calico-network-policy-extensions)
7. [Patrones de diseño](#design-patterns)
8. [Pruebas de Network Policies](#testing-network-policies)
9. [Consideraciones de EKS](#eks-considerations)
10. [Herramientas de visualización](#visualization-tools)

---

## Descripción general de Network Policy {#network-policy-overview}

### ¿Qué es una Network Policy?

Una NetworkPolicy de Kubernetes selecciona Pods de su propio namespace (espacio de nombres) y controla el tráfico de ingress y egress admitido. Un Pod sin ninguna política que lo seleccione para una dirección no queda aislado por NetworkPolicy en esa dirección; el enrutamiento, los security groups, las NACL y otros motores de políticas aún pueden impedir la conectividad.

**Ambos extremos deben permitir** una conexión Pod a Pod: las reglas de egress efectivas del origen y las reglas de ingress efectivas del destino deben permitirla. El tráfico de retorno de una conexión permitida se permite implícitamente. Las políticas se implementan de forma asíncrona mediante un plugin de red compatible; un objeto de la API por sí solo no demuestra que se apliquen. El tráfico de nodo/hostNetwork y los protocolos distintos de TCP/UDP/SCTP requieren una revisión específica de la implementación. Los diagramas siguientes muestran la intención de la política, no una garantía de alcanzabilidad.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    No Network Policy (Default State)                     │
│                                                                         │
│    ┌─────────┐        ┌─────────┐        ┌─────────┐                   │
│    │  Pod A  │◀──────▶│  Pod B  │◀──────▶│  Pod C  │                   │
│    └─────────┘        └─────────┘        └─────────┘                   │
│         ▲                  ▲                  ▲                         │
│         │                  │                  │                         │
│         └──────────────────┴──────────────────┘                         │
│              Free communication between all Pods                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    With Network Policy Applied                           │
│                                                                         │
│    ┌─────────┐        ┌─────────┐        ┌─────────┐                   │
│    │  Pod A  │───────▶│  Pod B  │        │  Pod C  │                   │
│    └─────────┘        └─────────┘        └─────────┘                   │
│                            ▲                                            │
│                            │ Allowed                                    │
│                       ┌────┴────┐                                       │
│                       │Controlled│                                      │
│                       │by Policy │                                      │
│                       └─────────┘                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Características de Network Policy

| Propiedad | Descripción |
|----------|-------------|
| **Ámbito de Namespace** | NetworkPolicy se aplica a los recursos dentro de un namespace |
| **Aditiva** | Las reglas de permiso de las NetworkPolicies de Kubernetes que seleccionan el Pod forman una unión para cada dirección; las denegaciones de Cilium, los tiers de Calico y las políticas administrativas de AWS tienen semánticas distintas |
| **Aplicación selectiva** | Los Pods objetivo se especifican mediante podSelector |
| **Control direccional** | Control independiente para Ingress (entrante) y Egress (saliente) |
| **Dependiente del CNI** | El plugin de CNI debe admitir NetworkPolicy |

### Compatibilidad de NetworkPolicy por CNI

| CNI | NetworkPolicy básica | Extensiones | Política L7 |
|-----|---------------------|------------|-----------|
| **Cilium** | ✓ | CiliumNetworkPolicy, CiliumClusterwideNetworkPolicy | ✓ |
| **Calico** | ✓ | GlobalNetworkPolicy, NetworkSet, Tier | Integración opcional con Istio/Dikastes; verifique el producto y las versiones desplegadas |
| **Weave Net (proyecto archivado)** | Compatibilidad histórica | Referencia heredada; evalúe una implementación mantenida para nuevos despliegues | ✗ |
| **Flannel por sí solo** | Sin aplicación de políticas por sí mismo | Se necesita un motor de políticas compatible aparte | ✗ |
| **Amazon VPC CNI** | ✓ cuando está habilitado en nodos EC2 Linux compatibles | NetworkPolicy estándar; ClusterNetworkPolicy con VPC CNI 1.21+ | Egress de DNS en nodos de EKS Auto Mode; consulte las consideraciones de EKS |

---

## Especificación de NetworkPolicy de Kubernetes {#kubernetes-networkpolicy-spec}

### Estructura básica

Especifique `policyTypes` de forma explícita. Si se omite, Kubernetes asume Ingress de forma predeterminada y añade Egress cuando existe al menos una regla de egress. Los arrays de reglas vacíos por sí solos no implican ambas direcciones.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: example-policy
  namespace: default
spec:
  # Select Pods to apply policy
  podSelector:
    matchLabels:
      app: web

  # Policy types (auto-inferred if omitted)
  policyTypes:
    - Ingress
    - Egress

  # Ingress rules (inbound traffic)
  ingress:
    - from:
        - podSelector:
            matchLabels:
              role: frontend
        - namespaceSelector:
            matchLabels:
              project: myproject
        - ipBlock:
            cidr: 172.17.0.0/16
            except:
              - 172.17.1.0/24
      ports:
        - protocol: TCP
          port: 80
        - protocol: TCP
          port: 443

  # Egress rules (outbound traffic)
  egress:
    - to:
        - podSelector:
            matchLabels:
              role: database
      ports:
        - protocol: TCP
          port: 5432
```

### podSelector

Selecciona los Pods de su propio namespace a los que se aplica la política. Los siguientes son fragmentos alternativos de especificación, no recursos independientes de la API.

```yaml
# Apply to Pods with specific labels
spec:
  podSelector:
    matchLabels:
      app: api
      version: v1

---
# Apply to all Pods (empty selector)
spec:
  podSelector: {}

---
# Using matchExpressions
spec:
  podSelector:
    matchExpressions:
      - key: app
        operator: In
        values:
          - api
          - web
      - key: environment
        operator: NotIn
        values:
          - development
```

### namespaceSelector

Selecciona namespaces por etiquetas, incluido el namespace actual si coincide. `name` no es una etiqueta de namespace asignada automáticamente. Use la etiqueta integrada e inmutable `kubernetes.io/metadata.name` para indicar un nombre exacto de namespace; restrinja quién puede modificar las etiquetas personalizadas de tenencia.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-from-monitoring
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        # Allow all Pods from monitoring namespace
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
        # Allow specific Pods from production namespace
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: production
          podSelector:
            matchLabels:
              role: frontend
```

**Nota:** distinción entre AND y OR al usar `namespaceSelector` y `podSelector` juntos:

```yaml
# OR condition (two separate peer entries)
ingress:
  - from:
      - namespaceSelector:    # Rule 1
          matchLabels:
            kubernetes.io/metadata.name: team-a
      - podSelector:          # Rule 2
          matchLabels:
            role: frontend

---
# AND condition (single rule)
ingress:
  - from:
      - namespaceSelector:    # Both conditions must be met
          matchLabels:
            kubernetes.io/metadata.name: team-a
        podSelector:
          matchLabels:
            role: frontend
```

### ipBlock

Un `ipBlock` permite un CIDR menos sus rangos `except` en esa regla. Una excepción no es una denegación global y otra política puede permitirla. La traducción de direcciones de Service/load balancer puede cambiar el origen o el destino visible para el CNI; verifique la ruta real. Los CIDR de documentación siguientes son ilustrativos, no endpoints de producción alcanzables.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-external-traffic
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: public-api
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        # Example private source range; not a guarantee of the load balancer source IP
        - ipBlock:
            cidr: 10.0.0.0/8
        # Allow specific external IP
        - ipBlock:
            cidr: 203.0.113.0/24
  egress:
    - to:
        # Allow external API server access
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 10.0.0.0/8      # Exclude internal networks
              - 172.16.0.0/12
              - 192.168.0.0/16
      ports:
        - protocol: TCP
          port: 443
```

### ports

Especifique los puertos y protocolos permitidos. `endPort` requiere un puerto inicial numérico y compatibilidad del CNI con rangos; un puerto con nombre no puede ser el inicio de un rango. La aceptación por parte de la API no demuestra por sí sola que todos los plugins la apliquen.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: port-specific-policy
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: web
  policyTypes:
    - Ingress
  ingress:
    - ports:
        # Specific ports
        - protocol: TCP
          port: 80
        - protocol: TCP
          port: 443
        # Port range (Kubernetes 1.25+)
        - protocol: TCP
          port: 8000
          endPort: 8080
        # Named port
        - protocol: TCP
          port: http
```

---

## Políticas de denegación predeterminada {#default-deny-policies}

Una base vacía no aporta ningún permiso; otras políticas que seleccionen el Pod aún pueden permitir tráfico. El comportamiento de las conexiones existentes tras un cambio de política depende de la implementación y debe probarse por separado.

### Denegación predeterminada de Ingress

Una base de aislamiento de ingress sin permisos propios. Otras políticas que seleccionen el Pod aún pueden permitir ingress:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}  # Apply to all Pods
  policyTypes:
    - Ingress
  # No ingress rules = block all inbound traffic
```

### Denegación predeterminada de Egress

Una base de aislamiento de egress sin permisos propios. Otras políticas que seleccionen el Pod aún pueden permitir egress:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Egress
  # No egress rules = block all outbound traffic
```

### Denegación total (Ingress + Egress)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### Denegación predeterminada con DNS permitido

Este perfil supone un CoreDNS basado en Pods en `kube-system` con `k8s-app=kube-dns`. Permite TCP y UDP 53. Si el propio DNS tiene aislamiento de ingress, su política también debe permitir a los clientes. NodeLocal DNSCache y el CoreDNS local del nodo en Auto Mode necesitan el perfil real de ruta/IP de su resolutor; no aplique este selector de Pod sin cambios en esos casos.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress-allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### Política predeterminada de arquitectura Zero Trust

Están presentes ambas direcciones de frontend→API. Esto no permite tráfico entrante hacia el frontend ni API→base de datos; añada únicamente los flujos revisados. Use la suposición de DNS basado en Pods indicada arriba.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: zero-trust-default
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8080
```

## Orden y evaluación de políticas {#policy-order-and-evaluation}

### Reglas de evaluación de políticas

Para cada endpoint y dirección, evalúe únicamente las **NetworkPolicies de Kubernetes** que lo seleccionan, como se indica a continuación. Después, compruebe la dirección del otro endpoint y todos los demás controles de red. Una política solo de ingress no aísla el egress.

```
┌─────────────────────────────────────────────────────────────────┐
│                  NetworkPolicy Evaluation Flow                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Are there policies that apply to the Pod?                   │
│     │                                                           │
│     ├─ No → Allow all traffic (default behavior)                │
│     │                                                           │
│     └─ Yes → Start policy evaluation                            │
│              │                                                  │
│              ▼                                                  │
│  2. Is there a policy for this direction (Ingress/Egress)?      │
│     │                                                           │
│     ├─ No → Allow traffic in that direction                     │
│     │                                                           │
│     └─ Yes → Start rule matching                                │
│              │                                                  │
│              ▼                                                  │
│  3. Does traffic match one or more rules?                       │
│     │                                                           │
│     ├─ Matched → Allow traffic                                  │
│     │                                                           │
│     └─ Not matched → Block traffic                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Combinación de varias políticas

Cuando varias NetworkPolicies se aplican al mismo Pod, todas las reglas de las políticas se combinan (unión):

```yaml
---
# Policy 1: Allow traffic from frontend
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
---
# Policy 2: Allow traffic from monitoring
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
      ports:
        - protocol: TCP
          port: 8080
        - protocol: TCP
          port: 9090
```

**Resultado:** el ingress de la API permite Pods de frontend en 8080 y Pods del namespace monitoring en 8080/9090. Sus reglas de egress, los listeners reales y otros controles de red también deben permitir la conexión.

### Orden de evaluación de políticas

La API NetworkPolicy de Kubernetes no tiene prioridad ni reglas de denegación explícitas. Su unión de permisos no describe el orden/las acciones de tier de Calico, las denegaciones explícitas de Cilium ni la evaluación de políticas administrativas de AWS:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Policy A    Policy B    Policy C                              │
│   (allow X)   (allow Y)   (allow Z)                             │
│       │           │           │                                 │
│       └───────────┼───────────┘                                 │
│                   │                                             │
│                   ▼                                             │
│           ┌───────────────┐                                     │
│           │     Union     │                                     │
│           │ (X OR Y OR Z) │                                     │
│           └───────────────┘                                     │
│                   │                                             │
│                   ▼                                             │
│           Final allowed traffic:                                │
│           X, Y, Z all allowed                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Extensiones de Network Policy de Cilium {#cilium-network-policy-extensions}

Estos ejemplos usan el esquema de políticas de la versión publicada Cilium 1.20.1, no son una indicación de actualizar todos los clústeres. Las reglas HTTP necesitan una ruta de proxy L7 compatible. El chaining con AWS VPC CNI tiene limitaciones documentadas en funciones avanzadas, incluidas las políticas L7; no suponga que estos ejemplos HTTP funcionan en ese modo. Una identidad de seguridad numérica de Cilium es una asignación para un conjunto de etiquetas, no un ID de aplicación permanente.

### CiliumNetworkPolicy

Cilium amplía la NetworkPolicy básica con funciones más potentes.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: cilium-l7-policy
  namespace: production
spec:
  # Endpoint selection
  endpointSelector:
    matchLabels:
      app: api

  # L3/L4 rules (similar to basic NetworkPolicy)
  ingress:
    - fromEndpoints:
        - matchLabels:
            app: frontend
      toPorts:
        - ports:
            - port: "8080"
              protocol: TCP
          # L7 rules (Cilium extension)
          rules:
            http:
              - method: GET
                path: "/api/v1/.*"
              - method: POST
                path: "/api/v1/users"
                headers:
                  - 'Content-Type: application/json'
```

### Política HTTP L7

Las reglas HTTP de Cilium filtran las solicitudes visibles para su proxy L7; no autentican claves de API ni establecen roles de administrador. Un llamante puede suministrar una cabecera `X-User-Role`. Este ejemplo filtra métodos, rutas y un `Content-Type` exacto. Aplique la autenticación y la autorización en la aplicación o en una puerta de enlace autenticada. El TLS de extremo a extremo no se descifra automáticamente para la inspección HTTP. Revise otras políticas que puedan permitir el mismo tráfico en L4.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: http-api-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: api-server
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: web-frontend
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
      rules:
        http:
        - method: GET
          path: /api/v1/products
        - method: GET
          path: /api/v1/products/[0-9]+
        - method: POST
          path: /api/v1/orders
          headerMatches:
          - name: Content-Type
            value: application/json
```

[HTTP API — Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/pkg/policy/api/http.go)

### Política Kafka L7

El esquema CNP de la versión publicada Cilium 1.20.1 admite reglas L7 de HTTP y DNS, pero no tiene `rules.kafka`. La antigua receta con `role`, `topic` y `clientID` no es una API desplegable actual. Restrinja la conectividad con los brokers mediante network policy y después aplique los permisos de productor/consumidor para `orders` y `events` usando la autenticación y las ACL de Kafka. Un ID de cliente no es un principal autenticado.

Este ejemplo L4 supone un listener de broker con TLS ya configurado en TCP 9093, clientes en el mismo namespace y egress/DNS del cliente autorizados por separado. No configura TLS, ACL de broker ni permisos de topic.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kafka-client-network-access
  namespace: data
spec:
  endpointSelector:
    matchLabels:
      app: kafka
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: producer
    - matchLabels:
        app: consumer
    toPorts:
    - ports:
      - port: '9093'
        protocol: TCP
```

[CNP schema — Cilium 1.20.1](https://github.com/cilium/cilium/blob/v1.20.1/pkg/k8s/apis/cilium.io/client/crds/v2/ciliumnetworkpolicies.yaml)

### Política DNS L7

Este ejemplo usa CoreDNS basado en Pods. `ANY` en el puerto53 cubre UDP y TCP. El permiso para consultas DNS y el permiso para conectarse a una IP devuelta son distintos: resolver el nombre de la base de datos que aparece a continuación no permite conexiones a la base de datos. Sustituya el dominio de ejemplo, tenga en cuenta los sufijos de búsqueda de DNS, la caché y el TTL, y verifique el perfil real del resolutor. Las reglas FQDN aprenden IP a partir del DNS; no autentican un tenant de SaaS ni sustituyen a TLS o a la autorización de la aplicación.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: dns-policy
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: web
  egress:
  - toEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: kube-system
        k8s:k8s-app: kube-dns
    toPorts:
    - ports:
      - port: '53'
        protocol: ANY
      rules:
        dns:
        - matchName: api.example.com
        - matchName: database.production.svc.cluster.local
  - toFQDNs:
    - matchName: api.example.com
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

### CiliumClusterwideNetworkPolicy

El recurso tiene ámbito de clúster, mientras que su selector lo limita explícitamente a `production/app=api`. Permite Pods de gateway en TCP8080. Controla solo el ingress; el aislamiento de egress/DNS y el propio egress del gateway requieren sus políticas correspondientes. El ejemplo anterior de permiso cluster/world para todos los endpoints no era una política de denegación predeterminada.

```yaml
apiVersion: cilium.io/v2
kind: CiliumClusterwideNetworkPolicy
metadata:
  name: production-api-from-edge
spec:
  endpointSelector:
    matchLabels:
      k8s:io.kubernetes.pod.namespace: production
      app: api
  ingress:
  - fromEndpoints:
    - matchLabels:
        k8s:io.kubernetes.pod.namespace: gateway-system
        app: edge-proxy
    toPorts:
    - ports:
      - port: '8080'
        protocol: TCP
```

### Política basada en entidades de Cilium

`host` incluye el nodo local y sus contenedores con red de host; `cluster` incluye más que los Pods de aplicación. `world` cubre los endpoints externos al clúster y no es una lista de permitidos granular de Internet/SaaS. Use reglas explícitas de CIDR/FQDN cuando limite el acceso externo. Este ejemplo concede acceso TCP443 únicamente a un cliente etiquetado de la API de Kubernetes; configure aparte su endpoint de API, la confianza TLS, las credenciales y el RBAC. La identidad de origen puede cambiar en las rutas de red de un plano de control gestionado, así que inspeccione la identidad real del flujo en lugar de ampliar el ingress a todo el clúster.

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: kubernetes-api-client
  namespace: production
spec:
  endpointSelector:
    matchLabels:
      app: kubernetes-api-client
  egress:
  - toEntities:
    - kube-apiserver
    toPorts:
    - ports:
      - port: '443'
        protocol: TCP
```

## Extensiones de Network Policy de Calico {#calico-network-policy-extensions}

Los ejemplos de política/Tier siguen los recursos de Calico Open Source3.32.2. `projectcalico.org/v3` requiere el servidor de API de Calico compatible o el flujo de trabajo equivalente con `calicoctl`; no es la API de almacenamiento cruda de Kubernetes `crd.projectcalico.org/v1`. Verifique el datastore/API instalado antes de aplicarlos. Las acciones ordenadas de Calico y la delegación entre tiers difieren de la API aditiva NetworkPolicy de Kubernetes.

La documentación actual de Open Source también describe la [integración a nivel de aplicación con Istio/Dikastes](https://docs.tigera.io/calico/latest/network-policy/istio/app-layer-policy). La API HTTPMatch requiere esa configuración aparte y admite reglas Allow de ingress. Los ejemplos de Calico siguientes cubren políticas L3/L4; esta revisión no desplegó ni probó la integración L7.

### NetworkPolicy de Calico

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: calico-policy
  namespace: production
spec:
  # Policy order (lower = evaluated first)
  order: 100

  selector: app == 'api'

  types:
    - Ingress
    - Egress

  ingress:
    - action: Allow
      protocol: TCP
      source:
        selector: app == 'frontend'
      destination:
        ports:
          - 8080

  egress:
    - action: Allow
      protocol: TCP
      destination:
        selector: app == 'database'
        ports:
          - 5432
```

### GlobalNetworkPolicy

Estos dos recursos globales seleccionan únicamente cargas de trabajo del namespace `production`. Un `selector: all()` sin restricciones también puede afectar a los host endpoints; no aplique una denegación a nivel de clúster sin un ámbito explícito y una vía de recuperación. Un `order` menor se evalúa primero dentro del tier. El ejemplo permite el DNS basado en Pods y, por lo demás, proporciona una base de denegación; añada los flujos de aplicación revisados y tenga en cuenta las acciones de los tiers superiores.

```yaml
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: production-default-deny
spec:
  namespaceSelector: projectcalico.org/name == 'production'
  selector: all()
  order: 1000
  types:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: production-allow-dns
spec:
  namespaceSelector: projectcalico.org/name == 'production'
  selector: all()
  order: 100
  types:
  - Egress
  egress:
  - action: Allow
    protocol: UDP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
  - action: Allow
    protocol: TCP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
```

### NetworkSet

Los selectores de NetworkSet coinciden con `metadata.labels`, no con el nombre del recurso. El primer conjunto tiene ámbito de namespace; el conjunto bloqueado es global y lo consume el ejemplo del tier de seguridad más abajo. Todos los CIDR aquí son rangos de documentación y deben sustituirse por destinos revisados. El ejemplo de egress permite TCP443 hacia el conjunto etiquetado con ámbito de namespace; el DNS es una regla aparte.

```yaml
apiVersion: projectcalico.org/v3
kind: NetworkSet
metadata:
  name: external-apis
  namespace: production
  labels:
    network-role: external-api
spec:
  nets:
  - 203.0.113.0/24
  - 198.51.100.10/32
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkSet
metadata:
  name: blocked-ips
  labels:
    network-role: blocked
spec:
  nets:
  - 192.0.2.0/24
---
apiVersion: projectcalico.org/v3
kind: NetworkPolicy
metadata:
  name: allow-external-apis
  namespace: production
spec:
  selector: app == 'web'
  types:
  - Egress
  egress:
  - action: Allow
    protocol: TCP
    destination:
      selector: network-role == 'external-api'
      ports:
      - 443
```

### Políticas basadas en Tier

Los tiers están disponibles en la versión de Calico Open Source referenciada, no solo en Enterprise. Un tier que selecciona el endpoint aplica `Deny` de forma predeterminada cuando ninguna regla actúa. Por eso el tier deny-known-threats usa explícitamente `defaultAction: Pass`, para que el tráfico no relacionado pueda llegar a las políticas posteriores. `Pass` es delegación, no permiso. `global()` corresponde a `namespaceSelector`; el selector de etiquetas separado identifica el GlobalNetworkSet. Complete las políticas del tier de aplicación y verifique el comportamiento final de perfil/tier predeterminado antes del despliegue; crear un Tier vacío no es una política completa de aislamiento de aplicaciones.

```yaml
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: security
spec:
  order: 100
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: platform
spec:
  order: 200
  defaultAction: Pass
---
apiVersion: projectcalico.org/v3
kind: Tier
metadata:
  name: application
spec:
  order: 300
  defaultAction: Deny
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: security.block-known-threats
spec:
  tier: security
  order: 100
  selector: all()
  namespaceSelector: projectcalico.org/name == 'production'
  types:
  - Ingress
  ingress:
  - action: Deny
    source:
      selector: network-role == 'blocked'
      namespaceSelector: global()
---
apiVersion: projectcalico.org/v3
kind: GlobalNetworkPolicy
metadata:
  name: platform.allow-dns
spec:
  tier: platform
  order: 100
  selector: all()
  namespaceSelector: projectcalico.org/name == 'production'
  types:
  - Egress
  egress:
  - action: Allow
    protocol: UDP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
  - action: Allow
    protocol: TCP
    destination:
      selector: k8s-app == 'kube-dns'
      namespaceSelector: projectcalico.org/name == 'kube-system'
      ports:
      - 53
```

## Patrones de diseño {#design-patterns}

Estos son **perfiles de política alternativos**, no un paquete para aplicar en conjunto. Reutilizar `production` no hace compatibles ejemplos no relacionados: sus reglas de permiso se acumularían. Prepare primero los namespaces, las etiquetas de las cargas de trabajo, los puertos de escucha y el perfil de DNS real. Los ejemplos se comprobaron localmente en cuanto a esquema/intención, no se ejercitaron en un clúster.

### Microsegmentación

Este perfil permite frontend→API en TCP8080 y API→base de datos en TCP5432 en ambos lados, además del DNS. Deliberadamente no tiene egress a Internet ni ingress externo al frontend. Si se requieren, añada un CIDR/puerto de destino aprobado o un perfil de gateway de egress autenticado; excluir RFC1918 de 0.0.0.0/0 no es una lista de permitidos de SaaS.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: frontend
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: frontend-to-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-to-database
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-from-api
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 5432
```

### Aislamiento de Namespace

El perfil de equipo incluye ingress **y egress** dentro del mismo equipo, además del DNS. Los servicios compartidos necesitan además un ingress en el destino que permita a team-a y un listener TLS443 real. Restrinja la administración de las etiquetas de namespace; una etiqueta de equipo no es un límite de confianza independiente.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
  labels:
    team: team-a
    environment: production
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-same-team
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - &id001
      namespaceSelector:
        matchLabels:
          team: team-a
  egress:
  - to:
    - *id001
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-shared-services
  namespace: team-a
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          shared-services: 'true'
      podSelector:
        matchLabels:
          exposed: 'true'
    ports:
    - protocol: TCP
      port: 443
```

### Protección de la base de datos

El namespace `database` debe existir. Los llamantes de producción y los Pods de monitorización necesitan sus propios permisos de egress. Las reglas de peer en TCP5432 permiten únicamente el transporte de replicación supuesto de PostgreSQL; configure aparte la autenticación/TLS de la base de datos. TCP9187 supone un exporter instalado por separado.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-protection
  namespace: database
spec:
  podSelector:
    matchLabels:
      app: postgresql
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          environment: production
      podSelector:
        matchLabels:
          database-access: 'true'
    ports:
    - protocol: TCP
      port: 5432
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: monitoring
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9187
  - from:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgresql
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

### Política para arquitectura de 3 capas

Suponga una carga de trabajo existente `gateway-system/app=edge-proxy` que termina el TLS del cliente y puede alcanzar los Pods web en TCP80. La política de egress del gateway queda fuera de este namespace. El ingress y el egress entre peers de datos usan TCP5432/6379; los puertos adicionales de replicación, bus de clúster o copia de seguridad dependen de la base de datos elegida y no están implícitos. Separe los selectores de PostgreSQL y Redis en un despliegue real.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: three-tier-default-deny
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: web-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: web
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: gateway-system
      podSelector:
        matchLabels:
          app: edge-proxy
    ports:
    - protocol: TCP
      port: 80
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: app
    ports:
    - protocol: TCP
      port: 8080
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: web
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: data-tier-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      tier: data
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: app
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
  - from:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
  egress:
  - to:
    - podSelector:
        matchLabels:
          tier: data
    ports:
    - protocol: TCP
      port: 5432
    - protocol: TCP
      port: 6379
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: three-tier-dns
  namespace: production
spec:
  podSelector:
    matchExpressions:
    - key: tier
      operator: In
      values:
      - web
      - app
      - data
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
```

---

## Pruebas de Network Policies {#testing-network-policies}

### Pruebas con netshoot

Use Pods de diagnóstico aprobados y ya aprovisionados, con imágenes fijadas y permisos revisados. Seleccione etiquetas de origen, namespace y ubicación de nodo que realmente ejerciten la política; un Pod genérico sin etiquetas no representa a la aplicación. Aprovisionar netshoot crea una carga de trabajo y puede entrar en conflicto con la admisión de Pod Security. No cree ni elimine un nombre compartido fijo `test-pod` como parte de un script de observación. Ejecute pruebas únicamente contra endpoints de prueba propios.

### Pruebas con kubectl exec

Establezca el contexto, el namespace, el Pod existente y el contenedor de forma explícita. El éxito del DNS no es el éxito de TCP; el rechazo de la conexión, un listener no saludable, un error de TLS y un descarte por política son resultados diferentes. Estos comandos solo prueban la conectividad y no imprimen cuerpos de respuesta. No se ejecutaron contra un clúster durante esta revisión.

```bash
# Both Pods already exist in the approved test environment.
kubectl --context="$CONTEXT" -n "$NAMESPACE" get pods --show-labels
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- nslookup api-service.production.svc.cluster.local
kubectl --context="$CONTEXT" -n "$NAMESPACE" exec "$ALLOW_POD" \
  -c "$PROBE_CONTAINER" -- curl --silent --show-error --output /dev/null \
  --connect-timeout 3 --max-time 5 http://api-service.production.svc.cluster.local:8080/health
```

### Prueba de conectividad de Cilium

`cilium connectivity test` crea recursos de prueba y tráfico; no es un comando de estado de solo lectura. Use un clúster/namespace aislado y aprobado, una CLI e imágenes compatibles, destinos externos definidos y un plan de limpieza. Consulte `cilium connectivity test --help` para conocer los filtros de la CLI instalada en lugar de suponer que los nombres históricos de pruebas siguen existiendo. Que la suite pase no demuestra que se cumplan todas las políticas de la aplicación ni todas las funciones del chaining de CNI.

### Script de prueba automatizado

Este script solo ejecuta sondas curl acotadas en dos Pods existentes; no crea ni elimina recursos del clúster. Establezca `CONTEXT`, `NAMESPACE`, `ALLOW_POD`, `DENIED_POD`, `PROBE_CONTAINER` y una `TARGET_URL` sin datos secretos que termine en `/health`. Ambos contenedores necesitan `sh` y `curl`. El primer Pod es un control positivo conocido para el mismo destino. Las respuestas de error HTTP siguen demostrando alcanzabilidad de red, porque esta prueba no valida la salud de la aplicación.

La salida1 significa que el sujeto bloqueado se conectó de forma inesperada; la salida2 significa desconocido/error; la salida3 significa un tiempo de espera agotado que requiere corroboración. Un tiempo de espera agotado **nunca** se convierte en PASS automático: correlacione el origen/destino/puerto/hora exactos con un veredicto de descarte por política del CNI, comprobando además la salud del endpoint, las rutas y los controles de SG/NACL. Las pruebas simuladas locales no afirman que exista aplicación en vivo.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${CONTEXT:?Set an approved kubectl context}"
: "${NAMESPACE:?Set the test namespace}"
: "${ALLOW_POD:?Set an existing positive-control Pod}"
: "${DENIED_POD:?Set a different existing policy-subject Pod}"
: "${PROBE_CONTAINER:?Set a container with sh and curl in both Pods}"
: "${TARGET_URL:?Set the same non-secret health URL for both probes}"
if [[ "$ALLOW_POD" == "$DENIED_POD" ||
      ! "$TARGET_URL" =~ ^https?://[A-Za-z0-9.-]+(:[0-9]+)?/health$ ]]; then
  echo "Invalid probe inputs: use different Pods and a plain /health URL." >&2
  exit 2
fi
work=$(mktemp -d "${TMPDIR:-/tmp}/network-policy-probe.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
probe() {
  local pod=$1 result
  if ! result=$(kubectl --context="$CONTEXT" --request-timeout=15s \
      -n "$NAMESPACE" exec "$pod" -c "$PROBE_CONTAINER" -- \
      sh -c 'rc=0
        curl --silent --output /dev/null --connect-timeout 3 --max-time 5 "$1" || rc=$?
        printf "PROBE_EXIT=%s\n" "$rc"' sh "$TARGET_URL" \
      2>"$work/transport-error"); then
    echo "UNKNOWN: kubectl exec/authorization/transport failed." >&2
    return 2
  fi
  if [[ ! "$result" =~ ^PROBE_EXIT=([0-9]+)$ ]]; then
    echo "UNKNOWN: missing or malformed remote probe result." >&2
    return 2
  fi
  printf '%s\n' "${BASH_REMATCH[1]}"
}
allowed=$(probe "$ALLOW_POD") || exit 2
if [[ "$allowed" != 0 ]]; then
  echo "UNKNOWN: positive control could not reach the target." >&2
  exit 2
fi
denied=$(probe "$DENIED_POD") || exit 2
case "$denied" in
  0) echo "FAIL: the intended blocked Pod reached the target."; exit 1 ;;
  28) echo "INCONCLUSIVE: timeout; correlate an actual policy-drop verdict."; exit 3 ;;
  *) echo "UNKNOWN: DNS/TLS/refused/tool error is not proof of a policy drop."; exit 2 ;;
esac
```

## Consideraciones de EKS {#eks-considerations}

### Amazon VPC CNI y NetworkPolicy

Amazon VPC CNI admite network policy después de habilitarla. La guía actual de AWS exige VPC CNI 1.21+ tanto para las políticas estándar como para las administrativas, una plataforma de EKS compatible y un kernel de Linux 5.10+. La aplicación se limita a nodos EC2 Linux compatibles, no a Fargate ni a Windows. Use una versión de EKS actualmente compatible y verifique la versión compatible de su add-on; no deduzca la compatibilidad de EKS a partir de las versiones upstream de Kubernetes.

Para un add-on de VPC CNI **gestionado por EKS**, conserve su configuración existente al establecer la cadena documentada `"enableNetworkPolicy": "true"`. Lo siguiente modifica el clúster seleccionado tras la revisión; no actualiza la versión del add-on. Si la versión instalada es incompatible, deténgase y siga primero el procedimiento de actualización documentado.

```bash
# Requires AWS CLI, kubectl and jq; use an approved test cluster.
set -euo pipefail
: "${CLUSTER_NAME:?Set the approved test-cluster name}"
umask 077
aws eks describe-addon --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni   --output json > vpc-cni-before.json
jq -e '(.addon.configurationValues // "{}") | if . == "" then {} else fromjson end
  | .enableNetworkPolicy = "true"' vpc-cni-before.json > vpc-cni-network-policy.json
# Review the saved current version/configuration and the complete merged JSON first.
aws eks update-addon --cluster-name "$CLUSTER_NAME" --addon-name vpc-cni   --configuration-values file://vpc-cni-network-policy.json --resolve-conflicts PRESERVE
```

Compruebe el estado de la actualización y el comportamiento de las políticas antes del despliegue general. `--resolve-conflicts PRESERVE` no combina por usted un documento JSON de reemplazo; el ejemplo arrastra explícitamente los valores existentes. Conserve la instantánea para la recuperación. Una instalación gestionada por Helm usa su chart/values revisados y `enableNetworkPolicy: true`; no tome posesión de ella mediante este comando de add-on gestionado. Establecer la variable de entorno inventada `ENABLE_NETWORK_POLICY` no es el procedimiento de habilitación.

El modo de arranque estándar puede permitir inicialmente un Pod nuevo hasta que su política se programe. `NETWORK_POLICY_ENFORCING_MODE=strict` arranca los Pods elegibles en estado denegado y requiere una matriz de permisos completa, incluido el DNS; cambiarlo puede interrumpir las cargas de trabajo. Los Pods gestionados por un controlador son el objetivo fiable de las pruebas. La aplicación se realiza en la interfaz principal del Pod, así que inspeccione aparte las interfaces adicionales, el egress IPv6 hacia IPv4, la red de host y el NAT. No instale dos motores para gestionar las mismas políticas estándar ni elimine `aws-node` como atajo de migración.

### Políticas de seguridad de red mejoradas de EKS (December 2025)

> **Anunciado**: December 15, 2025 · [Fuente](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

La función es real, pero sus recursos usan **`networking.k8s.aws/v1alpha1`**. `ClusterNetworkPolicy` tiene ámbito de clúster y un `tier` obligatorio; el egress basado en DNS usa `ApplicationNetworkPolicy` para el ejemplo de namespace siguiente. Que VPC CNI admita políticas estándar/administrativas en EC2 Linux no significa que todos los modos de cómputo lo admitan. Las reglas de DNS solo se aplican en **instancias EC2 lanzadas por Auto Mode**, incluso en un clúster mixto.

Este ejemplo del tier Admin deniega el tráfico entrante desde Pods seleccionados por namespace hacia `isolated-demo`, incluidos los Pods de ese mismo namespace. No es un firewall completo externo/de red de host ni una política de permiso de DNS. Un Deny de Admin no puede ser anulado por una NetworkPolicy de namespace. Revise el CRD realmente instalado antes de añadir otras acciones: el esquema actual del controlador upstream de AWS llama `Accept` a su acción de permiso, mientras que el texto de la guía de usuario usa «Allow».

```yaml
apiVersion: networking.k8s.aws/v1alpha1
kind: ClusterNetworkPolicy
metadata:
  name: isolate-demo-namespace
spec:
  tier: Admin
  priority: 10
  subject:
    namespaces:
      matchLabels:
        kubernetes.io/metadata.name: isolated-demo
  ingress:
  - name: deny-pod-ingress
    action: Deny
    from:
    - namespaces:
        matchLabels: {}
```

El ejemplo de FQDN selecciona `app=backend` en `production`. **Sustituya `10.100.0.10/32` por la IP real de CoreDNS de Auto Mode de su clúster**: es la dirección de red del CIDR de Service más 10 (`::a/128` para IPv6). El CoreDNS de Auto Mode puro se ejecuta en el nodo; un selector de Pod de CoreDNS convencional no es intercambiable. Permita DNS por TCP y por UDP. Use un nombre de recurso único que no colisione con una NetworkPolicy de ese namespace.

```yaml
apiVersion: networking.k8s.aws/v1alpha1
kind: ApplicationNetworkPolicy
metadata:
  name: approved-api-egress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 10.100.0.10/32
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
  - to:
    - domainNames:
      - api.stripe.com
    ports:
    - protocol: TCP
      port: 443
```

El proxy de DNS observa las respuestas permitidas y sus TTL, y después la ruta de datos permite las IP/puertos de destino aprendidos. Esto no autentica una cuenta de SaaS ni demuestra la identidad HTTP del peer; las IP compartidas y el comportamiento del DNS requieren pruebas. La verificación del certificado TLS, la autorización de la aplicación, las rutas y cualquier regla de DNS Firewall de Route 53 siguen siendo relevantes. Otras políticas aplicables y las rutas directas al backend deben revisarse en conjunto.

[AWS NetworkPolicy](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy.html) · [Configuración](https://docs.aws.amazon.com/eks/latest/userguide/cni-network-policy-configure.html) · [Políticas de Auto Mode](https://docs.aws.amazon.com/eks/latest/userguide/auto-net-pol.html)

### Security Groups for Pods

Este ejemplo de vinculación supone el VPC Resource Controller de EKS, sus permisos de **cluster role**, nodos EC2 Linux compatibles con trunking y una configuración revisada de VPC CNI. La guía actual de AWS excluye Windows y EKS Auto Mode. Fargate usa un modelo distinto de SG por Pod y no obtiene compatibilidad con NetworkPolicy de VPC CNI por el simple hecho de tener un security group. Aplique la vinculación a los nuevos Pods de carga de trabajo coincidentes a través de su propietario; los Pods existentes no se adaptan automáticamente.

Para Calico junto con SG por Pod, AWS documenta VPC CNI1.11.0+ con `POD_SECURITY_GROUP_ENFORCING_MODE=standard`; use también los requisitos actuales del CNI, en lugar de tratar ese mínimo como una versión recomendada. El SNAT externo en modo estándar puede usar el SG del nodo en lugar del SG del Pod. Verifique la ruta exacta. El antiguo Pod de PostgreSQL sin más carecía de credenciales/almacenamiento y no era un despliegue de base de datos funcional.

```yaml
# Binding example only: use an existing reviewed security group.
apiVersion: vpcresources.k8s.aws/v1beta1
kind: SecurityGroupPolicy
metadata:
  name: database-sg-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  securityGroups:
    groupIds:
      - sg-0123456789abcdef0
```

El fragmento de Terraform permite el ingress a la BD desde un único SG de aplicación revisado y no inicia nuevas conexiones de egress. El tráfico de retorno con estado se permite por el seguimiento del SG; añada aparte solo el DNS, la replicación, las copias de seguridad o el egress externo necesarios. Las variables son entradas existentes del operador; no se ejecutó ningún plan/apply de Terraform.

```hcl
# Fragment for an existing reviewed Terraform configuration.
# Supply the actual VPC and application SG; this is not a standalone module.
resource "aws_security_group" "database_pods" {
  name_prefix = "database-pods-"
  vpc_id      = var.vpc_id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.application_security_group_id]
  }
  egress = []
}
```

### Combinación de controles a nivel de VPC con NetworkPolicy

La NetworkPolicy, los SG realmente aplicados y las NACL deben permitir todos la ruta correspondiente. Esta NetworkPolicy solo de ingress no restringe el egress de la base de datos; añada el perfil de egress seleccionado y el egress del Pod de origen. Varios SG combinan sus permisos. Las NACL son **sin estado**, así que una regla de subred que permita el puerto5432 entrante necesita una ruta de retorno equivalente hacia los puertos efímeros del cliente, además de reglas apropiadas en la subred del cliente. Los fragmentos siguientes no sustituyen un conjunto completo y revisado de reglas de ACL.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-policy
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              database-access: "true"
      ports:
        - protocol: TCP
          port: 5432
```

```hcl
# Fragments for a DB subnet NACL and an explicitly reviewed client CIDR.
# Choose the client's actual ephemeral port range; also review its subnet NACL.
resource "aws_network_acl_rule" "database_inbound" {
  network_acl_id = var.database_network_acl_id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.application_subnet_cidr
  from_port      = 5432
  to_port        = 5432
}
resource "aws_network_acl_rule" "database_return" {
  network_acl_id = var.database_network_acl_id
  rule_number    = 100
  egress         = true
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.application_subnet_cidr
  from_port      = var.client_ephemeral_port_start
  to_port        = var.client_ephemeral_port_end
}
```

### Uso de Cilium en EKS

Elija entre el **chaining con AWS VPC CNI** o una migración completa de CNI/IPAM diseñada por separado. En modo chaining, AWS VPC CNI conserva la responsabilidad de ENI/IPAM y Cilium acopla su datapath. Conserve `aws-node`; eliminarlo no es un atajo de instalación. Revise el propietario existente del add-on/Helm y evite motores de aplicación de políticas superpuestos. Los Pods existentes necesitan una recreación controlada antes de que se aplique la política del chaining; planifique la interrupción y la reversión.

La guía oficial de chaining de la versión1.20.1 proporciona estos valores, pero también documenta limitaciones de L7/IPsec. Contiene salidas ilustrativas antiguas; esas no validan su entorno actual de EKS. Prepare el repositorio/paquete del chart, verifique su procedencia y renderice primero:

```bash
# Render locally after verifying the official chart/package provenance.
# Rendering alone does not change a cluster or validate a migration.
helm template cilium cilium/cilium --version 1.20.1 \
  --namespace kube-system \
  --set cni.chainingMode=aws-cni \
  --set cni.exclusive=false \
  --set enableIPv4Masquerade=false \
  --set routingMode=native > cilium-reviewed.yaml
```

[AWS VPC CNI chaining — Cilium 1.20.1](https://docs.cilium.io/en/stable/installation/cni-chaining-aws-cni/)

## Herramientas de visualización {#visualization-tools}

### Editor de Network Policy de Cilium

Un editor de políticas ayuda a crear políticas; **la interfaz de Hubble visualiza los flujos de servicio observados**. Son herramientas diferentes. Habilitar Hubble/su interfaz cambia la configuración del clúster y corresponde al propietario de la instalación. Con un servicio de Hubble ya instalado y autenticado, inspeccione el servicio existente y use un port-forward local. No exponga la interfaz públicamente como atajo de depuración.

```bash
kubectl --context="$CONTEXT" -n kube-system port-forward --address=127.0.0.1 svc/hubble-ui 12000:80
```

### Comprobación de veredictos de política en Cilium

Use una conexión autenticada de Hubble. `DROPPED` incluye motivos distintos de la política; inspeccione el motivo del descarte, la identidad del endpoint, la hora y la dirección. Una observación `FORWARDED` en un punto no garantiza la entrega de extremo a extremo.


```bash
# Inspect observed policy decisions
hubble observe --verdict DROPPED
hubble observe --verdict FORWARDED

# Check traffic for specific Pod
hubble observe --pod production/api-server

# Output in JSON format
hubble observe --output json | jq '.flow.verdict'
```

### Interfaz de Calico Enterprise

La interfaz de gestión de Enterprise requiere el producto con licencia y su configuración real de servicio/TLS/autenticación; no se instala automáticamente con Calico Open Source. Inspeccione el nombre/puerto del servicio instalado y la política de acceso antes de hacer port-forward. No suponga que `cnx-manager` existe en todas las instalaciones.

### Herramientas de visualización de Network Policy

Use `kubectl get networkpolicy -n <namespace>` y `kubectl describe networkpolicy <name> -n <namespace>` para inspeccionar los selectores/reglas de las políticas de Kubernetes, y las herramientas de flujo autenticadas del motor instalado para inspeccionar la aplicación. La disponibilidad y las opciones de visores/plugins de terceros deben comprobarse frente a la versión actual de ese proyecto. Un grafo del YAML por sí solo no puede demostrar la aplicación en el plano de datos.

### Pruebas de seguridad con Kube-hunter

kube-hunter es un escáner de exposición/seguridad del clúster, no un verificador de permisos/denegaciones de NetworkPolicy. Sus escaneos pueden generar tráfico intrusivo; use un objetivo/ámbito aprobado explícitamente y una versión/imagen revisada. No despliegue un escáner sin versión fijada en un namespace en vivo a partir de un tutorial genérico de políticas. Esta revisión no ejecutó ningún escáner.

## Prácticas recomendadas

### 1. Aplicar una política de denegación predeterminada

```yaml
# Applies only to this production namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

### 2. Principio de mínimo privilegio

Permita explícitamente solo el tráfico necesario:

```yaml
# Explicit and specific rules
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-minimal-access
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - port: 8080
          protocol: TCP
```

### 3. Documentar las políticas

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-ingress
  namespace: production
  annotations:
    description: "Allow traffic from frontend to API on port 8080"
    owner: "platform-team"
    review-ticket: "REPLACE_WITH_APPROVED_CHANGE"
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080
```

### 4. Auditorías periódicas de políticas

Este inventario de solo lectura enumera las bases de permiso vacías de ámbito de namespace por separado para ingress y egress. Se tratan tanto los `[]` vacíos como los arrays de reglas ausentes, mientras que una regla `{}` permite tráfico y no es una base de denegación. Los errores de API/autorización provocan un fallo en lugar de aparecer como cero políticas. Una base enumerada **no es prueba de aislamiento**: otras reglas de permiso, las políticas de extensión, los Pods no cubiertos y el estado del CNI siguen requiriendo revisión.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${CONTEXT:?Set an approved kubectl context}"
work=$(mktemp -d "${TMPDIR:-/tmp}/network-policy-inventory.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
if ! kubectl --context="$CONTEXT" --request-timeout=15s get namespaces -o json >"$work/namespaces.json"; then
  echo "UNKNOWN: namespace inventory failed." >&2
  exit 2
fi
if ! kubectl --context="$CONTEXT" --request-timeout=15s get networkpolicies -A -o json >"$work/policies.json"; then
  echo "UNKNOWN: policy inventory failed." >&2
  exit 2
fi
jq -n --slurpfile ns "$work/namespaces.json" --slurpfile np "$work/policies.json" '
  def directions:
    (.spec.policyTypes // []) as $types |
    if ($types | length) > 0 then $types
    else ["Ingress"] + (if ((.spec.egress // []) | length) > 0 then ["Egress"] else [] end)
    end;
  def selects_all:
    ((.spec.podSelector.matchLabels // {}) | length) == 0 and
    ((.spec.podSelector.matchExpressions // []) | length) == 0;
  def empty_baseline($direction; $rules):
    select(selects_all and ((directions | index($direction)) != null) and
           ((.spec[$rules] // []) | length) == 0) | .metadata.name;
  {
    note: "Inventory only: other allow rules, extension policies and CNI enforcement are not evaluated.",
    namespaces: [
      $ns[0].items[] | .metadata.name as $name |
      [$np[0].items[] | select(.metadata.namespace == $name)] as $policies |
      {
        namespace: $name,
        policyCount: ($policies | length),
        ingressBaselines: [$policies[] | empty_baseline("Ingress"; "ingress")],
        egressBaselines: [$policies[] | empty_baseline("Egress"; "egress")]
      }
    ]
  }
'
```

## Resumen

Las Network Policies de Kubernetes son un mecanismo de seguridad esencial para controlar la comunicación entre Pods dentro de los clústeres:

1. **NetworkPolicy básica**: ámbito de namespace, admite podSelector/namespaceSelector/ipBlock
2. **Extensiones de Cilium**: políticas L7, políticas basadas en FQDN de DNS, políticas de ámbito de clúster
3. **Extensiones de Calico**: GlobalNetworkPolicy, NetworkSet, políticas basadas en Tier
4. **Consideraciones de EKS**: activación de NetworkPolicy en VPC CNI, Security Groups for Pods, ClusterNetworkPolicy y control de egress basado en DNS (FQDN)

### Recomendaciones

- Aplicar una política de denegación predeterminada a todos los namespaces de producción
- Permitir solo el tráfico necesario siguiendo el principio de mínimo privilegio
- Auditorías y pruebas periódicas de las políticas
- Considerar Cilium cuando se necesiten políticas L7

---

## Referencias

- [Documentación oficial de Network Policies de Kubernetes](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Documentación de Network Policy de Cilium](https://docs.cilium.io/en/stable/security/policy/index.html)
- [Documentación de Network Policy de Calico](https://docs.tigera.io/calico/latest/reference/resources/networkpolicy)
- [Prácticas recomendadas de seguridad de EKS: seguridad de red](https://docs.aws.amazon.com/eks/latest/best-practices/network-security.html)
- [Políticas de seguridad de red mejoradas de Amazon EKS (2025-12-15)](https://aws.amazon.com/about-aws/whats-new/2025/12/amazon-eks-enhanced-network-security-policies/)

- [Security groups de Pod en EKS](https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html)
- [Tier de Calico](https://docs.tigera.io/calico/latest/reference/resources/tier)
- [NetworkSet de Calico](https://docs.tigera.io/calico/latest/reference/resources/networkset)
